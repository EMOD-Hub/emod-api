import json
import math
import numpy as np
import os
import pandas as pd
import pathlib
import tempfile
import sys

from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from emod_api.demographics import DemographicsTemplates as DT
from emod_api.demographics.BaseInputFile import BaseInputFile
from emod_api.demographics.DemographicsInputDataParsers import node_ID_from_lat_long, duplicate_nodeID_check
from emod_api.demographics.DemographicsTemplates import CrudeRate, YearlyRate, DemographicsTemplatesConstants
from emod_api.demographics.Node import Node
from emod_api.demographics.PropertiesAndAttributes import IndividualAttributes, IndividualProperty, NodeAttributes
from emod_api.demographics.service import service

from typing import List, Dict, Union
from functools import partial
from emod_api.migration import migration

# TODO: replace all self.raw usage to use Node objects?
#  https://github.com/InstituteforDiseaseModeling/emod-api/issues/687


# TODO: All following "from_X()" methods should be class methods of Demographics
#  https://github.com/InstituteforDiseaseModeling/emod-api/issues/688
def from_template_node(lat=0, lon=0, pop=1000000, name="Erewhon", forced_id=1):
    """
    Create a single-node :py:class:`Demographics` instance from a few parameters.    
    """
    new_nodes = [Node(lat, lon, pop, forced_id=forced_id, name=name)]
    return Demographics(nodes=new_nodes)


def from_file(base_file):
    """
    Create a :py:class:`Demographics` instance from an existing demographics file.
    """
    with open(base_file, "rb") as src:
        raw = json.load(src)
        nodes = []

        # Load the nodes
        for node in raw["Nodes"]:
            nodes.append(Node.from_data(node))

        # Load the idref
        idref = raw["Metadata"]["IdReference"]

    # Create the file
    return Demographics(nodes, idref, base_file)


def get_node_ids_from_file(demographics_file):
    """
    Get a list of node ids from a demographics file.
    """
    d = from_file(demographics_file)
    return sorted(d.node_ids)


def get_node_pops_from_params(tot_pop, num_nodes, frac_rural):
    """
    Get a list of node populations from the params used to create a sparsely 
    parameterized multi-node :py:class:`Demographics` instance. The first population 
    in the list is the "urban" population and remaning populations are roughly drawn from a
    log-uniform distribution.

    Args:
        tot_pop (int): Sum of all node populations (not guaranteed)
        num_nodes (int): The total number of nodes.
        frac_rural (float): The fraction of the total population that is to be distributed across the
            `num_nodes`-1 "rural" nodes.

    Returns:
        A list containing the urban node population followed by the rural nodes.
    """

    # Draw from a log-uniform or reciprocal distribution (support from (1, \infty))
    nsizes = np.exp(-np.log(np.random.rand(num_nodes - 1)))
    # normalize to frac_rural
    nsizes = frac_rural * nsizes / np.sum(nsizes)
    # require atleast 100 people
    nsizes = np.minimum(nsizes, 100 / tot_pop)
    # normalize to frac_rural
    nsizes = frac_rural * nsizes / np.sum(nsizes)
    # add the urban node
    nsizes = np.insert(nsizes, 0, 1 - frac_rural)
    # round the populations to the nearest integer and change type to list
    npops = ((np.round(tot_pop * nsizes, 0)).astype(int)).tolist()
    return npops


def from_params(tot_pop=1000000, num_nodes=100, frac_rural=0.3, id_ref="from_params", random_2d_grid=False):
    """
    Create an EMOD-compatible :py:class:`Demographics` object with the population and numbe of nodes specified.
 
    Args:
        tot_pop: The total population.
        num_nodes: Number of nodes. Can be defined as a two-dimensional grid  of nodes [longitude, latitude].
            The distance to the next neighbouring node is 1.
        frac_rural: Determines what fraction of the population gets put in the 'rural' nodes, which means all nodes
            besides node 1. Node 1 is the 'urban' node.
        id_ref:  Facility name
        random_2d_grid: Create a random distanced grid with num_nodes nodes.

    Returns:
        A :py:class:`Demographics` object
    """
    if frac_rural > 1.0:
        raise ValueError(f"frac_rural can't be greater than 1.0")
    if frac_rural < 0.0:
        raise ValueError(f"frac_rural can't be less than 0")
    if frac_rural == 0.0:
        frac_rural = 1e-09

    if random_2d_grid:
        total_nodes = num_nodes
        ucellb = np.array([[1.0, 0.0], [-0.5, 0.86603]])
        nlocs = np.random.rand(num_nodes, 2)
        nlocs[0, :] = 0.5
        nlocs = np.round(np.matmul(nlocs, ucellb), 4)
    else:
        if isinstance(num_nodes, int):
            lon_grid = num_nodes
            lat_grid = 1
        else:
            lon_grid = num_nodes[0]  # east/west
            lat_grid = num_nodes[1]  # north/south

        total_nodes = lon_grid * lat_grid
        nlocs = [[i, j] for i in range(lon_grid) for j in range(lat_grid)]

    nodes = []
    npops = get_node_pops_from_params(tot_pop, total_nodes, frac_rural)

    # Add nodes to demographics
    for idx, lat_lon in enumerate(nlocs):
        nodes.append(Node(lat=lat_lon[0], lon=lat_lon[1], pop=npops[idx], forced_id=idx + 1))

    return Demographics(nodes=nodes, idref=id_ref)


