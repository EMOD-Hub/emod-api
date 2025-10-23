import sender
import os
import json
import pdb

def send_over_file():
    print( "Transfer data from another module using files." )
    import tempfile
    tmpfile = tempfile.NamedTemporaryFile().name
    # We create the file handle and we pass it to the other module which writes to it.
    with open( tmpfile, "w" ) as ipc:
        sender.send( ipc )

    # Assuming the above worked, we read the file from disk -- and print it for proof.
    with open( tmpfile, "r" ) as ipc:
        read_data = ipc.read()
        #print( read_data )

    print( f"TBD: Add code to check for valid demographics.json at {tmpfile}." )
    os.remove( tmpfile )

def send_over_pipe():
    print( "Transfer data from another module using 'regular' pipe." )
    r,w = os.pipe()
    process_id = os.fork()
    if process_id:
        os.close(r)
        sender.send( w )
    else:
        os.close( w )
        rr = os.fdopen( r )
        read_data = rr.read()
        #print( read_data )
        rr.close()
        #os.close( r )

def send_over_named_pipe():
    # Named pipe solution 1, uses os.open, not open.
    import tempfile
    tmpfile = tempfile.NamedTemporaryFile().name
    os.mkfifo( tmpfile )

    fifo_reader = os.open( tmpfile, os.O_RDONLY |  os.O_NONBLOCK )
    fifo_writer = os.open( tmpfile, os.O_WRONLY |  os.O_NONBLOCK )
    sender.send( fifo_writer )
    os.close( fifo_writer )
    data = os.read( fifo_reader, int(1e6) )
    #print( data )

def send_over_named_pipe2():
    """
    Using os.write() needs to send a max of 2^16=65536 bytes at a time and leave the user
    to handle the complexity. Using write on the file descriptor opened by open avoids this
    but requires forking because both open calls block until both have been called.
    """
    import tempfile
    tmpfile = tempfile.NamedTemporaryFile().name
    os.mkfifo( tmpfile )

    process_id = os.fork()
    # parent stays here, child is the sender
    if process_id:
        # reader
        fifo_reader = open( tmpfile, "r" )
        data = fifo_reader.read()
        fifo_reader.close()
    else:
        # writer
        sender.send( tmpfile )
    #print( data )
    with open( "schema.json", "w" ) as json_file:
        json.dump( json.loads(data), json_file )

def send_demog_over_named_pipe2( number=1 ):
    import emod_api.demographics.demographics as Demog
    import emod_api.demographics.PreDefinedDistributions as Distributions

    print( "Creating big complex demographics." )
    mydemog = Demog.from_params( num_nodes=10000 )
    age_distribution = Distributions.AgeDistribution_SEAsia 
    mort_distribution = Distributions.SEAsia_Diag
    for node_id in range(10000):
        mydemog.SetAgeDistribution(age_distribution, [node_id+1])
        mydemog.SetMortalityDistribution(mort_distribution, [node_id+1])
        mydemog.SetFertilityOverTimeFromParams(years_region1=100,years_region2=10,start_rate=0.3,inflection_rate=0.25,end_rate=0.1, node_ids=[node_id+1])

    print( "Serialize and send." )
    for _ in range(number):
        print( "Start asking existing demographics to send..." )
        import tempfile
        tmpfile = tempfile.NamedTemporaryFile().name
        os.mkfifo( tmpfile )

        process_id = os.fork()
        # parent stays here, child is the sender
        if process_id:
            # reader
            fifo_reader = open( tmpfile, "r" )
            data = fifo_reader.read()
            fifo_reader.close()
        else:
            # writer
            mydemog.send( tmpfile )
        print( "demographics received..." )

    print( "Received demographics. Writing to disk." )
    with open( "demographics.json", "w" ) as demog_file:
        json.dump( json.loads(data), demog_file )

def send_demog_over_named_pipe():
    # Archive, ignore
    import emod_api.demographics.demographics as Demog
    import emod_api.demographics.PreDefinedDistributions as Distributions

    import tempfile
    tmpfile = tempfile.NamedTemporaryFile().name
    os.mkfifo( tmpfile )

    fifo_reader = os.open( tmpfile, os.O_RDONLY |  os.O_NONBLOCK ) # have to open reader first

    def tell_demog_to_send( demog ):
        fifo_writer = os.open( tmpfile, os.O_WRONLY |  os.O_NONBLOCK )
        demog.send( fifo_writer )
        os.close( fifo_writer )

    mydemog = Demog.from_params( num_nodes=10000 )
    age_distribution = Distributions.AgeDistribution_SEAsia 
    mort_distribution = Distributions.SEAsia_Diag
    for node_id in range(10000):
        mydemog.SetAgeDistribution(age_distribution, [node_id+1])
        mydemog.SetMortalityDistribution(mort_distribution, [node_id+1])
        mydemog.SetFertilityOverTime(100,10,1860,0.3,0.25,0.1, [node_id+1])

    # TBD: Add lots of stuff to the demographics file first
    tell_demog_to_send( mydemog )

    data = os.read( fifo_reader, int(1e10) )
    print( "Received demographics." )

    #print( data ) # just to prove we got it.

    with open( "demographics.json", "w" ) as demog_file:
        json.dump( json.loads(data), demog_file )


#send_over_file()
#send_over_pipe()
#send_over_named_pipe()
#send_over_named_pipe2()
#send_demog_over_named_pipe()
send_demog_over_named_pipe2(number=100)
