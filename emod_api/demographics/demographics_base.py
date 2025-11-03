import json
import math
import os
import pathlib
import sys
import tempfile
import warnings
from collections import Counter
from functools import partial
from typing import List, Iterable, Any, Dict, Union

import numpy as np
import pandas as pd
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from emod_api.demographics import demographics_templates as DT
from emod_api.demographics.base_input_file import BaseInputFile
from emod_api.demographics.demographics_templates import CrudeRate, YearlyRate
from emod_api.demographics.node import Node
from emod_api.demographics.age_distribution_old import AgeDistributionOld as AgeDistribution
from emod_api.demographics.demographic_exceptions import InvalidNodeIdException
from emod_api.demographics.mortality_distribution_old import MortalityDistributionOld as MortalityDistribution
from emod_api.migration import migration


class DemographicsBase(BaseInputFile):
    """
    Base class for :py:obj:`emod_api:emod_api.demographics.Demographics` and
        :py:obj:`emod_api:emod_api.demographics.DemographicsOverlay`.
    """

    DEFAULT_NODE_NAME = 'default_node'

    class UnknownNodeException(ValueError):
        pass

    class DuplicateNodeIdException(Exception):
        pass

    class DuplicateNodeNameException(Exception):
        pass

    def __init__(self, nodes: List[Node], idref: str, default_node: Node = None):
        super().__init__(idref=idref)
        # TODO: node ids should be required to be UNIQUE to prevent later failures when running EMOD. Any update to
        #  self.nodes should trigger a check/error if needed.
        self.nodes = nodes
        self.implicits = list()
        self.migration_files = list()

        # verify that the provided non-default nodes have ids > 0
        for node in self.nodes:
            if node.id <= 0:
                raise InvalidNodeIdException(f"Non-default nodes must have integer ids > 0 . Found id: {node.id}")

        # Build the default node if not provided
        metadata = self.generate_headers()
        if default_node is None:  # use raw attribute, current malaria/other disease style
            # currently all non-HIV disease route
            self.default_node = None
            self.metadata = None
            self.raw = {"Defaults": dict(), "Metadata": metadata}
            self.raw["Defaults"]["NodeAttributes"] = dict()
            self.raw["Defaults"]["IndividualAttributes"] = dict()
            self.raw["Defaults"]["NodeID"] = 0
            self.raw["Defaults"]["IndividualProperties"] = list()
            # TODO: remove the following setting of birth_rate on the default node once this EMOD binary issue is fixed
            #  https://github.com/InstituteforDiseaseModeling/DtkTrunk/issues/4009
            self.raw["Defaults"]["NodeAttributes"]["BirthRate"] = 0
        else:  # HIV style
            self.default_node = default_node
            self.default_node.name = self.DEFAULT_NODE_NAME
            if self.default_node.id != 0:
                raise InvalidNodeIdException(f"Default nodes must have an id of 0. It is {self.default_node.id} .")
            self.metadata = metadata
            # TODO: remove the following setting of birth_rate on the default node once this EMOD binary issue is fixed
            #  https://github.com/InstituteforDiseaseModeling/DtkTrunk/issues/4009
            self.get_node_by_id(node_id=0).birth_rate = 0

        # enforce unique node ids and names
        self.verify_demographics_integrity()

    def _select_node_dicts(self, node_ids=None):
        if node_ids is None:
            node_dicts = [self.raw['Defaults']]
        else:
            node_dicts = [node_dict for node_dict in self.raw["Nodes"] if node_dict["NodeID"] in node_ids]
        return node_dicts

    # TODO: example of node-node update() call, make sure this still works after changing Updateable.update()
    # Or do we really need this?? (only used in tests or maybe emodpy-malaria; don't know for the latter)
    def apply_overlay(self,
                      overlay_nodes: list):
        """
        :param overlay_nodes: Overlay list of nodes over existing nodes in demographics
        :return:
        """
        map_ids_overlay = {}  # map node_id to overlay node_id
        for node in overlay_nodes:
            map_ids_overlay[node.forced_id] = node

        for index, node in enumerate(self.nodes):
            if map_ids_overlay.get(node.forced_id):
                self.nodes[index].update(map_ids_overlay[node.forced_id])

    def send(self,
             write_to_this: Union[int, str, os.PathLike],
             return_from_forked_sender: bool = False):
        """
        Write data to a file descriptor as specified by the caller. It must be a pipe,
        a filename, or a file 'handle'

        Args:
            write_to_this: File pointer, file path, or file handle.
            return_from_forked_sender: Defaults to False. Only applies to pipes.
                Set to true if caller will handle exiting of fork.

        Example::

            1) Send over named pipe client code
            # Named pipe solution 1, uses os.open, not open.
            import tempfile
            tmpfile = tempfile.NamedTemporaryFile().name
            os.mkfifo(tmpfile)

            fifo_reader = os.open(tmpfile, os.O_RDONLY |  os.O_NONBLOCK)
            fifo_writer = os.open(tmpfile, os.O_WRONLY |  os.O_NONBLOCK)
            demog.send(fifo_writer)
            os.close(fifo_writer)
            data = os.read(fifo_reader, int(1e6))

            2) Send over named pipe client code version 2 (forking)
            import tempfile
            tmpfile = tempfile.NamedTemporaryFile().name
            os.mkfifo(tmpfile)

            process_id = os.fork()
            # parent stays here, child is the sender
            if process_id:
                # reader
                fifo_reader = open(tmpfile, "r")
                data = fifo_reader.read()
                fifo_reader.close()
            else:
                # writer
                demog.send(tmpfile)

            3) Send over file.
            import tempfile
            tmpfile = tempfile.NamedTemporaryFile().name
            # We create the file handle and we pass it to the other module which writes to it.
            with open(tmpfile, "w") as ipc:
                demog.send(ipc)

            # Assuming the above worked, we read the file from disk.
            with open(tmpfile, "r") as ipc:
                read_data = ipc.read()

            os.remove(tmpfile)

        Returns:

        """

        if type(write_to_this) is int:
            # Case 1: gonna say this is a pipe
            data_as_bytes = json.dumps(self.to_dict()).encode('utf-8')
            # Sending demographics to pipe
            try:
                os.write(write_to_this, data_as_bytes)
            except Exception as ex:
                raise ValueError(str(ex) + "\n\nException encountered while trying to write demographics json to "
                                           "inferred pipe handle.")
        elif type(write_to_this) is str:
            # Case 2: we've been passed a filepath ot use to open a named pipe
            # print("Serializing demographics object to json string.")
            data_as_str = json.dumps(self.to_dict())
            # Sending demographics to named pipe
            try:
                fifo_writer = open(write_to_this, "w")
                fifo_writer.write(data_as_str)
                fifo_writer.close()
                if return_from_forked_sender:
                    return
                else:
                    sys.exit()
            except Exception as ex:
                raise ValueError(str(ex) + f"\n\nException encountered while trying to write demographics json to pipe "
                                           f"based on name {write_to_this}.")
        else:
            # Case 3: with(open(some_path)) as write_to_this
            try:
                json.dump(self.to_dict(), write_to_this)
            except Exception as ex:
                raise ValueError(str(ex) + f"\n\nException encountered while trying to write demographics json to "
                                           f"inferred file based on {write_to_this}.")

    @property
    def node_ids(self):
        """
        Return the list of (geographic) node ids.
        """
        return [node.id for node in self.nodes]

    @property
    def node_count(self):
        """
        Return the number of (geographic) nodes.
        """
        message = "node_count is a deprecated property of Node objects, use len(demog.nodes) instead."
        warnings.warn(message=message, category=DeprecationWarning, stacklevel=2)
        return len(self.nodes)

    # TODO: this is deprecated because it is (was) odd, searching by id THEN name.
    #  Remove and replace with get_node_by_name() (by_id implemented already, below)
    #  https://github.com/InstituteforDiseaseModeling/emod-api/issues/690
    def get_node(self, nodeid: int) -> Node:
        """
        Return the node with node.id equal to nodeid.

        Args:
            nodeid: an id to use in retrieving the requested Node object. None or 0 for 'the default node'.

        Returns:
            a Node object
        """
        message = "get_node() is a deprecated function of Node objects, use get_node_by_id() instead. " \
                  "(e.g. demographics.get_node_by_id(node_id=4))"
        warnings.warn(message=message, category=DeprecationWarning, stacklevel=2)
        return self.get_node_by_id(node_id=nodeid)

    def verify_demographics_integrity(self):
        """
        One stop shopping for making sure a demographics object doesn't have known invalid settings.
        """
        self._verify_node_id_uniqueness()
        self._verify_node_name_uniqueness()

    @staticmethod
    def _duplicates_check(items: Iterable[Any]) -> List[Any]:
        """
        Simple function that detects and returns the duplicates in an provide iterable.
        Args:
            items: a collection of items to search for duplicates

        Returns: a list of duplicated items from the provided list
        """
        usage_count = Counter(items)
        return [item for item in usage_count.keys() if usage_count[item] > 1]

    def _verify_node_id_uniqueness(self):
        nodes = self._all_nodes
        node_ids = [node.id for node in nodes]
        duplicate_items = self._duplicates_check(items=node_ids)
        if len(duplicate_items) > 0:
            duplicate_items_str = [str(item) for item in duplicate_items]
            duplicates_str = ", ".join(duplicate_items_str)
            raise self.DuplicateNodeIdException(f"Duplicate node ids detected: {duplicates_str}")

    def _verify_node_name_uniqueness(self):
        nodes = self._all_nodes
        node_names = [node.name for node in nodes]
        duplicate_items = self._duplicates_check(items=node_names)
        if len(duplicate_items) > 0:
            duplicate_items_str = [str(item) for item in duplicate_items]
            duplicates_str = ", ".join(duplicate_items_str)
            raise self.DuplicateNodeNameException(f"Duplicate node names detected: {duplicates_str}")

    @property
    def _all_nodes(self) -> List[Node]:
        # only HIV is using a default node object right now, malaria currently uses self.raw
        # None protection if users are using self.raw default node access
        default_node = [] if self.default_node is None else [self.default_node]
        all_nodes = self.nodes + default_node
        return all_nodes

    @property
    def _all_node_names(self) -> List[int]:
        return [node.name for node in self._all_nodes]

    @property
    def _all_nodes_by_name(self) -> Dict[int, Node]:
        return {node.name: node for node in self._all_nodes}

    @property
    def _all_node_ids(self) -> List[int]:
        return [node.id for node in self._all_nodes]

    @property
    def _all_nodes_by_id(self) -> Dict[int, Node]:
        return {node.id: node for node in self._all_nodes}

    def get_node_by_id(self, node_id: int) -> Node:
        """
        Returns the Node object requested by its node id.

        Args:
            node_id: a node_id to use in retrieving the requested Node object. None or 0 for 'the default node'.

        Returns:
            a Node object
        """
        return list(self.get_nodes_by_id(node_ids=[node_id]).values())[0]

    def get_nodes_by_id(self, node_ids: List[int]) -> Dict[int, Node]:
        """
        Returns the Node objects requested by their node id.

        Args:
            node_ids: a list of node ids to use in retrieving Node objects. None or 0 for 'the default node'.

        Returns:
            a dict with id: node entries
        """
        # replace a None id (default node) request with 0
        if node_ids is None:
            node_ids = [0]
        if None in node_ids:
            node_ids.remove(None)
            node_ids.append(0)

        missing_node_ids = [node_id for node_id in node_ids if node_id not in self._all_node_ids]
        if len(missing_node_ids) > 0:
            msg = ', '.join([str(node_id) for node_id in missing_node_ids])
            raise self.UnknownNodeException(f"The following node id(s) were requested but do not exist in this demographics "
                                            f"object:\n{msg}")
        requested_nodes = {node_id: node for node_id, node in self._all_nodes_by_id.items() if node_id in node_ids}
        return requested_nodes

    def get_node_by_name(self, node_name: str) -> Node:
        """
        Returns the Node object requested by its node name.

        Args:
            node_name: a node_name to use in retrieving the requested Node object. None for 'the default node'.

        Returns:
            a Node object
        """
        return list(self.get_nodes_by_name(node_names=[node_name]).values())[0]

    def get_nodes_by_name(self, node_names: List[str]) -> Dict[str, Node]:
        """
        Returns the Node objects requested by their node name.

        Args:
            node_names: a list of node names to use in retrieving Node objects. None for 'the default node'.

        Returns:
            a dict with name: node entries
        """
        # replace a None name (default node) request with the default node's name
        if node_names is None:
            node_names = [self.default_node.name]
        if None in node_names:
            node_names.remove(None)
            node_names.append(self.default_node.name)

        missing_node_names = [node_name for node_name in node_names if node_name not in self._all_node_names]
        if len(missing_node_names) > 0:
            msg = ', '.join([str(node_name) for node_name in missing_node_names])
            raise self.UnknownNodeException(f"The following node name(s) were requested but do not exist in this demographics "
                                            f"object:\n{msg}")
        requested_nodes = {node_name: node for node_name, node in self._all_nodes_by_name.items()
                           if node_name in node_names}
        return requested_nodes

    def set_demographics_filenames(self, file_names):
        """
        Set paths to demographic file.

        Args:
            file_names: Paths to demographic files.
        """
        if self.implicits is not None:
            self.implicits.append(partial(DT._set_demographic_filenames, file_names=file_names))

    def SetDefaultIndividualAttributes(self):
        """
        NOTE: This is very Measles-ish. We might want to move into MeaslesDemographics
        """
        warnings.warn('SetDefaultIndividualAttributes() is deprecated. Default nodes should now be represented by Node '
                      'objects and passed to the Demographics object during the constructor call. They can be modified '
                      'afterward, if needed.',
                      DeprecationWarning, stacklevel=2)
        self.raw['Defaults']['IndividualAttributes'] = {}
        DT.NoInitialPrevalence(self)
        # Age distribution from UNWPP
        DT.AgeStructureUNWPP(self)
        # Mortality rates carried over from Nigeria DHS
        DT.MortalityStructureNigeriaDHS(self)
        DT.DefaultSusceptibilityDistribution(self)

    def SetMinimalNodeAttributes(self):
        warnings.warn('SetMinimalNodeAttributes() is deprecated. Default nodes should now be represented by Node '
                      'objects and passed to the Demographics object during the constructor call. They can be modified '
                      'afterward, if needed.',
                      DeprecationWarning, stacklevel=2)
        self.SetDefaultNodeAttributes(birth=False)

    # WB is births per 1000 pop per year
    # DTK is births per person per day.
    def SetBirthRate(self,
                     birth_rate: float,
                     node_ids: List = None):
        """
        Set Default birth rate to birth_rate. Turn on Vital Dynamics and Births implicitly.
        """
        warnings.warn('SetBirthRate() is deprecated. Default nodes should now be represented by Node '
                      'objects and passed to the Demographics object during the constructor call. They can be modified '
                      'afterward, if needed.',
                      DeprecationWarning, stacklevel=2)
        if type(birth_rate) is float or type(birth_rate) is int:
            birth_rate = CrudeRate(birth_rate)
        dtk_birthrate = birth_rate.get_dtk_rate()
        if node_ids is None:
            self.raw['Defaults']['NodeAttributes'].update({
                "BirthRate": dtk_birthrate
            })
        else:
            for node_id in node_ids:
                self.get_node_by_id(node_id=node_id).birth_rate = dtk_birthrate
        self.implicits.append(DT._set_population_dependent_birth_rate)

    def SetMortalityRate(self,
                         mortality_rate: CrudeRate, node_ids: List[int] = None):
        """
        Set constant mortality rate to mort_rate. Turn on Enable_Natural_Mortality implicitly.
        """
        warnings.warn('SetMortalityRate() is deprecated. Please use the emodpy Demographics method: '
                      'set_mortality_distribution()', DeprecationWarning, stacklevel=2)

        # yearly_mortality_rate = YearlyRate(mortality_rate)
        if type(mortality_rate) is float or type(mortality_rate) is int:
            mortality_rate = CrudeRate(mortality_rate)
        mortality_rate = mortality_rate.get_dtk_rate()
        if node_ids is None:
            # setting = {"MortalityDistribution": DT._ConstantMortality(yearly_mortality_rate).to_dict()}
            setting = {"MortalityDistribution": DT._ConstantMortality(mortality_rate).to_dict()}
            self.SetDefaultFromTemplate(setting)
        else:
            for node_id in node_ids:
                # distribution = DT._ConstantMortality(yearly_mortality_rate)
                distribution = DT._ConstantMortality(mortality_rate)
                self.get_node_by_id(node_id=node_id)._set_mortality_complex_distribution(distribution)

        if self.implicits is not None:
            self.implicits.append(DT._set_mortality_age_gender)

    def SetMortalityDistribution(self, distribution: MortalityDistribution = None,
                                 node_ids: List[int] = None):
        """
        Set a default mortality distribution for all nodes or per node. Turn on Enable_Natural_Mortality implicitly.

        Args:
            distribution: distribution
            node_ids: a list of node_ids

        Returns:

        """
        warnings.warn('SetMortalityDistribution() is deprecated. Please use the emodpy Demographics method: '
                      'set_mortality_distribution()', DeprecationWarning, stacklevel=2)
        if node_ids is None:
            self.raw["Defaults"]["IndividualAttributes"]["MortalityDistribution"] = distribution.to_dict()
        else:
            for node_id in node_ids:
                self.get_node_by_id(node_id=node_id)._set_mortality_complex_distribution(distribution)

        if self.implicits is not None:
            self.implicits.append(DT._set_mortality_age_gender)

    def SetMortalityDistributionFemale(self, distribution: MortalityDistribution = None,
                                       node_ids: List[int] = None):
        """
        Set a default female mortality distribution for all nodes or per node. Turn on Enable_Natural_Mortality
            implicitly.

        Args:
            distribution: distribution
            node_ids: a list of node_ids

        Returns:

        """
        warnings.warn('SetMortalityDistributionFemale() is deprecated. Please use the emodpy Demographics method: '
                      'set_mortality_distribution()', DeprecationWarning, stacklevel=2)

        if node_ids is None:
            self.raw["Defaults"]["IndividualAttributes"]["MortalityDistributionFemale"] = distribution.to_dict()
        else:
            for node_id in node_ids:
                self.get_node_by_id(node_id=node_id)._set_mortality_female_complex_distribution(distribution)

        if self.implicits is not None:
            self.implicits.append(DT._set_mortality_age_gender)

    def SetMortalityDistributionMale(self, distribution: MortalityDistribution = None,
                                     node_ids: List[int] = None):
        """
        Set a default male mortality distribution for all nodes or per node. Turn on Enable_Natural_Mortality
            implicitly.

        Args:
            distribution: distribution
            node_ids: a list of node_ids

        Returns:

        """
        warnings.warn('SetMortalityDistributionMale() is deprecated. Please use the emodpy Demographics method: '
                      'set_mortality_distribution()', DeprecationWarning, stacklevel=2)

        if node_ids is None:
            self.raw["Defaults"]["IndividualAttributes"]["MortalityDistributionMale"] = distribution.to_dict()
        else:
            for node_id in node_ids:
                self.get_node_by_id(node_id=node_id)._set_mortality_male_complex_distribution(distribution)

        if self.implicits is not None:
            self.implicits.append(DT._set_mortality_age_gender)

    def SetMortalityOverTimeFromData(self,
                                     data_csv: Union[str, os.PathLike],
                                     base_year: int,
                                     node_ids: List = None):
        """
        Set default mortality rates for all nodes or per node. Turn on mortality configs implicitly. You can use
        the x_Other_Mortality configuration parameter to tune/calibrate.

        Args:
            data_csv: Path to csv file with the mortality rates by calendar year and age bucket.
            base_year: The calendar year the sim is treating as the base.
            node_ids: Optional list of node ids to apply this to. Defaults to all.

        Returns:

        """
        warnings.warn('SetMortalityOverTimeFromData() is deprecated. Please use the emodpy Demographics method: '
                      'set_mortality_distribution()', DeprecationWarning, stacklevel=2)

        if node_ids is None:
            node_ids = []
        if base_year < 0:
            raise ValueError(f"User passed negative value of base_year: {base_year}.")
        if base_year > 2050:
            raise ValueError(f"User passed too large value of base_year: {base_year}.")

        # Load csv. Convert rate arrays into DTK-compatiable JSON structures.
        rates = []  # array of arrays, but leave that for a minute
        df = pd.read_csv(data_csv)
        header = df.columns
        year_start = int(header[1]) # someone's going to come along with 1990.5, etc. Sigh.
        year_end = int(header[-1])
        if year_end <= year_start:
            raise ValueError(f"Failed check that {year_end} is greater than {year_start} in csv dataset.")
        num_years = year_end - year_start + 1
        rel_years = list()
        for year in range(year_start, year_start + num_years):
            mort_data = list(df[str(year)])
            rel_years.append(year - base_year)

        age_key = None
        for trykey in df.keys():
            if trykey.lower().startswith("age"):
                age_key = trykey
                raw_age_bins = list(df[age_key])

        if age_key is None:
            raise ValueError("Failed to find 'Age_Bin' (or similar) column in the csv dataset. Cannot process.")

        num_age_bins = len(raw_age_bins)
        age_bins = list()
        try:
            for age_bin in raw_age_bins:
                left_age = float(age_bin.split("-")[0])
                age_bins.append(left_age)

        except Exception as ex:
            raise ValueError(f"Ran into error processing the values in the Age-Bin column. {ex}")

        for idx in range(len(age_bins)):  # 18 of these
            # mort_data is the array of mortality rates (by year bin) for age_bin
            mort_data = list(df.transpose()[idx][1:])
            rates.append(mort_data)  # 28 of these, 1 for each year, eg

        num_pop_groups = [num_age_bins, num_years]
        pop_groups = [age_bins, rel_years]

        distrib = MortalityDistribution(result_values=rates,
                                        axis_names=["age", "year"],
                                        axis_scale_factors=[365, 1],
                                        axis_units="N/A",
                                        num_distribution_axes=len(num_pop_groups),
                                        num_population_groups=num_pop_groups,
                                        population_groups=pop_groups,
                                        result_scale_factor=2.74e-06,
                                        result_units="annual deaths per 1000 individuals")

        if not node_ids:
            self.raw["Defaults"]["IndividualAttributes"]["MortalityDistributionMale"] = distrib.to_dict()
            self.raw["Defaults"]["IndividualAttributes"]["MortalityDistributionFemale"] = distrib.to_dict()
        else:
            if len(self.nodes) == 1 and len(node_ids) > 1:
                raise ValueError("User specified several node ids for single node demographics setup.")
            for node_id in node_ids:
                self.get_node_by_id(node_id=node_id)._set_mortality_male_complex_distribution(distrib)
                self.get_node_by_id(node_id=node_id)._set_mortality_female_complex_distribution(distrib)

        if self.implicits is not None:
            self.implicits.append(DT._set_mortality_age_gender_year)

    def SetAgeDistribution(self, distribution: AgeDistribution, node_ids: List[int] = None):
        """
        Set a default age distribution for all nodes or per node. Sets distribution type to COMPLEX implicitly.
        Args:
            distribution: age distribution
            node_ids: a list of node_ids

        Returns:

        """
        warnings.warn("SetAgeDistibution is deprecated. Please use emodpy Demographics.set_age_distribution instead.",
                      DeprecationWarning, stacklevel=2)
        if node_ids is None:
            self.raw["Defaults"]["IndividualAttributes"]["AgeDistribution"] = distribution.to_dict()
        else:
            for node_id in node_ids:
                self.get_node_by_id(node_id=node_id)._set_age_complex_distribution(distribution)

        if self.implicits is not None:
            self.implicits.append(DT._set_age_complex)

    def SetDefaultNodeAttributes(self, birth=True):
        """
        Set the default NodeAttributes (Altitude, Airport, Region, Seaport), optionally including birth,
        which is most important actually.
        """
        warnings.warn('SetDefaultNodeAttributes() is deprecated. Default nodes should now be represented by Node '
                      'objects and passed to the Demographics object during the constructor call. They can be modified '
                      'afterward, if needed.',
                      DeprecationWarning, stacklevel=2)
        self.raw['Defaults']['NodeAttributes'] = {"Altitude": 0,
                                                  "Airport": 1,  # why are these still needed?
                                                  "Region": 1,
                                                  "Seaport": 1}
        if birth:
            self.SetBirthRate(YearlyRate(math.log(1.03567)))

    def SetDefaultProperties(self):
        """
        Set a bunch of defaults (age structure, initial susceptibility and initial prevalencec) to sensible values.
        """
        warnings.warn('SetDefaultProperties() is deprecated. Default nodes should now be represented by Node objects '
                      'and passed to the Demographics object during the constructor call. They can be modified '
                      'afterward, if needed.',
                      DeprecationWarning, stacklevel=2)
        self.SetDefaultNodeAttributes()
        self.SetDefaultIndividualAttributes()  # Distributions for initialization of immunity, risk heterogeneity, etc.
        self.raw['Defaults']['IndividualProperties'] = []

    def SetDefaultFromTemplate(self, template, setter_fn=None):
        """
        Add to the default IndividualAttributes using the input template (raw json) and set corresponding
        config values per the setter_fn. The template should always be constructed by a
        function in DemographicsTemplates. Eventually this function will be hidden and only
        accessed via separate application-specific API functions such as the ones below.
        """
        warnings.warn('SetDefaultFromTemplate() is deprecated. Please use the emodpy Demographics methods: '
                      'set_XYZ_distribution() as needed and other object-based setting functions',
                      DeprecationWarning, stacklevel=2)

        self.raw['Defaults']['IndividualAttributes'].update(template)
        if self.implicits is not None and setter_fn is not None:
            self.implicits.append(setter_fn)

    # TODO: is this useful in a way that warrants a special-case function in emodpy built around set_age_distribution?
    #  https://github.com/InstituteforDiseaseModeling/emod-api-old/issues/788
    def SetEquilibriumAgeDistFromBirthAndMortRates(self, CrudeBirthRate=CrudeRate(40), CrudeMortRate=CrudeRate(20),
                                                   node_ids=None):
        """
        Set the inital ages of the population to a sensible equilibrium profile based on the specified input birth and
        death rates. Note this does not set the fertility and mortality rates.
        """
        warnings.warn('SetEquilibriumAgeDistFromBirthAndMortRates() is deprecated. Please use the emodpy Demographics method: '
                      'set_age_distribution()', DeprecationWarning, stacklevel=2)

        yearly_birth_rate = YearlyRate(CrudeBirthRate)
        yearly_mortality_rate = YearlyRate(CrudeMortRate)
        dist = DT._EquilibriumAgeDistFromBirthAndMortRates(yearly_birth_rate, yearly_mortality_rate)
        setter_fn = DT._set_age_complex
        if node_ids is None:
            self.SetDefaultFromTemplate(dist, setter_fn)
        else:
            new_dist = AgeDistribution()
            dist = new_dist.from_dict(dist["AgeDistribution"])
            for node in node_ids:
                self.get_node_by_id(node_id=node)._set_age_complex_distribution(dist)
            self.implicits.append(setter_fn)

    def SetInitialAgeExponential(self, rate=0.0001068, description=""):
        """
        Set the initial age of the population to an exponential distribution with a specified rate.
        :param  rate: rate
        :param  description: description, why was this distribution chosen
        """
        warnings.warn('SetInitialAgeExponential() is deprecated. Please use the emodpy Demographics method: '
                      'set_age_distribution()', DeprecationWarning, stacklevel=2)

        if not description:
            description = "Initial ages set to draw from exponential distribution with {rate}"

        setting = {"AgeDistributionFlag": 3,
                   "AgeDistribution1": rate,
                   "AgeDistribution2": 0,
                   "AgeDistribution_Description": description}
        self.SetDefaultFromTemplate(setting, DT._set_age_simple)

    def SetInitialAgeLikeSubSaharanAfrica(self, description=""):
        """
        Set the initial age of the population to a overly simplified structure that sort of looks like
        sub-Saharan Africa. This uses the SetInitialAgeExponential.
        :param  description: description, why was this age chosen?
        """
        warnings.warn('SetInitialAgeLikeSubSaharanAfrica() is deprecated. Please use the emodpy Demographics method: '
                      'set_age_distribution()', DeprecationWarning, stacklevel=2)

        if not description:
            description = "Setting initial age distribution like Sub Saharan Africa, drawing from exponential distribution."

        self.SetInitialAgeExponential(description=description)  # use default rate

    def SetInitPrevFromUniformDraw(self, min_init_prev, max_init_prev, description=""):
        """
        Set Initial Prevalence (one value per node) drawn from an uniform distribution.
        :param  min_init_prev: minimal initial prevalence
        :param  max_init_prev: maximal initial prevalence
        :param  description: description, why were these parameters chosen?
        """
        if not description:
            description = f"Drawing prevalence from uniform distribution, min={min_init_prev} and max={max_init_prev}"

        warnings.warn('SetInitPrevFromUniformDraw() is deprecated. Please use the emodpy Demographics method: '
                      'set_prevalence_distribution()', DeprecationWarning, stacklevel=2)

        DT.InitPrevUniform(self, min_init_prev, max_init_prev, description)

    def AddMortalityByAgeSexAndYear(self, age_bin_boundaries_in_years: List[float],
                                    year_bin_boundaries: List[float],
                                    male_mortality_rates: List[List[float]],
                                    female_mortality_rates: List[List[float]]):
        warnings.warn('AddMortalityByAgeSexAndYear() is deprecated. Please use the emodpy Demographics method: '
                      'set_mortality_distribution()', DeprecationWarning, stacklevel=2)

        assert len(age_bin_boundaries_in_years) == len(male_mortality_rates), "One array with distributions per age " \
                                                                              "bin is required. \n number of age bins "\
                                                                              "= {len(age_bin_boundaries_in_years)} " \
                                                                              "number of male mortality rates = {len(" \
                                                                              "male_mortality_rates)} "
        assert len(age_bin_boundaries_in_years) == len(female_mortality_rates), "One array with distributions per age "\
                                                                                "bin is required. \n number of age " \
                                                                                "bins = {len(" \
                                                                                "age_bin_boundaries_in_years)} number "\
                                                                                "of female mortality rates = {len(" \
                                                                                "male_mortality_rates)} "
        for yearly_mort_rate in male_mortality_rates:
            assert len(year_bin_boundaries) == len(yearly_mort_rate), "The number of year bins must be equal the " \
                                                                      "number of male mortality rates per year.\n" \
                                                                      "number of year bins = {len(" \
                                                                      "year_bin_boundaries)} number of male mortality "\
                                                                      "rates = {len(yearly_mort_rate)} "
        for yearly_mort_rate in female_mortality_rates:
            assert len(year_bin_boundaries) == len(yearly_mort_rate), "The number of year bins must be equal the " \
                                                                      "number of female mortality rates per year.\n " \
                                                                      "number of year bins = {len(" \
                                                                      "year_bin_boundaries)} number of male " \
                                                                      "mortality rates = {len(yearly_mort_rate)} "

        axis_names = ["age", "year"]
        axis_scale_factors = [365, 1]
        num_population_groups = [len(age_bin_boundaries_in_years), len(year_bin_boundaries)]
        population_groups = [age_bin_boundaries_in_years, year_bin_boundaries]

        mort_distr_male = MortalityDistribution(axis_names=axis_names,
                                                axis_scale_factors=axis_scale_factors,
                                                num_population_groups=num_population_groups,
                                                population_groups=population_groups,
                                                result_scale_factor=1.0,
                                                result_values=male_mortality_rates)
        self.SetMortalityDistributionMale(mort_distr_male)

        mort_distr_female = MortalityDistribution(axis_names=axis_names,
                                                  axis_scale_factors=axis_scale_factors,
                                                  num_population_groups=num_population_groups,
                                                  population_groups=population_groups,
                                                  result_scale_factor=1.0,
                                                  result_values=female_mortality_rates)
        self.SetMortalityDistributionFemale(mort_distr_female)

        if self.implicits is not None:
            self.implicits.append(DT._set_mortality_age_gender_year)

    def SetFertilityOverTimeFromParams(self,
                                       years_region1: int,
                                       years_region2: int,
                                       start_rate: float,
                                       inflection_rate: float,
                                       end_rate: float,
                                       node_ids: List = None) -> List[float]:
        """
        Set fertility rates that vary over time based on a model with two linear regions. Note that fertility rates
        use GFR units: babies born per 1000 women of child-bearing age annually. You can use the x_Birth configuration
        parameter to tune/calibrate.

        Refer to the following diagram.

        .. figure:: images/fertility_over_time_doc.png

        Args:
            years_region1: The number of years covered by the first linear region. So if this represents
                1850 to 1960, years_region1 would be 110.
            years_region2: The number of years covered by the second linear region. So if this represents
                1960 to 2020, years_region2 would be 60.
            start_rate: The fertility rate at t=0.
            inflection_rate: The fertility rate in the year where the two linear regions meet.
            end_rate: The fertility rate at the end of the period covered by region1 + region2.
            node_ids: Optional list of node ids to apply this to. Defaults to all.

        Returns:
            rates array (Just in case user wants to do something with them like inspect or plot.)
        """
        warnings.warn('SetFertilityOverTimeFromParams() is deprecated. Please use the emodpy-hiv Demographics method: '
                      'set_fertility_distribution()', DeprecationWarning, stacklevel=2)
        if node_ids is None:
            node_ids = []
        rates = []
        if years_region1 < 0:
            raise ValueError("years_region1 can't be negative.")
        if years_region2 < 0:
            raise ValueError("years_region2 can't be negative.")
        if start_rate < 0:
            raise ValueError("start_rate can't be negative.")
        if inflection_rate < 0:
            raise ValueError("inflection_rate can't be negative.")
        if end_rate < 0:
            raise ValueError("end_rate can't be negative.")
        for i in range(years_region1):
            rate = start_rate + (inflection_rate - start_rate) * (i / years_region1)
            rates.append(rate)
        for i in range(years_region2):
            rate = inflection_rate + (end_rate - inflection_rate) * (i / years_region2)
            rates.append(rate)
        # OK, now we put this into the nasty complex fertility structure
        dist = DT.get_fert_dist_from_rates(rates)
        if not node_ids:
            dist_dict = dist.to_dict()
            if "FertilityDistribution" not in dist_dict:
                full_dict = {"FertilityDistribution": dist.to_dict()}
            else:
                full_dict = dist_dict
            self.SetDefaultFromTemplate(full_dict, DT._set_fertility_age_year)
        else:
            if len(self.nodes) == 1 and len(node_ids) > 1:
                raise ValueError("User specified several node ids for single node demographics setup.")
            for node_id in node_ids:
                self.get_node_by_id(node_id=node_id)._set_fertility_complex_distribution(dist)
            if self.implicits is not None:
                self.implicits.append(DT._set_fertility_age_year)
        return rates

    def infer_natural_mortality(self,
                                file_male,
                                file_female,
                                interval_fit: List[Union[int, float]] = None,
                                which_point='mid',
                                predict_horizon=2050,
                                csv_out=False,
                                n=0,  # I don't know what this means
                                results_scale_factor=1.0 / 365.0) -> [Dict, Dict]:
        """
        Calculate and set the expected natural mortality by age, sex, and year from data, predicting what it would
        have been without disease (HIV-only).
        """
        from collections import OrderedDict
        from sklearn.linear_model import LinearRegression
        from functools import reduce

        warnings.warn('infer_natural_mortality() is deprecated. Please use modern country model loading.',
                      DeprecationWarning, stacklevel=2)

        if interval_fit is None:
            interval_fit = [1970, 1980]

        name_conversion_dict = {'Age (x)': 'Age',
                                'Central death rate m(x,n)': 'Mortality_mid',
                                'Age interval (n)': 'Interval',
                                'Period': 'Years'
                                }
        sex_dict = {'Male': 0, 'Female': 1}

        def construct_interval(x, y):
            return x, x + y

        def midpoint(x, y):
            return (x + y) / 2.0

        def generate_dict_order(tuple_list, which_entry=1):
            my_unordered_list = tuple_list.apply(lambda x: x[which_entry])
            dict_to_order = OrderedDict(zip(tuple_list, my_unordered_list))
            return dict_to_order

        def map_year(x_tuple, flag='mid'):
            valid_entries_loc = ['mid', 'end', 'start']

            if flag not in valid_entries_loc:
                raise ValueError('invalid endpoint specified')

            if flag == 'mid':
                return (x_tuple[0] + x_tuple[1]) / 2.0
            elif flag == 'start':
                return x_tuple[0]
            else:
                return x_tuple[1]

        df_mort_male = pd.read_csv(file_male, usecols=name_conversion_dict)
        df_mort_male['Sex'] = 'Male'
        df_mort_female = pd.read_csv(file_female, usecols=name_conversion_dict)
        df_mort_female['Sex'] = 'Female'
        df_mort = pd.concat([df_mort_male, df_mort_female], axis=0)
        df_mort.rename(columns=name_conversion_dict, inplace=True)
        df_mort['Years'] = df_mort['Years'].apply(lambda x: tuple(
            [float(zz) for zz in x.split('-')]))  # this might be a bit too format specific (ie dashes in input)

        # log transform the data and drop unneeded columns
        df_mort['log_Mortality_mid'] = df_mort['Mortality_mid'].apply(lambda x: np.log(x))
        df_mort['Age'] = df_mort[['Age', 'Interval']].apply(lambda zz: construct_interval(*zz), axis=1)

        year_order_dict = generate_dict_order(df_mort['Years'])
        age_order_dict = generate_dict_order(df_mort['Age'])
        df_mort['sortby2'] = df_mort['Age'].map(age_order_dict)
        df_mort['sortby1'] = df_mort['Sex'].map(sex_dict)
        df_mort['sortby3'] = df_mort['Years'].map(year_order_dict)
        df_mort.sort_values(['sortby1', 'sortby2', 'sortby3'], inplace=True)
        df_mort.drop(columns=['Mortality_mid', 'Interval', 'sortby1', 'sortby2', 'sortby3'], inplace=True)

        # convert to years (and to string for age_list due to really annoying practical slicing reasons
        df_mort['Years'] = df_mort['Years'].apply(lambda x: map_year(x, which_point))
        df_mort['Age'] = df_mort['Age'].apply(lambda x: str(x))
        df_before_time = df_mort[df_mort['Years'].between(0, interval_fit[0])].copy()

        df_mort.set_index(['Sex', 'Age'], inplace=True)
        sex_list = list(set(df_mort.index.get_level_values('Sex')))
        age_list = list(set(df_mort.index.get_level_values('Age')))

        df_list = []
        for sex in sex_list:
            for age in age_list:
                tmp_data = df_mort.loc[(sex, age, slice(None)), :]
                extrap_model = make_pipeline(StandardScaler(with_mean=False), LinearRegression())

                first_extrap_df = tmp_data[tmp_data['Years'].between(interval_fit[0], interval_fit[1])]
                xx = tmp_data[tmp_data['Years'].between(interval_fit[0], predict_horizon)].values[:, 0]

                values = first_extrap_df.values
                extrap_model.fit(values[:, 0].reshape(-1, 1), values[:, 1])

                extrap_predictions = extrap_model.predict(xx.reshape(-1, 1))

                loc_df = pd.DataFrame.from_dict({'Sex': sex, 'Age': age, 'Years': xx, 'Extrap': extrap_predictions})
                loc_df.set_index(['Sex', 'Age', 'Years'], inplace=True)

                df_list.append(loc_df.copy())

        df_e1 = pd.concat(df_list, axis=0)

        df_list_final = [df_mort, df_e1]
        df_total = reduce(lambda left, right: pd.merge(left, right, on=['Sex', 'Age', 'Years']), df_list_final)

        df_total = df_total.reset_index(inplace=False).set_index(['Sex', 'Age'], inplace=False)

        df_total['Extrap'] = df_total['Extrap'].apply(np.exp)
        df_total['Data'] = df_total['log_Mortality_mid'].apply(np.exp)
        df_before_time['Data'] = df_before_time['log_Mortality_mid'].apply(np.exp)

        df_before_time.set_index(['Sex', 'Age'], inplace=True)
        df_total = pd.concat([df_total, df_before_time], axis=0, join='outer', sort=True)

        df_total.reset_index(inplace=True)
        df_total['sortby2'] = df_total['Age'].map(age_order_dict)
        df_total['sortby1'] = df_total['Sex'].map(sex_dict)
        df_total.sort_values(by=['sortby1', 'sortby2', 'Years'], inplace=True)
        df_total.drop(columns=['sortby1', 'sortby2'], inplace=True)

        estimates_list = []
        estimates_list.append(df_total.copy())
        # estimates_list = [df_total.copy()] alternative

        def min_not_nan(x_list):
            loc_in = list(filter(lambda x: not np.isnan(x), x_list))
            return np.min(loc_in)

        # This was in another function before
        df = estimates_list[n]
        df['FE'] = df[['Data', 'Extrap']].apply(min_not_nan, axis=1)
        df['Age'] = df['Age'].apply(lambda x: int(x.split(',')[1].split(')')[0]))
        male_df = df[df['Sex'] == 'Male']
        female_df = df[df['Sex'] == 'Female']

        male_df.set_index(['Sex', 'Age', 'Years'], inplace=True)
        female_df.set_index(['Sex', 'Age', 'Years'], inplace=True)
        male_data = male_df['FE']
        female_data = female_df['FE']

        male_data = male_data.unstack(-1)
        male_data.sort_index(level='Age', inplace=True)
        female_data = female_data.unstack(-1)
        female_data.sort_index(level='Age', inplace=True)

        years_out_male = list(male_data.columns)
        years_out_female = list(female_data.columns)

        age_out_male = list(male_data.index.get_level_values('Age'))
        age_out_female = list(male_data.index.get_level_values('Age'))

        male_output = male_data.values
        female_output = female_data.values

        if csv_out:
            male_data.to_csv(f'Male{csv_out}')
            female_data.to_csv(f'Female{csv_out}')

        # TBD: This is the part that should use base file functionality

        dict_female = {'AxisNames': ['age', 'year'],
                       'AxisScaleFactors': [365.0, 1],
                       'AxisUnits': ['years', 'years'],
                       'PopulationGroups': [age_out_female, years_out_female],
                       'ResultScaleFactor': results_scale_factor,
                       'ResultUnits': 'annual deaths per capita',
                       'ResultValues': female_output.tolist()
                       }

        dict_male = {'AxisNames': ['age', 'year'],
                     'AxisScaleFactors': [365.0, 1],
                     'AxisUnits': ['years', 'years'],
                     'PopulationGroups': [age_out_male, years_out_male],
                     'ResultScaleFactor': results_scale_factor,
                     'ResultUnits': 'annual deaths per capita',
                     'ResultValues': male_output.tolist()
                     }
        self.implicits.append(DT._set_mortality_age_gender_year)
        return dict_female, dict_male
