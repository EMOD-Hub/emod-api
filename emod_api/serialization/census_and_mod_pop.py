import emod_api.serialization.serialized_population as sp


def change_ser_pop(input_serpop_path, mod_fn=None, save_file_path=None):
    """
    This function loads a serialization population file, iterates over each person, calls a
    user-provided callback with each individuals, and saves the population as manipulated by
    the user.

    The mod function can act at will on the population object. There are no checks.

    The new file is saved to a name provided by user. Interactive if none provided to function.

    Assuming a single node file for now.
    """
    # print( f"change_ser_pop called with 'path'={input_serpop_path}, 'save_file_path'={save_file_path}." )

    """
    if not os.path.exists( input_serpop_path ):
        print( f"Couldn't find specified serialized population file: {input_serpop_path}." )
        sys.exit(0)
    """

    if mod_fn is None:
        print("Calling with no mod_fn serves to test whether the .dtk input file can be loaded, but makes no change.")

    ser_pop = sp.SerializedPopulation(input_serpop_path)

    if len(ser_pop.nodes) > 1:
        print("This code currently operates properly on single-node population files. This file has {len(ser_pop)} nodes.")
        return

    node_0 = ser_pop.nodes[0]
    pop_size = len(node_0["individualHumans"])
    print(f"Found {pop_size} people -- or agents -- in serialized population file.")

    for person in range(len(node_0["individualHumans"])):
        # 1) Figure out what age bucket this person is in.
        if "individualHumans" not in node_0:
            print("ERROR: Failed to find 'individualHumans' in node_0 serialized population input.")

        if mod_fn:
            node_0["individualHumans"][person] = mod_fn(node_0["individualHumans"][person])

    if mod_fn:
        if not save_file_path:
            save_file_path = input("Enter filename of new serialized population (e.g., my_sp_file.dtk): ")
    ser_pop.write(save_file_path)
