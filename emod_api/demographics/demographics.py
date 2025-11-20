import json
import numpy as np
import pandas as pd
from typing import List, Dict

from emod_api.demographics.demographics_base import DemographicsBase
from emod_api.demographics.node import Node
from emod_api.demographics.properties_and_attributes import NodeAttributes
from emod_api.demographics.service import service


class Demographics(DemographicsBase):
    """
    This class is a container of data necessary to produce a EMOD-valid demographics input file.
    """
    def __init__(self, nodes: List[Node], idref: str = "Gridded world grump2.5arcmin", default_node: Node = None,
                 metadata: Dict = None, set_defaults: bool = True):
        """
        Object representation of an EMOD Demographics input (json) file.

        Args:
            nodes: list(Node) nodes to include in the Demographics object.
            idref: (string) an identifier for the Demographics file. Used to co-identify sets of Demographics/overlay
                files.
            default_node: (Node) Represents default values for all nodes, unless overridden on a per-node basis.
            metadata: (Dict) set the demographics metadata to the supplied dictionary. Default yields default
                metadata values.
            set_defaults: (bool) Whether to set default node attributes on the default node. Defaults to True.
        """
        super().__init__(nodes=nodes, idref=idref, default_node=default_node, metadata=metadata)

        # set some standard EMOD defaults
        if set_defaults:
            for node in self._all_nodes:
                node.node_attributes.airport = 1
                node.node_attributes.seaport = 1
                node.node_attributes.region = 1

    def to_file(self, path: str = "demographics.json") -> None:
        """
        Write the Demographics object to an EMOD demograhpics json file.

        Args:
            path: (str) the filepath to write the file to. Default is "demographics.json".

        Returns:
            Nothing
        """
        with open(path, "w") as output:
            json.dump(self.to_dict(), output, indent=3, sort_keys=True)

    def generate_file(self, path: str = "demographics.json"):
        import warnings
        warnings.warn("generate_file() is deprecated. Please use to_file()", DeprecationWarning, stacklevel=2)
        self.to_file(path=path)

    @classmethod
    def from_file(cls, path: str) -> "Demographics":
        """
        Create a Demographics object from an EMOD-compatible demographics json file.

        Args:
            path (str): the file path to read from.:

        Returns:
            a Demographics object
        """

        with open(path, "rb") as src:
            demographics_dict = json.load(src)
        demographics_dict["Defaults"]["NodeID"] = 0  # This is a requirement of all emod-api Demographics objects
        implicit_functions = []
        nodes = []
        for node_dict in demographics_dict["Nodes"]:
            node, implicits = Node.from_data(data=node_dict)
            implicit_functions.extend(implicits)
            nodes.append(node)
        default_node, implicits = Node.from_data(data=demographics_dict["Defaults"])
        implicit_functions.extend(implicits)
        metadata = demographics_dict["Metadata"]
        idref = demographics_dict["Metadata"]["IdReference"]

        demographics = cls(nodes=nodes, default_node=default_node, idref=idref, metadata=metadata, set_defaults=False)
        demographics.implicits.extend(implicit_functions)
        return demographics

    @classmethod
    def from_template_node(cls,
                           lat: float = 0,
                           lon: float = 0,
                           pop: int = 1000000,
                           name: str = "Erewhon",
                           forced_id: int = 1) -> "Demographics":
        """
        Creates a basic, single-node Demographics object.

        Args:
            lat: (float, optional) latitude of node to be created. Default is 0.
            lon: (float, optional) longitude of node to be created. Default is 0.
            pop: (int, optional) number of people in the node to be created. Default is 1000000.
            name: (str, optional) name of node to be created. Default is Erewhon.
            forced_id: (int, optional) id of node to be created. Default is 1.

        Returns:
            A Demographics object
        """
        new_nodes = [Node(lat=lat, lon=lon, pop=pop, forced_id=forced_id, name=name)]
        return cls(nodes=new_nodes)

    # The below implements the standard naming convention for DTK nodes based on latitude and longitude.
    # The node ID encodes both lat and long at a specified pixel resolution, and I've maintained this
    # convention even when running on spatial setups that are not non-uniform grids.
    @staticmethod
    def _node_id_from_lat_lon_res(lat: float, lon: float, res: float = 30 / 3600) -> int:
        node_id = int((np.floor((lon + 180) / res) * (2 ** 16)).astype(np.uint) + (np.floor((lat + 90) / res) + 1).astype(np.uint))
        return node_id

    @classmethod
    def from_csv(cls,
                 input_file: str,
                 res: float = 30 / 3600,
                 id_ref: str = "from_csv") -> "Demographics":
        """
        Create an EMOD-compatible :py:class:`Demographics` instance from a csv population-by-node file.

        Args:
            input_file (str): the csv filepath to read from.
            res (float, optional): spatial resolution of the nodes in arc-seconds
            id_ref (str, optional): Description of the file source for co-identification of demographics objects/files.

        Returns:
            A Demographics object
        """
        def get_value(row, headers):
            for h in headers:
                if row.get(h) is not None:
                    return float(row.get(h))
            return None

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

            forced_id = int(cls._node_id_from_lat_lon_res(lat=lat, lon=lon, res=res)) if node_id is None else int(node_id)

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
        return cls(nodes=out_nodes, idref=id_ref)

    # This will be the long-term API for this function.
    @classmethod
    def from_pop_raster_csv(cls,
                            pop_filename_in: str,
                            res: float = 1 / 120,
                            id_ref: str = "from_raster",
                            pop_dirname_out: str = "spatial_gridded_pop_dir",
                            site: str = "No_Site") -> "Demographics":
        """
        Take a csv of a population-counts raster and build a grid for use with EMOD simulations.
        Grid size is specified by grid resolution in arcs or in kilometers. The population counts
        from the raster csv are then assigned to their nearest grid center and a new intermediate
        grid file is generated with latitude, longitude and population. This file is then fed to
        from_csv to generate a demographics object.

        Args:
            pop_filename_in (str): The filepath of the population-counts raster in CSV format.
            res (float, optional): The grid resolution in arcs or kilometers. Default is 1/120.
            id_ref (str, optional): Identifier reference for the grid. Default is "from_raster".
            pop_dirname_out (str, optional): The output directory name to hold the intermediate grid file.
                Default is "spatial_gridded_pop_dir".
            site (str, optional): The site name or identifier. Default is "No_Site".

        Returns:
            A Demographics object based on the input grid file.

        Raises:

        """
        grid_file_path = service._create_grid_files(point_records_file_in=pop_filename_in,
                                                    final_grid_files_dir=pop_dirname_out,
                                                    site=site)
        print(f"{grid_file_path} grid file created.")
        return cls.from_csv(input_file=grid_file_path, res=res, id_ref=id_ref)

    @classmethod
    def from_pop_csv(cls,
                     pop_filename_in: str,
                     res: float = 1 / 120,
                     id_ref: str = "from_raster",
                     pop_dirname_out: str = "spatial_gridded_pop_dir",
                     site: str = "No_Site") -> "Demographics":
        import warnings
        warnings.warn("from_pop_csv is deprecated. Please use from_pop_csv.", DeprecationWarning, stacklevel=2)
        return cls.from_pop_raster_csv(pop_filename_in=pop_filename_in,
                                       res=res,
                                       id_ref=id_ref,
                                       pop_dirname_out=pop_dirname_out,
                                       site=site)
