"""Class to load and manipulate a saved population."""
import collections
import difflib
import emod_api.serialization.dtkFileTools as dft

from typing import Union

COUNTER = 0


class SerializedPopulation:
    """Opens the passed file and reads in all the nodes.

    Args:
        file: serialized population file

    Examples:
        Create an instance of SerializedPopulation::
            import emod_api.serialization.SerializedPopulation as SerPop
            ser_pop = SerPop.SerializedPopulation('state-00001.dtk')

     """

    def __init__(self, file: str):
        self.next_infection_suid = None
        self.next_infection_suid_initialized = False
        self.dtk = dft.read(file)

    @property
    def nodes(self):
        """All nodes.

        Examples:
            Delete number_of_ind individuals from node 0::
                node = ser_pop.nodes[0]
                del node.individualHumans[0:number_of_ind]

            Only keep individuals with a certain condition::
                node.individualHumans = [ind for ind in node.individualHumans if keep_fct(ind)]

            Change susceptibility of an individual::
                print(node.individualHumans[0].susceptibility)
                new_susceptibility = {"age": 101.01, "mod_acquire": 0}
                node.individualHumans[0].susceptibility.update(new_susceptibility)

            Copy individual[0] from node 0, change properties and add individual as new individual::
                import copy
                individual_properties = {"m_age": 1234}
                individual = copy.deepcopy(node.individualHumans[0])
                individual["suid"] = ser_pop.get_next_individual_suid(0)
                individual.update(individual_properties)
                ser_pop.nodes[0].individualHumans.append(individual)

            Infect an individual with an infection copied from another individual::
                import copy
                individual_0 = node.individualHumans[0]
                individual_1 = node.individualHumans[1]
                new_infection = copy.deepcopy(individual_0.infections[0])
                new_infection["suid"] = ser_pop.get_next_infection_suid()
                individual_1.infections.append(new_infection)
                individual_1.m_is_infected = True

        """
        return self.dtk.nodes

    def flush(self):
        """Save all made changes to the node(s)."""
        for idx in range(len(self.dtk.nodes)):
            self.dtk.nodes[idx] = self.dtk.nodes[idx]

    def write(self, output_file: str = "my_sp_file.dtk"):
        """Write the population to a file.

        Args:
            output_file: output file
        """
        self.flush()
        sim = self.dtk.simulation
        sim["infectionSuidGenerator"]["next_suid"] = self.get_next_infection_suid()
        self.dtk.simulation = sim

        print(f"Saving file {output_file}.")
        dft.write(self.dtk, output_file)

    def get_next_infection_suid(self):
        """Each infection needs a unique identifier, this function returns one."""
        sim = self.dtk.simulation
        if not self.next_infection_suid_initialized:
            self.next_infection_suid = sim["infectionSuidGenerator"]["next_suid"]
            self.next_infection_suid_initialized = True
        else:
            self.next_infection_suid["id"] = (
                self.next_infection_suid["id"]
                + sim["infectionSuidGenerator"]["numtasks"]
            )

        return dict(self.next_infection_suid)

    def get_next_individual_suid(self, node_id: int) -> dict:
        """Each individual needs a unique identifier, this function returns one.

        Args:
            node_id: The first parameter.

        Returns:
            The return value. True for success, False otherwise.

        Examples:
            To get a unique id for an individual::

                print(sp.get_next_individual_suid(0))
                {'id': 2}
        """
        suid = self.dtk.nodes[node_id]["m_IndividualHumanSuidGenerator"]["next_suid"]
        self.dtk.nodes[node_id]["m_IndividualHumanSuidGenerator"]["id"] = (
            suid["id"]
            + self.dtk.nodes[node_id]["m_IndividualHumanSuidGenerator"]["numtasks"]
        )
        return dict(suid)


# Some useful functions
def find(name: str,
         handle: Union[str, collections.Iterable],
         currentlevel: str = "dtk.nodes"):
    """Recursively searches for a paramters that matches or is close to name and prints out where to find it in the file.

    Args:
        name: the paramter you are looking for e.g. "age", "gender".
        handle: some iterable data structure, can be a list of
                nodes, a node, list of individuals, etc
        currentlevel: just a string to print out where the found item
                is located e.g. "dtk.nodes" or "dtk.node.individuals"

    Examples:
        What is the exact paramteter name used for the age of an individual?::

            SerPop.find("age", node)
            ...
            1998   Found in:  dtk.nodes.individualHumans[999].m_age
            1999   Found in:  dtk.nodes.individualHumans[999].susceptibility.age
            2000   Found in:  dtk.nodes.m_vectorpopulations[0].EggQueues[0].age
            2001   Found in:  dtk.nodes.m_vectorpopulations[0].EggQueues[1].age
            ...
    """
    global COUNTER
    if isinstance(handle, str) and difflib.get_close_matches(name, [handle], cutoff=0.6):
        print(COUNTER, "  Found in: ", currentlevel)
        COUNTER += 1
        return

    if isinstance(handle, str) or not isinstance(handle, collections.Iterable):
        return

    # key can be a string or on dict/list/..
    for idx, key in enumerate(handle):
        level = (
            currentlevel + "." + key
            if isinstance(key, str)
            else currentlevel + "[" + str(idx) + "]"
        )
        try:
            tmp = handle[key]
            if isinstance(tmp, collections.Iterable):
                find(name, key, level + "[]")
            else:
                find(name, key, level)
        except BaseException:
            # list or keys of a dict, works in all cases but misses objects in
            # dicts
            find(name, key, level)
        if isinstance(handle, dict):
            find(name, handle[key], level)  # check if string is key for a dict


def get_parameters(handle: Union[str, collections.Iterable],
                   currentlevel: str = "dtk.nodes"):
    """Return a set of all parameters in the serialized population file. Helpful to get an overview about what is in the serialized population file.

    Args:
        handle: some iterable data structure, can be a list of
                nodes, a node, list of individuals, etc
        currentlevel: just a string to print out where the found item
                is located e.g. "dtk.nodes" or "dtk.node.individuals
    Examples:
        Print all parameters in serialized population file::
            for n in sorted(SerPop.get_parameters(node)):
                print(n)
    """
    param = set()

    if isinstance(handle, str):
        param.add(currentlevel)
        return param

    if not isinstance(handle, collections.Iterable):
        return param

    for _, d in enumerate(handle):
        level = currentlevel + " " + d if isinstance(d, str) else currentlevel
        param.update(get_parameters(d, level))
        if isinstance(handle, dict):
            param.update(get_parameters(handle[d], level))

    return param