def from_csv(input_file, res=30/3600, id_ref="from_csv"):
    """
    Create an EMOD-compatible :py:class:`Demographics` instance from a csv population-by-node file.

    Args:
        input_file (str): Filename
        res (float, optional): Resolution of the nodes in arc-seconds
        id_ref (str, optional): Description of the source of the file.
    """
    def get_value(row, headers):
        for h in headers:
            if row.get(h) is not None:
                return float(row.get(h))
        return None

    if not os.path.exists(input_file):
        print(f"{input_file} not found.")
        return

    print(f"{input_file} found and being read for demographics.json file creation.")
    node_info = pd.read_csv(input_file, encoding='iso-8859-1')
    out_nodes = []
    for index, row in node_info.iterrows():
        if 'under5_pop' in row:
            pop = int(6*row['under5_pop'])
            if pop < 25000:
                continue
        else:
            pop = int(row['pop'])

        latitude_headers = ["lat", "latitude", "LAT", "LATITUDE", "Latitude", "Lat"]
        lat = get_value(row, latitude_headers)

        longitude_headers = ["lon", "longitude", "LON", "LONGITUDE", "Longitude", "Lon"]
        lon = get_value(row, longitude_headers)

        birth_rate_headers = ["birth", "Birth", "birth_rate", "birthrate", "BirthRate", "Birth_Rate", "BIRTH",
                              "birth rate", "Birth Rate"]
        birth_rate = get_value(row, birth_rate_headers)
        if birth_rate is not None and birth_rate < 0.0:
            raise ValueError("Birth rate defined in " + input_file + " must be greater 0.")

        node_id = row.get('node_id')
        if node_id is not None and int(node_id) == 0:
            raise ValueError("Node ids can not be '0'.")

        forced_id = int(node_id) if (node_id is not None) else int(node_ID_from_lat_long(lat, lon, res))

        place_name = ""
        if 'loc' in row:
            place_name = str(row['loc'])
        meta = {} 
        """
        meta = {'dot_name': (row['ADM0_NAME']+':'+row['ADM1_NAME']+':'+row['ADM2_NAME']),
                'GUID': row['GUID'],
                'density': row['under5_pop_weighted_density']}
        """
        node_attributes = NodeAttributes(name=place_name, birth_rate=birth_rate)
        node = Node(lat, lon, pop,
                    node_attributes=node_attributes,
                    forced_id=forced_id, meta=meta)

        out_nodes.append(node)
    out_nodes = duplicate_nodeID_check(out_nodes)
    for node in out_nodes:
        # Not sure why this node causes issues, just dump it for speed.  Probably an issue in the duplicate nodeID check
        if node.id == 1639001798:
            remel = node
            out_nodes.remove(remel)

    return Demographics(nodes=out_nodes, idref=id_ref)


# This will be the long-term API for this function.
def from_pop_raster_csv(
    pop_filename_in,
    res=1/120,
    id_ref="from_raster",
    pop_filename_out="spatial_gridded_pop_dir",
    site="No_Site"
):
    """
        Take a csv of a population-counts raster and build a grid for use with EMOD simulations.
        Grid size is specified by grid resolution in arcs or in kilometers. The population counts 
        from the raster csv are then assigned to their nearest grid center and a new intermediate
        grid file is generated with latitude, longitude and population. This file is then fed to
        from_csv to generate a demographics object.
    
    Args:
        pop_filename_in (str): The filename of the population-counts raster in CSV format.
        res (float, optional): The grid resolution in arcs or kilometers. Default is 1/120.
        id_ref (str, optional): Identifier reference for the grid. Default is "from_raster".
        pop_filename_out (str, optional): The output filename for the intermediate grid file.
            Default is "spatial_gridded_pop_dir".
        site (str, optional): The site name or identifier. Default is "No_Site".
    
    Returns:
        :py:class`Demographics` object: The generated demographics object based on the grid file.
    
    Raises:
        N/A
    
    """
    grid_file_path = service._create_grid_files(pop_filename_in, pop_filename_out, site)
    print(f"{grid_file_path} grid file created.")
    return from_csv(grid_file_path, res, id_ref)


def from_pop_csv(
    pop_filename_in,
    res=1/120,
    id_ref="from_raster",
    pop_filename_out="spatial_gridded_pop_dir",
    site="No_Site"
):
    """
        Deprecated. Please use from_pop_raster_csv.
    """
    return from_pop_raster_csv(pop_filename_in, res, id_ref, pop_filename_out, site)


