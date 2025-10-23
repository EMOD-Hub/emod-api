import os, sys
import json
import unittest
import emod_api.demographics.Demographics as Demog
import emod_api.demographics.Node as Node
import emod_api.demographics.DemographicsTemplates as DT
# import manifest 
from datetime import date
import pandas as pd
import numpy as np
from emod_api.demographics.PropertiesAndAttributes import IndividualAttributes, IndividualProperty, IndividualProperties, NodeAttributes
import emod_api.demographics.PreDefinedDistributions as Distributions
import tempfile
from multiprocessing import Process, Pipe
import copy
import platform
thisplatform = sys.platform

class DemographicsTestMisc(unittest.TestCase):
    short_expected = ""
    short_demog=""
    large_demog =""
    large_expected=""

    @classmethod
    def setUpClass(cls):
        cls.create_large_demog(cls)

    def create_large_demog(cls):
        print ('called once before any tests in class')
        # Large demographics object.
        print( "Creating big complex demographics." )
        cls.large_demog =Demog.from_params(tot_pop=10000000, num_nodes=10000)
        age_distribution = Distributions.AgeDistribution_SEAsia 
        mort_distribution = Distributions.SEAsia_Diag
        for node_id in range(10000):
            cls.large_demog.SetAgeDistribution(age_distribution, [node_id+1])
            cls.large_demog.SetMortalityDistribution(mort_distribution, [node_id+1])
            cls.large_demog.SetFertilityOverTimeFromParams(years_region1=100,years_region2=10,start_rate=0.3,inflection_rate=0.25,end_rate=0.1, node_ids=[node_id+1])
        
        # Large Expected Results Dictionary
        cls.large_expected = cls.large_demog.to_dict()
        print(f"Total of nodes: {cls.large_expected['Metadata']['NodeCount']} ... file size is aprox 54 MB")
              
    def setUp(self) -> None:
        print(f"\n{self._testMethodName} started...")
        current_directory = os.path.dirname(os.path.realpath(__file__))
        demo_folder = os.path.join(current_directory, 'data', 'demographics')
        self.out_folder = demo_folder

        # Creating Short file demog file.  
        self.create_short_demog()

    def tearDown(self) -> None:
        print(f"\n{self._testMethodName} ...DONE...")

    def create_short_demog(self):
        # Creating short demog file.  
        print(f"Creating demographic expected object for {self._testMethodName}")
        short_expected_demog = ""
        short_expected_demog =Demog.from_params(tot_pop=10000000, num_nodes=444)
        
        # short Expected dictionary
        self.short_expected = short_expected_demog.to_dict()

    @unittest.skipIf(thisplatform.startswith("win"), "Not valid on Windows")
    def test_linux_send_over_file(self):
        # FUNCTIONAL TEST CASE: Call Send method using a valid File Name
        # EXPECTED: Valid file name is processed and generated objects are the same.

        tmpfile = tempfile.NamedTemporaryFile().name
        print( "Transfer data from another module using files." )

        #mydemog = copy.deepcopy()   #<<<==== verify if this is a problem, ideally I would use a deepcopy.
        # Gets a copy of a large 
        mydemog = copy.copy(self.large_demog)

        with open( tmpfile, "w" ) as ipc:
            # calling the Feature Under Test
            mydemog.send( ipc )

        # If the process worked, we open the generated file.
        with open( tmpfile, "r" ) as ipc:
            read_data = ipc.read()

        #Generate dictionaries to compare.
        expected = self.large_expected
        actual = json.loads(read_data)

        print("Validating now Expected versus Actual demog objects")
        
        # VALIDATION:
        self.assertDictEqual(expected, actual, "Demographic dict objects are different")
        print("...Validation Done...")
        os.remove( tmpfile )

    @unittest.skipIf(thisplatform.startswith("win"), "Not valid on Windows")
    def test_linux_send_over_pipe_basic(self):
        # FUNCTIONAL TEST CASE: Call to Send method using a valid Pipe Number
        # EXPECTED: Valid pipe number is handled and demographics file is processed.


        print( "The child will write text to a pipe and ")
        print( "the parent will read the text written by child...")

        # file descriptors r, w for reading and writing
        r, w = os.pipe() 
        
        # generate a large Demographics object
        mydemog = self.large_demog

        # Fork the main process
        processid = os.fork()

        if processid<0:
            self.fail("Failed to generate child process: os.fork()")
        elif processid>0:
            # This is the parent process 
            print("Parent process id:", processid)
            # Closes file descriptor w
            os.close(w)     # Closes the child connection
            # Reader - after the pipe
            r = os.fdopen(r)
            print( "\tParent reading")
            contents = r.read()
            #print ("text =", contents   )
            sys.stdout.flush()
            r.close()
            actual = json.loads(contents)
            # print(actual)
            expected = self.large_expected
            # print(">--<"*10)
            # print(expected)
            #self.maxDiff = None
            self.assertDictEqual(expected, actual, "\n Demog.send() - using pipes - FAILED - Demographic dict objects are different")
            
        elif processid == 0:
            print("Child process id:", processid)  # Should be zero
            os.close(r)     # Closes the parent connection
            w = os.fdopen(w, 'w')
            print ("\tChild writing")
            #  calling the Feature Under Test
            mydemog.send(w,return_from_forked_sender=True)
            sys.stdout.flush()
            w.close()
            print ("Child closing")
            #sys.exit()
            
        if processid>0:
            print("Parent (main) method - Done..")
        elif processid==0:
            print("Child method - Done..")
            
    @unittest.skipIf(thisplatform.startswith("win"), "Not valid on Windows")  
    def test_linux_send_over_named_pipe(self):
        # FUNCTIONAL TEST CASE: Call to Send method using a valid Named Pipe
        
        print( "Creating big complex demographics." )
        mydemog = self.large_demog

        tmpfile = ""
        tmpfile = tempfile.NamedTemporaryFile().name

        #FIFOs are named pipe which can be accessed like other regular files. This method only create FIFO
        #  but don’t open it and the created FIFO does exist until they are deleted. 
        # FIFOs are generally us as rendezvous between client and “server type processes.

        os.mkfifo( tmpfile )
        process_id = os.fork()

        if process_id:
            # This is the parent process 
            # reader
            fifo_reader = open( tmpfile, "r" )
            contents = fifo_reader.read()
            #print ( contents   )

            sys.stdout.flush()
            actual = json.loads(contents)
            # print(actual)

            expected = self.large_expected
            # print(expected)

            # VALIDATION:
            self.assertDictEqual(expected, actual, "\n Demog.send() - using Named Pipes (os.mkfifo) - FAILED - Demographic dict objects are different")
            print("\tDone with validation...")
            fifo_reader.close()
            print("Parent (reader) closing")

        elif process_id==0:
            print("Child process id:", process_id)  # Should be zero
            
            print ("\tChild writing")
            # tmpfile = named pipe.
            mydemog.send(tmpfile, return_from_forked_sender=True)    #  calling the Feature Under Test 
            sys.stdout.flush()
            print ("Child (sender / writter) removing")
            os.remove( tmpfile )
            #sys.exit()
 
if __name__ == '__main__':
    unittest.main()
