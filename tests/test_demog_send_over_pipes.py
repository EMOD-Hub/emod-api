import os
import sys
import json
import emod_api.demographics.Demographics as Demog
import emod_api.demographics.PreDefinedDistributions as Distributions
import tempfile
import copy

thisplatform = sys.platform


class DemographicsTestMisc():
    large_demog = ""
    large_expected = ""

    @classmethod
    def setUpClass(cls):
        cls.create_large_demog(cls)

    def create_large_demog(cls):
        print('called once before any tests in class')
        # Large demographics object.
        num_node = 1000
        print("Creating big complex demographics.")
        cls.large_demog = Demog.from_params(tot_pop=10000000, num_nodes=num_node)

        for node_id in range(num_node):
            cls.large_demog.SetFertilityOverTimeFromParams(years_region1=100, years_region2=10, start_rate=0.3, inflection_rate=0.25, end_rate=0.1, node_ids=[node_id + 1])
            cls.large_demog.nodes[node_id].individual_attributes.age_distribution = Distributions.AgeDistribution_SEAsia
            cls.large_demog.nodes[node_id].individual_attributes.mortality_distribution = Distributions.SEAsia_Diag

        # Large Expected Results Dictionary
        cls.large_expected = cls.large_demog.to_dict()
        print(f"Total of nodes: {cls.large_expected['Metadata']['NodeCount']} ... file size is aprox 54 MB")

    @pytest.mark.skipif(thisplatform.startswith("win"), "Not valid on Windows")
    def test_linux_send_over_file(self):
        # FUNCTIONAL TEST CASE: Call Send method using a valid File Name
        # EXPECTED: Valid file name is processed and generated objects are the same.

        tmpfile = tempfile.NamedTemporaryFile().name
        print("Transfer data from another module using files.")

        # Gets a copy of a large
        mydemog = copy.copy(self.large_demog)

        with open(tmpfile, "w") as ipc:
            # calling the Feature Under Test
            mydemog.send(ipc)

        # If the process worked, we open the generated file.
        with open(tmpfile, "r") as ipc:
            read_data = ipc.read()

        # Generate dictionaries to compare.
        expected = self.large_expected
        actual = json.loads(read_data)

        print("Validating now Expected versus Actual demog objects")

        # VALIDATION:
        self.assertDictEqual(expected, actual, "Demographic dict objects are different")
        print("...Validation Done...")
        os.remove(tmpfile)

    @pytest.mark.skipif(thisplatform.startswith("win"), "Not valid on Windows")
    def test_linux_send_over_pipe_basic(self):
        # FUNCTIONAL TEST CASE: Call to Send method using a valid Pipe Number
        # EXPECTED: Valid pipe number is handled and demographics file is processed.

        print("The child will write text to a pipe and ")
        print("the parent will read the text written by child...")

        # file descriptors r, w for reading and writing
        r, w = os.pipe()

        # generate a large Demographics object
        mydemog = self.large_demog

        # Fork the main process
        processid = os.fork()

        if (processid < 0):
            self.fail("Failed to generate child process: os.fork()")
        elif (processid > 0):
            # This is the parent process
            print("Parent process id:", processid)
            # Closes file descriptor w
            os.close(w)  # Closes the child connection
            # Reader - after the pipe
            r = os.fdopen(r)
            print("\tParent reading")
            contents = r.read()
            sys.stdout.flush()
            r.close()
            actual = json.loads(contents)
            expected = self.large_expected
            self.assertDictEqual(expected, actual, "\n Demog.send() - using pipes - FAILED - Demographic dict objects are different")
        elif (processid == 0):
            print("Child process id:", processid)  # Should be zero
            os.close(r)  # Closes the parent connection
            w = os.fdopen(w, 'w')
            print("\tChild writing")
            # calling the Feature Under Test
            mydemog.send(w, return_from_forked_sender=True)
            sys.stdout.flush()
            w.close()
            print("Child closing")

        if (processid > 0):
            print("Parent (main) method - Done..")
        elif (processid == 0):
            print("Child method - Done..")

    @pytest.mark.skipif(thisplatform.startswith("win"), "Not valid on Windows")
    def test_linux_send_over_named_pipe(self):
        # FUNCTIONAL TEST CASE: Call to Send method using a valid Named Pipe

        print("Creating big complex demographics.")
        mydemog = self.large_demog

        tmpfile = ""
        tmpfile = tempfile.NamedTemporaryFile().name

        # FIFOs are named pipe which can be accessed like other regular files. This method only create FIFO
        # but don’t open it and the created FIFO does exist until they are deleted.
        # FIFOs are generally us as rendezvous between client and “server type processes.

        os.mkfifo(tmpfile)
        process_id = os.fork()

        if process_id:
            # This is the parent process
            # reader
            fifo_reader = open(tmpfile, "r")
            contents = fifo_reader.read()

            sys.stdout.flush()
            actual = json.loads(contents)

            expected = self.large_expected

            # VALIDATION:
            self.assertDictEqual(expected, actual, "\n Demog.send() - using Named Pipes (os.mkfifo) - FAILED - Demographic dict objects are different")
            print("\tDone with validation...")
            fifo_reader.close()
            print("Parent (reader) closing")

        elif (process_id == 0):
            print("Child process id:", process_id)  # Should be zero
            print("\tChild writing")
            # tmpfile = named pipe.
            mydemog.send(tmpfile, return_from_forked_sender=True)  # calling the Feature Under Test
            sys.stdout.flush()
            print("Child (sender / writter) removing")
            os.remove(tmpfile)
