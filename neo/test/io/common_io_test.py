# encoding: utf-8
"""
Common tests for IOs:
 * check presence of all necessary attr
 * check types
 * write/read consistency  

See BaseTestIO.


The public URL is in url_for_tests.

The private url for writing is 
ssh://gate.g-node.org/groups/neo/io_test_files/

"""
__test__ = False #

url_for_tests =  "https://portal.g-node.org/neo/"

import os
import urllib
import logging

import neo
from neo.description import one_to_many_reslationship
from neo.test.tools import assert_arrays_almost_equal, assert_arrays_equal, assert_same_sub_schema, \
            assert_neo_object_is_compliant, assert_file_contents_equal, assert_sub_schema_is_lazy_loaded


from neo.test.io.generate_datasets import generate_from_supported_objects


try:
    import unittest2 as unittest
except ImportError:
    import unittest

class BaseTestIO(object):
    """
    This class make common tests for all IOs.
    
    Several startegies:
      * for IO able to read write : test_write_then_read
      * for IO able to read write with hash conservation (optional): test_read_then_write
      * for all IOs : test_assert_readed_neo_object_is_compliant
        2 cases:
          * files are at G-node and downloaded: download_test_files_if_not_present
          * files are generated by MyIO.write()
    
    """
    #~ __test__ = False
    
    # all IO test need to modify this:
    ioclass = None # the IOclass to be tested
    hash_conserved_when_write_read = False # when R/W and hash conserved    
    files_to_test = [ ] # list of files to test compliances
    files_to_download = [ ] # when files are at G-Node
    
    
    def setUp(self):
        self.local_test_dir = self.create_local_dir_if_not_exists()
        self.download_test_files_if_not_present()
        self.files_generated = [ ]
        self.generate_files_for_io_able_to_write()
        self.files_to_test.extend( self.files_generated )

    def create_local_dir_if_not_exists(self):
        shortname = self.ioclass.__name__.lower().strip('io')
        localdir = os.path.dirname(__file__)+'/files_for_tests'
        if not os.path.exists(localdir):
            os.mkdir(localdir)
        localdir = localdir +'/'+ shortname
        if not os.path.exists(localdir):
            os.mkdir(localdir)
        self.local_test_dir = localdir
        return localdir

    def download_test_files_if_not_present(self ):
        """
        Download file at G-node for testing
        url_for_tests is global at beginning of this file.
        
        """
        localdir = self.local_test_dir
        
        shortname = self.ioclass.__name__.lower().strip('io')
        url = url_for_tests+shortname
        for filename in self.files_to_download:
            make_all_directories(filename, localdir)
            
            localfile =  localdir+'/'+filename
            distantfile = url+'/'+filename
            
            if not os.path.exists(localfile):
                logging.info('Downloading %s here %s' % (distantfile, localfile))
                urllib.urlretrieve(distantfile, localfile)
    
    def generate_files_for_io_able_to_write(self):
        """
        
        """
        localdir = self.create_local_dir_if_not_exists()
        shortname = self.ioclass.__name__.lower().strip('io')
        higher = self.ioclass.supported_objects[0]
        
        if not(higher in self.ioclass.readable_objects and higher in self.ioclass.writeable_objects):
            return
        if not(higher == neo.Block or higher == neo.Segment):
            return
        # when io need external knowldge for writting or read such as sampling_rate (RawBinaryIO...)
        # the test is too much complex too design genericaly. 
        if higher in self.ioclass.read_params and len(self.ioclass.read_params[higher]) != 0 : return
        
        ob = generate_from_supported_objects(self.ioclass.supported_objects)
        
        if self.ioclass.mode == 'file':
            filename = localdir+'/Generated0_'+self.ioclass.__name__
            if len(self.ioclass.extensions)>=1:
                filename += '.'+self.ioclass.extensions[0]
            writer = self.ioclass(filename = filename)
            self.files_generated.append( filename )
        elif self.ioclass.mode == 'dir':
            dirname = localdir+'/Generated0_'+self.ioclass.__name__
            writer = self.ioclass(dirname = dirname)
            self.files_generated.append( dirname )
        else:
            return
        
        ob = generate_from_supported_objects(self.ioclass.supported_objects)
        if higher == neo.Block:
            writer.write_block(ob)
        elif higher == neo.Segment:
            writer.write_segment(ob)


    def test_write_then_read(self):
        """
        Test for IO that are able to write and read:
          1 - Generate a full schema with supported objects.
          2 - Write to a file
          3 - Read from the file
          4 - Check the hierachy
          5 - Check data
        
        Work only for IO for Block and Segment for the higher object (main cases).
        """
        localdir = self.create_local_dir_if_not_exists()
        shortname = self.ioclass.__name__.lower().strip('io')
        
        higher = self.ioclass.supported_objects[0]
        if not(higher in self.ioclass.readable_objects and higher in self.ioclass.writeable_objects):
            return
        if not(higher == neo.Block or higher == neo.Segment):
            return
        
        # when io need external knowldge for writting or read such as sampling_rate (RawBinaryIO...)
        # the test is too much complex too design genericaly. 
        if higher in self.ioclass.read_params and len(self.ioclass.read_params[higher]) != 0 : return
        
        if self.ioclass.mode == 'file':
            filename = localdir+'/Generated0_'+self.ioclass.__name__
            if len(self.ioclass.extensions)>=1:
                filename += '.'+self.ioclass.extensions[0]
            writer = self.ioclass(filename = filename)
            reader = self.ioclass(filename = filename)
        elif self.ioclass.mode == 'dir':
            dirname = localdir+'/Generated0_'+self.ioclass.__name__
            writer = self.ioclass(dirname = dirname)
            reader = self.ioclass(dirname = dirname)
        else:
            return
        
        ob = generate_from_supported_objects(self.ioclass.supported_objects)
        if higher == neo.Block:
            writer.write_block(ob)
            ob2 = reader.read_block()
        elif higher == neo.Segment:
            writer.write_segment(ob)
            ob2 = reader.read_segment()
        
        assert_same_sub_schema(ob, ob2)
        assert_neo_object_is_compliant(ob2)

    def test_read_then_write(self):
        """
        Test for IO that are able to read and write:
         1 - Read a file
         2 Write object set in another file
         3 Compare the 2 files hash
         
        """
        if self.hash_conserved_when_write_read:
            #TODO
            #localdir = self.create_local_dir_if_not_exists()
            #assert_file_contents_equal(a, b)
            pass


        
    def test_assert_readed_neo_object_is_compliant(self):
        """
        With downloaded files test neo compliance with: neo.test.tools.assert_neo_object_is_compliant
        
        """
        # This is for files presents at G-Node or generated
        for filename in self.files_to_test:
            filename = os.path.join(self.local_test_dir, filename)
            if self.ioclass.mode == 'file':
                r = self.ioclass(filename = filename)
            elif self.ioclass.mode == 'dir':
                r = self.ioclass(dirname = filename)
            else:
                continue
            ob = getattr(r, 'read_'+self.ioclass.supported_objects[0].__name__.lower())( cascade = True, lazy = False )
            assert_neo_object_is_compliant(ob)
            
    
    
    def test_readed_with_cascade_is_compliant(self):
        """
        This test reader with cascade = False should return empty children.
        """
        # This is for files presents at G-Node or generated
        for filename in self.files_to_test:
            filename = os.path.join(self.local_test_dir, filename)
            if self.ioclass.mode == 'file':
                r = self.ioclass(filename = filename)
            elif self.ioclass.mode == 'dir':
                r = self.ioclass(dirname = filename)
            else:
                continue
            ob = getattr(r, 'read_'+self.ioclass.supported_objects[0].__name__.lower())( cascade = False, lazy = False )
            
            assert_neo_object_is_compliant(ob)
            classname = ob.__class__.__name__
            if classname in one_to_many_reslationship:
                for childname in one_to_many_reslationship[classname]:
                    assert len(getattr(ob, childname.lower()+'s')) == 0, '%s reader with cascade = False should return empty children' % self.ioclass
        

    def test_readed_with_lazy_is_compliant(self):
        """
        This test reader with lazy = True : should return all Quantities and ndarray with size = 0.
        """
        # This is for files presents at G-Node or generated
        for filename in self.files_to_test:
            filename = os.path.join(self.local_test_dir, filename)
            if self.ioclass.mode == 'file':
                r = self.ioclass(filename = filename)
            elif self.ioclass.mode == 'dir':
                r = self.ioclass(dirname = filename)
            else:
                continue
            ob = getattr(r, 'read_'+self.ioclass.supported_objects[0].__name__.lower())( cascade = True, lazy = True )
            assert_sub_schema_is_lazy_loaded(ob)
            



def make_all_directories(filename, localdir):
    fullpath = os.path.join(localdir, os.path.dirname(filename))
    if os.path.dirname(filename) != '' and not os.path.exists(fullpath) :
        if not os.path.exists( os.path.dirname(fullpath)):
            make_all_directories(os.path.dirname(filename), localdir)
        os.mkdir(fullpath)
    
    

    
