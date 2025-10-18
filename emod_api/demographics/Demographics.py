# TODO: There are many, many methods in this file that duplicate in various ways the new demographics distribution
#  setting code in emodpy and emod-api. We should decide what we want to keep and where the kept parts should live
#  (emodpy, emod-api).
#  https://github.com/InstituteforDiseaseModeling/emod-api-old/issues/749

import json

import numpy as np
import os
import pandas as pd

from typing import List, Dict

from emod_api.demographics import DemographicsTemplates as DT
from emod_api.demographics.Node import Node
from emod_api.demographics.PropertiesAndAttributes import NodeAttributes
from emod_api.demographics.demographics_base import DemographicsBase
from emod_api.demographics.service import service


# TODO: replace all self.raw usage to use Node objects?
#  https://github.com/InstituteforDiseaseModeling/emod-api/issues/687


# TODO: All following "from_X()" methods should be class methods of Demographics
#  https://github.com/InstituteforDiseaseModeling/emod-api/issues/688
def from_template_node(lat=0,
                       lon=0,
                       pop=1000000,
                       name="Erewhon",
                       forced_id=1):
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


def get_node_pops_from_params(tot_pop,
                              num_nodes,
                              frac_rural) -> list:
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


def from_params(tot_pop: int = 1000000,
                num_nodes: int = 100,
                frac_rural: float = 0.3,
                id_ref: str = "from_params",
                random_2d_grid: bool = False):
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
        (Demographics): New Demographics object
    """
    if frac_rural > 1.0:
        raise ValueError("frac_rural can't be greater than 1.0")
    if frac_rural < 0.0:
        raise ValueError("frac_rural can't be less than 0")
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


# The below implements the standard naming convention for DTK nodes based on latitude and longitude.
# The node ID encodes both lat and long at a specified pixel resolution, and I've maintained this
# convention even when running on spatial setups that are not non-uniform grids.
def _node_id_from_lat_lon_res(lat: float, lon: float, res: float = 30 / 3600) -> int:
    node_id = int((np.floor((lon + 180) / res) * (2 ** 16)).astype(np.uint) + (np.floor((lat + 90) / res) + 1).astype(np.uint))
    return node_id


def from_csv(input_file,
             res=30 / 3600,
             id_ref="from_csv"):
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
            pop = int(6 * row['under5_pop'])
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

        forced_id = int(_node_id_from_lat_lon_res(lat=lat, lon=lon, res=res)) if node_id is None else int(node_id)

        if 'loc' in row:
            place_name = str(row['loc'])
        else:
            place_name = None
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
    return Demographics(nodes=out_nodes, idref=id_ref)


# This will be the long-term API for this function.
def from_pop_raster_csv(pop_filename_in,
                        res=1 / 120,
                        id_ref="from_raster",
                        pop_filename_out="spatial_gridded_pop_dir",
                        site="No_Site"):
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
        (Demographics): New Demographics object based on the grid file.

    Raises:

    """
    grid_file_path = service._create_grid_files(pop_filename_in, pop_filename_out, site)
    print(f"{grid_file_path} grid file created.")
    return from_csv(grid_file_path, res, id_ref)


def from_pop_csv(pop_filename_in,
                 res=1 / 120,
                 id_ref="from_raster",
                 pop_filename_out="spatial_gridded_pop_dir",
                 site="No_Site"):
    """
        Deprecated. Please use from_pop_raster_csv.
    """
    return from_pop_raster_csv(pop_filename_in, res, id_ref, pop_filename_out, site)


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

    def to_dict(self) -> Dict:
        self.verify_demographics_integrity()
        self.raw["Nodes"] = [node.to_dict() for node in self.nodes]
        self.raw["Metadata"]["NodeCount"] = len(self.nodes)
        return self.raw

    def generate_file(self, name="demographics.json"):
        """
        Write the contents of the instance to an EMOD-compatible (JSON) file.
        """
        with open(name, "w") as output:
            json.dump(self.to_dict(), output, indent=3, sort_keys=True)
        return name
