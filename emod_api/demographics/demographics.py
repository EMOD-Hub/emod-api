import json
import numpy as np
import os
import pandas as pd

from typing import List

from emod_api.demographics.node import Node
from emod_api.demographics.properties_and_attributes import NodeAttributes
from emod_api.demographics.demographics_base import DemographicsBase
from emod_api.demographics.service import service




class Demographics(DemographicsBase):
    """
    This class is a container of data necessary to produce a EMOD-valid demographics input file.
    """
    def __init__(self, nodes: List[Node], idref: str = "Gridded world grump2.5arcmin", default_node: Node = None):
        """
        A class to create demographics.
        :param nodes: list of Nodes
        :param idref: A name/reference
        :default_node: An optional node to use for default settings.
        """
        super().__init__(nodes=nodes, idref=idref, default_node=default_node)

        # set some standard EMOD defaults
        for node in self._all_nodes:
            node.node_attributes.airport = 1
            node.node_attributes.seaport = 1
            node.node_attributes.region = 1


    def generate_file(self, name="demographics.json"):
        """
        Write the contents of the object to an EMOD-compatible (JSON) file.
        """
        with open(name, "w") as output:
            json.dump(self.to_dict(), output, indent=3, sort_keys=True)
        return name

    @classmethod
    def from_template_node(cls,
                           lat=0,
                           lon=0,
                           pop=1000000,
                           name="Erewhon",
                           forced_id=1):
        """
        Create a single-node Demographics object from a few parameters.
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
                 input_file,
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
                            pop_filename_in,
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
        return cls.from_csv(grid_file_path, res, id_ref)


    @classmethod
    def from_pop_csv(cls,
                     pop_filename_in,
                     res=1 / 120,
                     id_ref="from_raster",
                     pop_filename_out="spatial_gridded_pop_dir",
                     site="No_Site"):
        import warnings
        warnings.warn("from_pop_csv is deprecated. Please use from_pop_csv.", DeprecationWarning, stacklevel=2)
        return cls.from_pop_raster_csv(pop_filename_in, res, id_ref, pop_filename_out, site)