# TODO: Move this class to a new file and update imports
#  https://github.com/InstituteforDiseaseModeling/emod-api/issues/689
class DemographicsBase(BaseInputFile):
    """
    Base class for :py:obj:`emod_api:emod_api.demographics.Demographics` and
        :py:obj:`emod_api:emod_api.demographics.DemographicsOverlay`.
    """

    class UnknownNodeException(ValueError):
        pass

    def __init__(self, nodes: List[Node], idref: str, default_node: Node = None):
        super().__init__(idref=idref)
        # TODO: node ids should be required to be UNIQUE to prevent later failures when running EMOD. Any update to
        #  self.nodes should trigger a check/error if needed.
        self.nodes = nodes
        self.idref = idref  # TODO: remove this line, self.idref is already an attribute of BaseInputFile
        self.implicits = list()
        self.migration_files = list()

        # Build the default node if not provided
        metadata = self.generate_headers()
        if default_node is None:  # use raw attribute, current malaria/other disease style
            # currently all non-HIV disease route
            self.raw = {"Defaults": dict(), "Metadata": metadata}
            self.raw["Defaults"]["NodeAttributes"] = dict()
            self.raw["Defaults"]["IndividualAttributes"] = dict()
            self.raw["Defaults"]["IndividualProperties"] = list()
        else:  # HIV style
            self.default_node = default_node

    def _select_node_dicts(self, node_ids=None):
        if node_ids is None:
            node_dicts = [self.raw['Defaults']]
        else:
            node_dicts = [node_dict for node_dict in self.raw["Nodes"] if node_dict["NodeID"] in node_ids]
        return node_dicts

    # TODO: deprecating _nodes, it is no longer used. Remove it.
    #  https://github.com/InstituteforDiseaseModeling/emod-api/issues/691
    @property
    def _nodes(self):
        from warnings import warn
        message = f"_nodes is a deprecated attribute of Node objects, use nodes instead (e.g. demographics.nodes)"
        warn(message=message, category=DeprecationWarning, stacklevel=2)
        return self.nodes

    # TODO: example of node-node update() call, make sure this still works after changing Updateable.update()
    # Or do we really need this?? (only used in tests or maybe emodpy-malaria; don't know for the latter)
    def apply_overlay(self, overlay_nodes: list):
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

    def send(self, write_to_this, return_from_forked_sender=False):
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
            N/A
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
        from warnings import warn
        message = f"node_count is a deprecated property of Node objects, use len(demog.nodes) instead."
        warn(message=message, category=DeprecationWarning, stacklevel=2)
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
        from warnings import warn
        message = f"get_node() is a deprecated function of Node objects, use get_node_by_id() instead. " \
                  f"(e.g. demographics.get_node_by_id(node_id=4))"
        warn(message=message, category=DeprecationWarning, stacklevel=2)
        return self.get_node_by_id(node_id=nodeid)

    @property
    def _all_nodes(self) -> List[Node]:
        # only HIV is using a default node object right now
        default_node = [self.default_node] if hasattr(self, 'default_node') else []
        return self.nodes + default_node

    @property
    def _all_node_ids(self) -> List[int]:
        return [node.id for node in self._all_nodes]

    @property
    def _all_nodes_by_id(self) -> Dict[int, Node]:
        return {node.id: node for node in self._all_nodes}

    def get_node_by_id(self, node_id: int) -> Node:
        """
        Returns the Node objects requested by their node id.

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

    def SetMigrationPattern(self, pattern: str = "rwd"):
        """
        Set migration pattern. Migration is enabled implicitly.
        It's unusual for the user to need to set this directly; normally used by emodpy.

        Args:
            pattern: Possible values are "rwd" for Random Walk Diffusion and "srt" for Single Round Trips.
        """
        if self.implicits is not None:
            if pattern.lower() == "srt":
                self.implicits.append(DT._set_migration_pattern_srt)
            elif pattern.lower() == "rwd":
                self.implicits.append(DT._set_migration_pattern_rwd)
            else:
                raise ValueError('Unknown migration pattern: %s. Possible values are "rwd" and "srt".', pattern)

    def _SetRegionalMigrationFileName(self, file_name):
        """
        Set path to migration file.

        Args:
            file_name: Path to migration file.
        """
        if self.implicits is not None:
            self.implicits.append(partial(DT._set_regional_migration_filenames, file_name=file_name))

    def _SetLocalMigrationFileName(self, file_name):
        """
        Set path to migration file.

        Args:
            file_name: Path to migration file.
        """
        if self.implicits is not None:
            self.implicits.append(partial(DT._set_local_migration_filename, file_name=file_name))

    def _SetDemographicFileNames(self, file_names):
        """
        Set paths to demographic file.

        Args:
            file_names: Paths to demographic files.
        """
        if self.implicits is not None:
            self.implicits.append(partial(DT._set_demographic_filenames, file_names=file_names))

    def SetRoundTripMigration(self, gravity_factor, probability_of_return=1.0, id_ref='short term commuting migration'):
        """
        Set commuter/seasonal/temporary/round-trip migration rates. You can use the x_Local_Migration configuration
            parameter to tune/calibrate.

        Args:
            gravity_factor: 'Big G' in gravity equation. Combines with 1, 1, and -2 as the other exponents.
            probability_of_return: Likelihood that an individual who 'commuter migrates' will return to the node 
                                   of origin during the next migration (not timestep). Defaults to 1.0. Aka, travel,
                                   shed, return."
            id_ref: Text string that appears in the migration file itself; needs to match corresponding demographics
                file.
        """
        if gravity_factor < 0:
            raise ValueError(f"gravity factor can't be negative.")

        gravity_params = [gravity_factor, 1.0, 1.0, -2.0]
        if probability_of_return < 0 or probability_of_return > 1.0:
            raise ValueError(f"probability_of_return parameter passed by not a probability: {probability_of_return}")

        mig = migration._from_demog_and_param_gravity(self, gravity_params=gravity_params,
                                                      id_ref=id_ref,
                                                      migration_type=migration.Migration.LOCAL)
        # migration_file_path = "commuter_migration.bin"
        migration_file_path = tempfile.NamedTemporaryFile().name + ".bin"
        mig.to_file(migration_file_path)
        self.migration_files.append(migration_file_path)

        if self.implicits is not None:
            self.implicits.append(partial(DT._set_local_migration_roundtrip_probability,
                                          probability_of_return=probability_of_return))
            self.implicits.append(partial(DT._set_local_migration_filename,
                                          file_name=pathlib.PurePath(migration_file_path).name))
        self.SetMigrationPattern("srt")

    def SetOneWayMigration(self, rates_path, id_ref='long term migration'):
        """
        Set one way migration. You can use the x_Regional_Migration configuration parameter to tune/calibrate.

        Args:
            rates_path: Path to csv file with node-to-node migration rates. Format is: source (node id),destination
                (node id),rate.
            id_ref: Text string that appears in the migration file itself; needs to match corresponding demographics
                file.
        """

        import pathlib
        mig = migration.from_csv(pathlib.Path(rates_path), id_ref=id_ref, mig_type=migration.Migration.REGIONAL)
        migration_file_path = tempfile.NamedTemporaryFile().name + ".bin"
        mig.to_file(migration_file_path)
        self.migration_files.append(migration_file_path)

        if self.implicits is not None:
            self.implicits.append(partial(DT._set_regional_migration_roundtrip_probability, probability_of_return=0.0))
            self.implicits.append(partial(DT._set_regional_migration_filenames,
                                          file_name=pathlib.PurePath(migration_file_path).name))
        self.SetMigrationPattern("srt")

    def SetSimpleVitalDynamics(self, crude_birth_rate=CrudeRate(40), crude_death_rate=CrudeRate(20), node_ids=None):
        """
        Set fertility, mortality, and initial age with single birth rate and single mortality rate.

        Args:
            crude_birth_rate: Birth rate, per year per kiloperson.
            crude_death_rate: Mortality rate, per year per kiloperson.
            node_ids: Optional list of nodes to limit these settings to.

        """

        self.SetBirthRate(crude_birth_rate, node_ids)
        self.SetMortalityRate(crude_death_rate, node_ids)
        self.SetEquilibriumAgeDistFromBirthAndMortRates(crude_birth_rate, crude_death_rate, node_ids)

    def SetEquilibriumVitalDynamics(self, crude_birth_rate=CrudeRate(40), node_ids=None):
        """
        Set fertility, mortality, and initial age with single rate and mortality to achieve steady state population.

        Args:
            crude_birth_rate: Birth rate. And mortality rate.
            node_ids: Optional list of nodes to limit these settings to.

        """

        self.SetSimpleVitalDynamics(crude_birth_rate, crude_birth_rate, node_ids)

    def SetEquilibriumVitalDynamicsFromWorldBank(self, wb_births_df, country, year, node_ids=None):
        """
        Set steady-state fertility, mortality, and initial age with rates from world bank, for given country and year.

        Args:
            wb_births_df: Pandas dataframe with World Bank birth rate by country and year.
            country: Country to pick from World Bank dataset.
            year: Year to pick from World Bank dataset.
            node_ids: Optional list of nodes to limit these settings to.

        """

        try:
            birth_rate = CrudeRate(wb_births_df[wb_births_df['Country Name'] == country][str(year)].tolist()[0])
            # result_scale_factor = 2.74e-06 # assuming world bank units for input
            # birth_rate *= result_scale_factor # from births per 1000 pop per year to per person per day
        except Exception as ex:
            raise ValueError(f"Exception trying to find {year} and {country} in dataframe.\n{ex}")
        self.SetEquilibriumVitalDynamics(birth_rate, node_ids)

    def SetIndividualAttributesWithFertMort(self, crude_birth_rate=CrudeRate(40), crude_mort_rate=CrudeRate(20)):
        self.raw['Defaults']['IndividualAttributes'] = {}
        DT.NoInitialPrevalence(self)
        DT.EveryoneInitiallySusceptible(self)
        if type(crude_birth_rate) is float or type(crude_birth_rate) is int:
            crude_birth_rate = CrudeRate(crude_birth_rate)
        if type(crude_mort_rate) is float or type(crude_mort_rate) is int:
            crude_mort_rate = CrudeRate(crude_mort_rate)
        self.SetSimpleVitalDynamics(crude_birth_rate, crude_mort_rate)

    def AddIndividualPropertyAndHINT(self, Property: str, Values: List[str], InitialDistribution: List[float] = None,
                                     TransmissionMatrix: List[List[float]] = None, Transitions: List = None,
                                     node_ids: List[int] = None, overwrite_existing: bool = False) -> None:
        """
        Add Individual Properties, including an optional HINT configuration matrix.

        Individual properties act as 'labels' on model agents that can be used for identifying and targeting
        subpopulations in campaign elements and reports. E.g. model agents may be given a property ('Accessibility')
        that labels them as either having access to health care (value: 'Yes') or not (value: 'No').

        Property-based heterogeneous disease transmission (HINT) is available for generic, environmental, typhoid,
        airborne, or TBHIV simulations as other simulation types have parameters for modeling the heterogeneity of
        transmission. By default, transmission is assumed to occur homogeneously among the population within a node.

        Note: EMOD requires individual property key and values (Property and Values args) to be the same across all
            nodes. The individual distributions of individual properties (InitialDistribution) can vary acros nodes.

        Documentation of individual properties and HINT:
            https://docs.idmod.org/projects/emod-generic/en/latest/model-properties.html
            https://docs.idmod.org/projects/emod-generic/en/latest/model-hint.html

        Args:
            Property: a new individual property key to add (if property already exists an exception is raised
                unless overwrite_existing is True).
            Values: the valid values of the new property key
            InitialDistribution: The fractional initial distribution of each valid Values entry. Order must match
                Values argument.
            TransmissionMatrix: HINT transmission matrix.
            node_ids: The node ids to apply changes to. None or 0 means the 'Defaults' node.
            overwrite_existing: Determines if an error is thrown if the IP is found pre-existing at a specified node.
                False: throw exception. True: overwrite the existing property.
        Returns:
            None
        """
        node_dicts = self._select_node_dicts(node_ids=node_ids)
        for node_dict in node_dicts:
            if 'IndividualProperties' not in node_dict:
                node_dict['IndividualProperties'] = []

            if not overwrite_existing and any([Property == x['Property'] for x in node_dict['IndividualProperties']]):
                raise ValueError("Property Type '{0}' already present in IndividualProperties list".format(Property))

            # Check if Property is in whitelist. If not, auto-set Disable_IP_Whitelist
            ip_whitelist = ["Age_Bin", "Accessibility", "Geographic", "Place", "Risk", "QualityOfCare", "HasActiveTB",
                            "InterventionStatus"]
            if Property not in ip_whitelist:
                def update_config(config):
                    config.parameters["Disable_IP_Whitelist"] = 1
                    return config

                if self.implicits is not None:
                    self.implicits.append(update_config)
                # TODO: if the implicits are None, should they now be [update_config] ??

            tm_dict = None if TransmissionMatrix is None else {"Route": "Contact", "Matrix": TransmissionMatrix}
            individual_property = IndividualProperty(property=Property,
                                                     values=Values,
                                                     initial_distribution=InitialDistribution,
                                                     transitions=Transitions,
                                                     transmission_matrix=tm_dict)
            node_dict['IndividualProperties'].append(individual_property.to_dict())

        if TransmissionMatrix is not None:
            def update_config(config):
                config.parameters.Enable_Heterogeneous_Intranode_Transmission = 1
                return config

            if self.implicits is not None:
                self.implicits.append(update_config)

    def AddAgeDependentTransmission(self, Age_Bin_Edges_In_Years: List = None,
                                    TransmissionMatrix: List[List[float]] = None):
        """
        Set up age-based HINT. Since ages are a first class property of an agent, Age_Bin is a special case
        of HINT. We don't specify a distribution, but we do specify the age bin edges, in units of years.
        So if Age_Bin_Edges_In_Years = [0, 10, 65, -1] it means you'll have 3 age buckets: 0-10, 10-65, & 65+.
        Always 'book-end' with 0 and -1.

        Args:
            Age_Bin_Edges_In_Years: array (or list) of floating point values, representing the age bucket bounderies.
            TransmissionMatrix: 2-D array of floating point values, representing epi connectedness of the age buckets.

        """
        if Age_Bin_Edges_In_Years is None:
            Age_Bin_Edges_In_Years = [0, 1, 2, -1]

        if TransmissionMatrix is None:
            TransmissionMatrix = [[1.0, 1.0, 1.0], [1.0, 1.0, 1.0], [1.0, 1.0, 1.0]]

        if Age_Bin_Edges_In_Years[0] != 0:
            raise ValueError("First value of 'Age_Bin_Edges_In_Years' must be 0.")
        if Age_Bin_Edges_In_Years[-1] != -1:
            raise ValueError("Last value of 'Age_Bin_Edges_In_Years' must be -1.")
        num_age_buckets = len(Age_Bin_Edges_In_Years)-1
        if len(TransmissionMatrix) != num_age_buckets:
            raise ValueError(f"Number of rows of TransmissionMatrix ({len(TransmissionMatrix)}) must match number of "
                             f"age buckets ({num_age_buckets}).")

        for idx in range(len(TransmissionMatrix)):
            num_cols = len(TransmissionMatrix[idx])
            if num_cols != num_age_buckets:
                raise ValueError(f"Number of columns of TransmissionMatrix ({len(TransmissionMatrix[idx])}) must match "
                                 f"number of age buckets ({num_age_buckets}).")

        self.AddIndividualPropertyAndHINT("Age_Bin", Age_Bin_Edges_In_Years, None, TransmissionMatrix)

        def update_config(config):
            config.parameters.Enable_Heterogeneous_Intranode_Transmission = 1
            return config

        if self.implicits is not None:
            self.implicits.append(update_config)

    def SetDefaultIndividualAttributes(self): 
        """
        NOTE: This is very Measles-ish. We might want to move into MeaslesDemographics
        """
        self.raw['Defaults']['IndividualAttributes'] = {}
        DT.NoInitialPrevalence(self)
        # Age distribution from UNWPP
        DT.AgeStructureUNWPP(self)
        # Mortality rates carried over from Nigeria DHS
        DT.MortalityStructureNigeriaDHS(self)

    def SetMinimalNodeAttributes(self): 
        self.SetDefaultNodeAttributes(birth=False)

    # WB is births per 1000 pop per year 
    # DTK is births per person per day.
    def SetBirthRate(self, birth_rate, node_ids=None):
        """
        Set Default birth rate to birth_rate. Turn on Vital Dynamics and Births implicitly.
        """
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
        self.implicits.append(DT._set_enable_births)

    def SetMortalityRate(self, mortality_rate: CrudeRate, node_ids: List[int] = None):
        """
        Set constant mortality rate to mort_rate. Turn on Enable_Natural_Mortality implicitly.
        """
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
                self.get_node_by_id(node_id=node_id)._set_mortality_distribution(distribution)

        if self.implicits is not None:
            self.implicits.append(DT._set_mortality_age_gender)

    def SetMortalityDistribution(self, distribution: IndividualAttributes.MortalityDistribution = None,
                                 node_ids: List[int] = None):
        """
        Set a default mortality distribution for all nodes or per node. Turn on Enable_Natural_Mortality implicitly.

        Args:
            distribution: distribution
            node_ids: a list of node_ids

        Returns:
            None
        """
        if node_ids is None:
            self.raw["Defaults"]["IndividualAttributes"]["MortalityDistribution"] = distribution.to_dict()
        else:
            for node_id in node_ids:
                self.get_node_by_id(node_id=node_id)._set_mortality_distribution(distribution)

        if self.implicits is not None:
            self.implicits.append(DT._set_mortality_age_gender)

    def SetVitalDynamicsFromWHOFile(self, pop_dat_file: pathlib.Path, base_year: int, start_year: int = 1950,
                                    max_daily_mort: float = 0.01,
                                    mortality_rate_x_values: list = DemographicsTemplatesConstants.Mortality_Rates_Mod30_5yrs_Xval,
                                    years_per_age_bin: int = 5):
        """
        Build demographics from UN World Population data.
        Args:
            pop_dat_file: path to UN World Population data file
            base_year: Base year/Reference year
            start_year: Read in the pop_dat_file starting with year 'start_year'
            years_per_age_bin: The number of years in one age bin, i.e. in one row of the UN World Population data file
            max_daily_mort: Maximum daily mortality rate
            mortality_rate_x_values: The distribution of non-disease mortality for a population.

        Returns:
            IndividualAttributes, NodeAttributes
        """
        attributes = DT.demographicsBuilder(pop_dat_file, base_year, start_year, max_daily_mort,
                                            mortality_rate_x_values, years_per_age_bin)
        self.SetVitalDynamicsFromTemplate(attributes)

    def SetMortalityDistributionFemale(self, distribution: IndividualAttributes.MortalityDistribution = None,
                                       node_ids: List[int] = None):
        """
        Set a default female mortality distribution for all nodes or per node. Turn on Enable_Natural_Mortality
            implicitly.

        Args:
            distribution: distribution
            node_ids: a list of node_ids

        Returns:
            None
        """

        if node_ids is None:
            self.raw["Defaults"]["IndividualAttributes"]["MortalityDistributionFemale"] = distribution.to_dict()
        else:
            for node_id in node_ids:
                self.get_node_by_id(node_id=node_id)._set_mortality_distribution_female(distribution)

        if self.implicits is not None:
            self.implicits.append(DT._set_mortality_age_gender)

    def SetMortalityDistributionMale(self, distribution: IndividualAttributes.MortalityDistribution = None,
                                     node_ids: List[int] = None):
        """
        Set a default male mortality distribution for all nodes or per node. Turn on Enable_Natural_Mortality
            implicitly.

        Args:
            distribution: distribution
            node_ids: a list of node_ids

        Returns:
            None
        """
        if node_ids is None:
            self.raw["Defaults"]["IndividualAttributes"]["MortalityDistributionMale"] = distribution.to_dict()
        else:
            for node_id in node_ids:
                self.get_node_by_id(node_id=node_id)._set_mortality_distribution_male(distribution)

        if self.implicits is not None:
            self.implicits.append(DT._set_mortality_age_gender)

    def SetMortalityOverTimeFromData(self, data_csv, base_year, node_ids: List = None):
        """
        Set default mortality rates for all nodes or per node. Turn on mortality configs implicitly. You can use 
        the x_Other_Mortality configuration parameter to tune/calibrate.

        Args:
            data_csv: Path to csv file with the mortality rates by calendar year and age bucket.
            base_year: The calendar year the sim is treating as the base.
            node_ids: Optional list of node ids to apply this to. Defaults to all.

        Returns:
            None
        """
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
        num_years = year_end-year_start+1
        rel_years = list()
        for year in range(year_start, year_start+num_years):
            mort_data = list(df[str(year)])
            rel_years.append(year-base_year)

        age_key = None
        for trykey in df.keys():
            if trykey.lower().startswith("age"):
                age_key = trykey
                raw_age_bins = list(df[age_key])

        if age_key is None:
            raise ValueError(f"Failed to find 'Age_Bin' (or similar) column in the csv dataset. Cannot process.")

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
        
        distrib = IndividualAttributes.MortalityDistribution(
                result_values=rates,
                axis_names=["age", "year"],
                axis_scale_factors=[365, 1],
                axis_units="N/A",
                num_distribution_axes=len(num_pop_groups),
                num_population_groups=num_pop_groups,
                population_groups=pop_groups,
                result_scale_factor=2.74e-06,
                result_units="annual deaths per 1000 individuals"
        )

        if not node_ids:
            self.raw["Defaults"]["IndividualAttributes"]["MortalityDistributionMale"] = distrib.to_dict()
            self.raw["Defaults"]["IndividualAttributes"]["MortalityDistributionFemale"] = distrib.to_dict()
        else:
            if len(self.nodes) == 1 and len(node_ids) > 1:
                raise ValueError(f"User specified several node ids for single node demographics setup.")
            for node_id in node_ids:
                self.get_node_by_id(node_id=node_id)._set_mortality_distribution_male(distrib)
                self.get_node_by_id(node_id=node_id)._set_mortality_distribution_female(distrib)

        if self.implicits is not None:
            self.implicits.append(DT._set_mortality_age_gender_year)

    def SetAgeDistribution(self, distribution: IndividualAttributes.AgeDistribution, node_ids: List[int] = None):
        """
        Set a default age distribution for all nodes or per node. Sets distribution type to COMPLEX implicitly.
        Args:
            distribution: age distribution
            node_ids: a list of node_ids

        Returns:
            None
        """
        if node_ids is None:
            self.raw["Defaults"]["IndividualAttributes"]["AgeDistribution"] = distribution.to_dict()
        else:
            for node_id in node_ids:
                self.get_node_by_id(node_id=node_id)._set_age_distribution(distribution)

        if self.implicits is not None:
            self.implicits.append(DT._set_age_complex)

    def SetDefaultNodeAttributes(self, birth=True):
        """
        Set the default NodeAttributes (Altitude, Airport, Region, Seaport), optionally including birth, 
        which is most important actually.
        """
        self.raw['Defaults']['NodeAttributes'] = {
                    "Altitude": 0,
                    "Airport": 1,  # why are these still needed?
                    "Region": 1,
                    "Seaport": 1
        }
        if birth:
            self.SetBirthRate(YearlyRate(math.log(1.03567)))

    def SetDefaultIndividualProperties(self):
        """
        Initialize Individual Properties to empty.
        """
        self.raw['Defaults']['IndividualProperties'] = []

    def SetDefaultProperties(self): 
        """
        Set a bunch of defaults (age structure, initial susceptibility and initial prevalencec) to sensible values.
        """
        self.SetDefaultNodeAttributes()
        self.SetDefaultIndividualAttributes()  # Distributions for initialization of immunity, risk heterogeneity, etc.
        self.SetDefaultIndividualProperties()  # Individual properties like accessibility, for targeting interventions

    def SetDefaultPropertiesFertMort(self, crude_birth_rate=CrudeRate(40), crude_mort_rate=CrudeRate(20)):
        """
        Set a bunch of defaults (birth rates, death rates, age structure, initial susceptibility and initial
        prevalence) to sensible values.
        """
        self.SetDefaultNodeAttributes() 
        self.SetDefaultIndividualAttributes()  # Distributions for initialization of immunity, risk heterogeneity, etc.
        self.SetBirthRate(crude_birth_rate)
        self.SetMortalityRate(crude_mort_rate)
        # self.SetDefaultIndividualProperties() # Individual properties like accessibility, for targeting interventions

    def SetDefaultFromTemplate(self, template, setter_fn=None):
        """
        Add to the default IndividualAttributes using the input template (raw json) and set corresponding 
        config values per the setter_fn. The template should always be constructed by a 
        function in DemographicsTemplates. Eventually this function will be hidden and only 
        accessed via separate application-specific API functions such as the ones below.
        """
        # TBD: Add some error checking. Make sure IndividualAttributes are Individual, not individual.
        self.raw['Defaults']['IndividualAttributes'].update(template)
        if self.implicits is not None and setter_fn is not None:
            self.implicits.append(setter_fn)

    def SetNodeDefaultFromTemplate(self, template, setter_fn):
        """
        Add to the default NodeAttributes using the input template (raw json) and set 
        corresponding config values per the setter_fn. The template should always 
        be constructed by a function in DemographicsTemplates. Eventually this function 
        will be hidden and only accessed via separate application-specific API functions 
        such as the ones below.
        """
        # TBD: Add some error checking. Make sure NodeAttributes are Node, not individual.
        self.raw['Defaults']['NodeAttributes'].update(template)
        if self.implicits is not None:
            self.implicits.append(setter_fn)

    def SetVitalDynamicsFromTemplate(self, template):
        # Set IndividualAttributes and config parameters
        self.SetDefaultFromTemplate(template[0].to_dict())
        if self.implicits is not None:
            self.implicits.append(DT._set_age_complex)
            self.implicits.append(DT._set_mortality_age_gender_year)

        # Set NodeAttributes and config parameters
        self.SetNodeDefaultFromTemplate(template[1].to_dict(), DT._set_enable_births)

    def SetEquilibriumAgeDistFromBirthAndMortRates(self, CrudeBirthRate=CrudeRate(40), CrudeMortRate=CrudeRate(20),
                                                   node_ids=None):
        """
        Set the inital ages of the population to a sensible equilibrium profile based on the specified input birth and
        death rates. Note this does not set the fertility and mortality rates.
        """
        yearly_birth_rate = YearlyRate(CrudeBirthRate)
        yearly_mortality_rate = YearlyRate(CrudeMortRate)
        dist = DT._EquilibriumAgeDistFromBirthAndMortRates(yearly_birth_rate, yearly_mortality_rate)
        setter_fn = DT._set_age_complex
        if node_ids is None:
            self.SetDefaultFromTemplate(dist, setter_fn)
        else:
            new_dist = IndividualAttributes.AgeDistribution()
            dist = new_dist.from_dict(dist["AgeDistribution"])
            for node in node_ids:
                self.get_node_by_id(node_id=node)._set_age_distribution(dist)
            self.implicits.append(setter_fn)

    def SetInitialAgeExponential(self, rate=0.0001068, description=""):
        """
        Set the initial age of the population to an exponential distribution with a specified rate.
        :param  rate: rate
        :param  description: description, why was this distribution chosen
        """
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
        if not description:
            description = f"Setting initial age distribution like Sub Saharan Africa, drawing from exponential " \
                          f"distribution."

        self.SetInitialAgeExponential(description=description)  # use default rate

    def SetOverdispersion(self, new_overdispersion_value, nodes: List = None):
        """
        Set the overdispersion value for the specified nodes (all if empty).
        """
        if nodes is None:
            nodes = []

        def enable_overdispersion(config):
            print("DEBUG: Setting 'Enable_Infection_Rate_Overdispersion' to 1.")
            config.parameters.Enable_Infection_Rate_Overdispersion = 1
            return config

        if self.implicits is not None:
            self.implicits.append(enable_overdispersion)
        self.raw['Defaults']['NodeAttributes']["InfectivityOverdispersion"] = new_overdispersion_value

    def SetConstantSusceptibility(self):
        """
        Set the initial susceptibilty for each new individual to a constant value of 1.0.
        """
        DT.InitSusceptConstant(self)

    def SetInitPrevFromUniformDraw(self, min_init_prev, max_init_prev, description=""):
        """
        Set Initial Prevalence (one value per node) drawn from an uniform distribution.
        :param  min_init_prev: minimal initial prevalence
        :param  max_init_prev: maximal initial prevalence
        :param  description: description, why were these parameters chosen?
        """
        if not description:
            description = f"Drawing prevalence from uniform distribution, min={min_init_prev} and max={max_init_prev}"

        DT.InitPrevUniform(self, min_init_prev, max_init_prev, description)

    def SetConstantRisk(self, risk=1, description=""):
        """
        Set the initial risk for each new individual to the same value, defaults to full risk
        :param  risk: risk
        :param  description: description, why was this parameter chosen?
        """
        if not description:
            description = f"Risk is set to constant, risk={risk}"

        if risk == 1:
            DT.FullRisk(self, description)
        else:
            # Could add a DT.ConstantRisk but I like using less code.
            DT.InitRiskUniform(self, risk, risk, description)

    def SetHeteroRiskUniformDist(self, min_risk=0, max_risk=1):
        """
        Set the initial risk for each new individual to a value drawn from a uniform distribution.
        """
        DT.InitRiskUniform(self, min_lim=min_risk, max_lim=max_risk)

    def SetHeteroRiskLognormalDist(self, mean=1.0, sigma=0):
        """
        Set the initial risk for each new individual to a value drawn from a log-normal distribution.
        """
        DT.InitRiskLogNormal(self, mean=mean, sigma=sigma)

    def SetHeteroRiskExponDist(self, mean=1.0):
        """
        Set the initial risk for each new individual to a value drawn from an exponential distribution.
        """
        DT.InitRiskExponential(self, mean=mean)

    def AddMortalityByAgeSexAndYear(self, age_bin_boundaries_in_years: List[float],
                                    year_bin_boundaries: List[float],
                                    male_mortality_rates: List[List[float]],
                                    female_mortality_rates: List[List[float]]):

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

        mort_distr_male = IndividualAttributes.MortalityDistribution(axis_names=axis_names,
                                                                     axis_scale_factors=axis_scale_factors,
                                                                     num_population_groups=num_population_groups,
                                                                     population_groups=population_groups,
                                                                     # result_scale_factor=result_values * scale_factor
                                                                     result_scale_factor=1.0,
                                                                     result_values=male_mortality_rates)
        self.SetMortalityDistributionMale(mort_distr_male)

        mort_distr_female = IndividualAttributes.MortalityDistribution(axis_names=axis_names,
                                                                       axis_scale_factors=axis_scale_factors,
                                                                       num_population_groups=num_population_groups,
                                                                       population_groups=population_groups,
                                                                       # result_scale_factor=result_values *scale_factor
                                                                       result_scale_factor=1.0,
                                                                       result_values=female_mortality_rates)
        self.SetMortalityDistributionFemale(mort_distr_female)

        if self.implicits is not None:
            self.implicits.append(DT._set_mortality_age_gender_year)

    def _SetInfectivityMultiplierByNode(self, node_id_to_multplier):
        raise ValueError("Not Yet Implemented.")

    def SetFertilityOverTimeFromParams(self, years_region1, years_region2, start_rate, inflection_rate, end_rate,
                                       node_ids: List = None):
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
            rate = start_rate + (inflection_rate-start_rate)*(i/years_region1)
            rates.append(rate)
        for i in range(years_region2):
            rate = inflection_rate + (end_rate-inflection_rate)*(i/years_region2)
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
                raise ValueError(f"User specified several node ids for single node demographics setup.")
            for node_id in node_ids:
                self.get_node_by_id(node_id=node_id)._set_fertility_distribution(dist)
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
            results_scale_factor=1.0/365.0) -> [Dict, Dict]:
        """
        Calculate and set the expected natural mortality by age, sex, and year from data, predicting what it would
        have been without disease (HIV-only).
        """
        from collections import OrderedDict
        from sklearn.linear_model import LinearRegression
        from functools import reduce

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
        df_list_future = []
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


# TODO: Move this class to a new file and update imports
#  https://github.com/InstituteforDiseaseModeling/emod-api/issues/689
class DemographicsOverlay(DemographicsBase):
    """
    In contrast to class :py:obj:`emod_api:emod_api.demographics.Demographics` this class does not set any defaults.
    It inherits from :py:obj:`emod_api:emod_api.demographics.DemographicsBase` so all functions that can be used to
    create demographics can also be used to create an overlay file. Parameters can be changed/set specifically by
    passing node_id, individual attributes, and individual attributes to the constructor.
    """

    def __init__(self, nodes: list = None,
                 idref: str = None,
                 individual_attributes=None,
                 node_attributes=None):
        """
        A class to create demographic overlays.
        Args:
            nodes: Overlay is applied to these nodes.
            idref: a name used to indicate files (demographics, climate, and migration) are used together
            individual_attributes: Object of type
                :py:obj:`emod_api:emod_api.demographics.PropertiesAndAttributes.IndividualAttributes
                to overwrite individual attributes
            node_attributes:  Object of type
                :py:obj:`emod_api:emod_api.demographics.PropertiesAndAttributes.NodeAttributes
                to overwrite individual attributes
        """
        super(DemographicsOverlay, self).__init__(nodes=nodes, idref=idref)

        self.individual_attributes = individual_attributes
        self.node_attributes = node_attributes

        if self.individual_attributes is not None:
            self.raw["Defaults"]["IndividualAttributes"] = self.individual_attributes.to_dict()

        if self.node_attributes is not None:
            self.raw["Defaults"]["NodeAttributes"] = self.node_attributes.to_dict()

    def to_dict(self):

        d = {"Defaults": dict()}
        if self.raw["Defaults"]["IndividualAttributes"]:
            d["Defaults"]["IndividualAttributes"] = self.raw["Defaults"]["IndividualAttributes"]

        if self.raw["Defaults"]["NodeAttributes"]:
            d["Defaults"]["NodeAttributes"] = self.raw["Defaults"]["NodeAttributes"]

        if self.raw["Metadata"]:
            d["Metadata"] = self.raw["Metadata"]  # there is no metadata class

        if self.raw["Defaults"]["IndividualProperties"]:
            d["Defaults"]["IndividualProperties"] = self.raw["Defaults"]["IndividualProperties"]

        d["Nodes"] = [{"NodeID": n.forced_id} for n in self.nodes]

        return d

    def to_file(self, file_name="demographics_overlay.json"):
        """
        Write the contents of the instance to an EMOD-compatible (JSON) file.
        """
        with open(file_name, "w") as demo_override_f:
            json.dump(self.to_dict(), demo_override_f)


class Demographics(DemographicsBase):
    """
    This class is a container of data necessary to produce a EMOD-valid demographics input file. It can be initialized
    from an existing valid demographics.joson type file or from an array of valid Nodes.
    """
    def __init__(self, nodes: List[Node], idref: str = "Gridded world grump2.5arcmin", base_file: str = None,
                 default_node: Node = None):
        """
        A class to create demographics.
        :param nodes: list of Nodes
        :param idref: A name/reference
        :param base_file: A demographics file in json format
        :default_node: An optional node to use for default settings.
        """
        super().__init__(nodes=nodes, idref=idref, default_node=default_node)

        # HIV is expected to pass a default node. Malaria is not (for now).
        if default_node is None:
            if base_file:
                with open(base_file, "rb") as src:
                    self.raw = json.load(src)
            else:
                # adding and using this default configuration (True) as malaria may use it; I don't know. HIV does not.
                self.SetMinimalNodeAttributes()
                DT.NoInitialPrevalence(self)  # does this need to be called?
                DT.InitAgeUniform(self)

    def to_dict(self):
        # TODO: refactor this when emod-api Node.to_dict() is fixed, to be more simply:
        #  self.raw["Nodes"] = [node.to_dict() for node in self.nodes]
        #  https://github.com/InstituteforDiseaseModeling/emod-api/issues/702
        self.raw["Nodes"] = []

        for node in self.nodes:
            d = node.to_dict()
            d.update(node.meta)
            self.raw["Nodes"].append(d)

        # Update node count
        self.raw["Metadata"]["NodeCount"] = len(self.nodes)
        return self.raw

    def generate_file(self, name="demographics.json"):
        """
        Write the contents of the instance to an EMOD-compatible (JSON) file.
        """
        with open(name, "w") as output:
            json.dump(self.to_dict(), output, indent=3, sort_keys=True)
        return name
