import json
from datetime import datetime
from enum import Enum
from typing import Literal

import pandas as pd

from emod_api.dtk_tools.demographics.DemographicsGeneratorConcern import (
    DemographicsGeneratorConcern,
    DemographicsGeneratorConcernChain,
)
from emod_api.demographics.Node import Node, nodeid_from_lat_lon
from emod_api.demographics.Demographics import Demographics
from emod_api.dtk_tools.support.General import init_logging

logger = init_logging("DemographicsGenerator")

# defaults section stored as module-variable, a dict (for now)
# structure will match file json structure initially, then be
# changed to a class with some abstraction from file format
defaults = {}

# Node class is used to store population data for spatial nodes
node_list = []

# Demographics is used to write the file to disk

CUSTOM_RESOLUTION = "custom"
DEFAULT_RESOLUTION = 30
VALID_RESOLUTIONS = {30: 30, 250: 250, CUSTOM_RESOLUTION: 30}


class InvalidResolution(BaseException):
    """
    Custom Exception
    """
    pass


class DemographicsType(Enum):
    """
    Enum
    """
    STATIC = "static"

    def __str__(self):
        return str(self.value)


def arcsec_to_deg(arcsec: float) -> float:
    """
    Arc second to degrees
    Args:
        arcsec: arcsecond as float

    Returns:
        arc second converted to degrees
    """
    return arcsec / 3600.0


def validate_res_in_arcsec(res_in_arcsec):
    """
    Validate that the resolution is valid
    Args:
        res_in_arcsec: Resolution in arsecond. Supported values can be found in VALID_RESOLUTIONS

    Returns:

    Raise:
        KeyError: If the resolution is invalid, a key error is raised

    """
    try:
        VALID_RESOLUTIONS[res_in_arcsec]
    except KeyError:
        raise InvalidResolution(
            f"{res_in_arcsec} is not a valid arcsecond resolution."
            f" Must be one of: {VALID_RESOLUTIONS.keys()}"
        )


class DemographicsGenerator:
    """
    Generates demographics file based on population input file.
    The population input file is csv with structure

    node_label, [lat], [lon], [pop]

    [columns] are optional
    """

    # mapping of requested arcsecond resolution -> demographic metadata arcsecond resolution.
    # All Hash values must be integers.
    def __init__(self,
                 nodes,
                 concerns: DemographicsGeneratorConcern | list[DemographicsGeneratorConcern] | None = None,
                 res_in_arcsec=CUSTOM_RESOLUTION,
                 node_id_from_lat_long: bool = False):
        """
        Initialize the Demographics generator
        Args:
            nodes: list of nodes
            node_concern (Optional[DemographicsNodeGeneratorConcern]): What DemographicsNodeGeneratorConcern should
                we apply. If not specified, we use the DefaultWorldBankEquilibriumConcern
                demographics_concern (Optional[DemographicsGeneratorConcern]): Any concern generator we need to execute
                after the Demographics object has been generated, but not saved
            res_in_arcsec: Simulation grid resolution
        """
        print("Creating DemographicsGenerator instance.")
        # self.nodes = nodes
        #  currently only static is implemented in generate_nodes(self)
        self.demographics_type = (
            DemographicsType.STATIC
        )  # could be 'static', 'growing' or a different type;
        self.node_id_from_lat_long = node_id_from_lat_long
        self.set_resolution(res_in_arcsec)

        if concerns and isinstance(concerns, list):
            concerns = DemographicsGeneratorConcernChain(*concerns)
        self.concerns = concerns

        # demographics data dictionary (working DTK demographics file when dumped as json)
        self.demographics = None

    def set_resolution(self,
                       res_in_arcsec: Literal[30, 250, CUSTOM_RESOLUTION]):
        """
        The canonical way to set arcsecond/degree resolutions on a DemographicsGenerator object. Verifies everything
        is set properly

        Args:
            res_in_arcsec: The requested resolution. e.g. 30, 250, 'custom'

        Returns: No return value.

        """
        validate_res_in_arcsec(res_in_arcsec)
        self.resolution = res_in_arcsec
        self.res_in_arcsec = VALID_RESOLUTIONS[res_in_arcsec]
        self.res_in_degrees = arcsec_to_deg(self.res_in_arcsec)
        if logger:
            logger.debug(
                f"Setting resolution to {self.res_in_arcsec} arcseconds ({self.res_in_degrees} deg.) from selection: {res_in_arcsec}"
            )

    def generate_nodes(self,
                       defaults) -> dict:
        """
        generate demographics file nodes


        The process for generating nodes starts with looping through the loaded demographics nodes. For each node,
        we:
        1. First determine the node's id. If the node has a forced id set, we use that. If we are
        using a custom resolution, we use the index(ie 1, 2, 3...). Lastly, we build the node id
        from the lat and lon id of the node

        2. We then start to populate the node_attributes and individual attributes for the current
        node. The node_attributes will have data loaded from the initial nodes fed into
        DemographicsGenerator. The individual attributes start off as an empty dict.

        3. We next determine the birthrate for the node. If the node attributes contains a Country
        element, we first lookup the birthrate from the World Pop data. We then build a
        MortalityDistribution configuration with country specific configuration elements and add
        that to the individual attributes. If there is no Country element in the node attributes,
        we set the birth rate to the default_birth_rate. This value was set in initialization of the
        DemographicsGenerator to the birth rate of the specified country from the world pop data

        4. We then calculate the per_node_birth_rate using get_per_node_birth_rate and then set the
        birth rate on the node attributes

        5. We then calculate the equilibrium_age_distribution and use that to create the
        AgeDistribution in individual_attributes

        6. We then add each new demographic node to a list to end returned at the end of the function

        """

        print("Generating demographics nodes.")
        nodes = [] # a list of dictionaries ('NodeID', "NodeAttributes', 'I...A...') we return

        def generate_node_id(i, node):
            node_id = None
            if node.forced_id:
                node_id = node.forced_id
            elif self.node_id_from_lat_long:
                node_id = nodeid_from_lat_lon(
                    float(node.lat), float(node.lon), self.res_in_degrees
                )
            else:
                node_id = i + 1
            return node_id

        for i, node in enumerate(node_list):
            # if res_in_degrees is custom assume node_ids are generated for a household-like setup
            # and not based on lat/lon
            node_id = generate_node_id(i, node)

            node_attributes = node.to_dict()
            individual_attributes = {}

            # Run our model through our Concern Set
            # UPDATE: NOT doing this anymore
            if self.concerns:
                self.concerns.update_node(
                    defaults, node, node_attributes, individual_attributes
                )

            print(f"Adding node {node_id}.")
            nodes.append(
                {
                    "NodeID": node_id,
                    "NodeAttributes": node_attributes,
                    "IndividualAttributes": individual_attributes,
                }
            )

        return nodes

    @staticmethod
    def __to_grid_file(grid_file_name: str,
                       demographics: Demographics,
                       include_attributes: list[str] | None = None,
                       node_attributes: list[str] | None = None):
        """
        Convert a demographics object(Full object represented as a nested dictionary) to a grid file

        Args:
            grid_file_name: Name of grid file to save
            demographics: Demographics object
            include_attributes: Attributes to include in export
            node_attributes: Optional list of attributes from the NodeAttributes path to include

        Returns:

        """

        node_attrs = ["Latitude", "Longitude", "InitialPopulation"]
        if include_attributes is None:
            include_attributes = []

        rows = []
        for node in demographics["Nodes"]:
            row = {
                k: v
                for k, v in node.items()
                if k in include_attributes or k in node_attrs
            }
            if node_attributes and "NodeAttributes" in row:
                other = {
                    k: v
                    for k, v in row["NodeAttributes"].items()
                    if k in node_attributes
                }
                row.update(other)
            rows.append(row)

        pd.DataFrame(rows).to_csv(grid_file_name)

    def generate_metadata(self) -> dict:
        """
        generate demographics file metadata
        """
        if self.resolution == CUSTOM_RESOLUTION:
            reference_id = "Custom user"
        else:
            reference_id = f"Gridded world grump{self.res_in_arcsec}arcsec"

        metadata = {
            "Author": "idm",
            "Tool": "dtk-tools",
            "IdReference": reference_id,
            "DateCreated": str(datetime.now()),
            "NodeCount": len(node_list),
            "Resolution": int(self.res_in_arcsec),
        }

        return metadata

    def generate_demographics(self):
        """
        return all demographics file components in a single dictionary; a valid DTK demographics file when dumped as json
        """
        print("Generating demographics dictionary from nodes and defaults.")
        if self.concerns:
            self.concerns.update_defaults(defaults)
        nodes = self.generate_nodes(defaults)
        self.demographics = {
            "Nodes": nodes,
            "Defaults": defaults,
            "Metadata": self.generate_metadata(),
        }

        return self.demographics


# MOVE TO demographics/DemographicsInputDataParsers.py
def from_dataframe(df: pd.DataFrame,
                   demographics_filename: str | None = None,
                   concerns: DemographicsGeneratorConcern | list[DemographicsGeneratorConcern] | None = None,
                   res_in_arcsec: Literal[30, 250, CUSTOM_RESOLUTION] = CUSTOM_RESOLUTION,
                   node_id_from_lat_long: bool = True,
                   default_population: int = 1000,
                   load_other_columns_as_attributes: bool = False,
                   include_columns: list[str] | None = None,
                   exclude_columns: list[str] | None = None,
                   nodeid_column_name: str | None = None,
                   latitude_column_name: str = "lat",
                   longitude_column_name: str = "lon",
                   population_column_name: str = "pop") -> Demographics:
    """

    Generates a demographics file from a dataframe

    Args:
        df: pandas DataFrame containing demographics information. Must contain all the columns specified by latitude_column_name,
            longitude_column_name. The population_column_name is optional. If not found, we fall back to default_population
        demographics_filename: demographics file to save the demographics file too. This is optional
            concerns (Optional[DemographicsNodeGeneratorConcern]): What DemographicsNodeGeneratorConcern should
            we apply. If not specified, we use the DefaultWorldBankEquilibriumConcern
        res_in_arcsec: Resolution in Arcseconds
        node_id_from_lat_long: Determine if we should calculate the node id from the lat long. By default this is
            true unless you also set res_in_arcsec to CUSTOM_RESOLUTION. When not using lat/long for ids, the first
            fallback it to check the node for a forced id. If that is not found, we assign it an index as id
        load_other_columns_as_attributes: Load additional columns from a csv file as node attributes
        include_columns: A list of columns that should be added as node attributes from the csv file. To be used in
            conjunction with load_other_columns_as_attributes.
        exclude_columns: A list of columns that should be ignored as attributes when
            load_other_columns_as_attributes is enabled. This cannot be combined with include_columns
        default_population: Default population. Only used if population_column_name does not exist
        nodeid_column_name: Column name to load nodeid values from
        latitude_column_name: Column name to load latitude values from
        longitude_column_name: Column name to load longitude values from
        population_column_name: Column name to load population values from

    Returns:
        demographics file as a dictionary
    """
    print("from_dataframe: Reading data.")
    warn_no_pop = False
    validate_res_in_arcsec(res_in_arcsec)
    res_in_deg = arcsec_to_deg(VALID_RESOLUTIONS[res_in_arcsec])

    if latitude_column_name not in df.columns.values:
        raise ValueError(
            f"Column {latitude_column_name} is required in input population file."
        )

    if longitude_column_name not in df.columns.values:
        raise ValueError(
            f"Column {longitude_column_name} is required in input population file."
        )

    if not warn_no_pop and population_column_name not in df.columns.values:
        warn_no_pop = True
        logger.warning(
            f"Could not locate population column{population_column_name}. Using the default "
            f"population value of {default_population}"
        )
        df[population_column_name] = default_population
    else:
        df[population_column_name] = df[population_column_name].astype(int)

    if not node_id_from_lat_long and not nodeid_column_name:
        logger.warning("NodeID column not specified. Reverting to csv  index + 1")
        df["node_label"] = df.index + 1
    if node_id_from_lat_long and "node_label" not in df.columns.values:
        df["node_label"] = df.apply(
            lambda x: nodeid_from_lat_lon(
                x[latitude_column_name], x[longitude_column_name], res_in_deg
            ),
            axis=1,
        )

    if include_columns:
        include_columns_verified = [
            x for x in include_columns if x in df.columns.values
        ]
        include_columns = include_columns_verified

    for r, row in df.iterrows():
        extra_attrs = {}

        if load_other_columns_as_attributes:
            if include_columns:
                extra_attrs = {x: row[x] for x in include_columns}
            elif exclude_columns:
                exclude_columns += [
                    latitude_column_name,
                    longitude_column_name,
                    population_column_name,
                    nodeid_column_name,
                ]
                extra_attrs = {
                    x: row[x] for x in df.columns.values if x not in exclude_columns
                }

        node_label = nodeid_column_name if nodeid_column_name else "node_label"

        # Append the newly created node to the list
        node_list.append(
            Node(
                row[latitude_column_name],
                row[longitude_column_name],
                row[population_column_name],
                forced_id=row[node_label],
                extra_attributes=extra_attrs,
            )
        )

    # node_list now exists -- what about defaults?

    # Option 1 to write
    df = Demographics(nodes=node_list)
    df.generate_file(demographics_filename + "_DF")

    # Option 2 to write
    if demographics_filename: # why would this be left unset? use case?
        # this is kind of ugly; we're inside a state class function, and creating
        # instance of the class just so we can call generate_demographics on it.
        # pretty sure we can do this all with static everything which kind of
        # eliminates need for class, just do as module variables.
        demo = DemographicsGenerator(node_list,
                                     concerns=concerns,
                                     res_in_arcsec=res_in_arcsec,
                                     node_id_from_lat_long=node_id_from_lat_long)
        demographics = demo.generate_demographics()

        print(f"Writing {demographics_filename}.")
        with open(demographics_filename, "w+") as demo_f:
            json.dump(demographics, demo_f, indent=4, sort_keys=True)
    else:
        print("demographics_filename was not defined. Not written.")
    return demographics


# MOVE TO demographics/DemographicsInputDataParsers.py
def from_file(population_input_file: str,
              demographics_filename: str | None = None,
              concerns: DemographicsGeneratorConcern | list[DemographicsGeneratorConcern] | None = None,
              res_in_arcsec: Literal[30, 250, CUSTOM_RESOLUTION] = CUSTOM_RESOLUTION,
              node_id_from_lat_long: bool = True,
              default_population: int = 1000,
              load_other_columns_as_attributes: bool = False,
              include_columns: list[str] | None = None,
              exclude_columns: list[str] | None = None,
              nodeid_column_name: str | None = None,
              latitude_column_name: str = "lat",
              longitude_column_name: str = "lon",
              population_column_name: str = "pop") -> Demographics:
    """

    Generates a demographics file from a CSV population

    Args:
        population_input_file: CSV population file. Must contain all the columns specified by latitude_column_name,
            longitude_column_name. The population_column_name is optional. If not found, we fall back to default_population
        demographics_filename: demographics file to save the demographics file too. This is optional
            concerns (Optional[DemographicsNodeGeneratorConcern]): What DemographicsNodeGeneratorConcern should
            we apply. If not specified, we use the DefaultWorldBankEquilibriumConcern
        res_in_arcsec: Resolution in Arcseconds
        node_id_from_lat_long: Determine if we should calculate the node id from the lat long. By default this is
            true unless you also set res_in_arcsec to CUSTOM_RESOLUTION. When not using lat/long for ids, the first
            fallback it to check the node for a forced id. If that is not found, we assign it an index as id
        load_other_columns_as_attributes: Load additional columns from a csv file as node attributes
        include_columns: A list of columns that should be added as node attributes from the csv file. To be used in
            conjunction with load_other_columns_as_attributes.
        exclude_columns: A list of columns that should be ignored as attributes when
            load_other_columns_as_attributes is enabled. This cannot be combined with include_columns
        default_population: Default population. Only used if population_column_name does not exist
        nodeid_column_name: Column name to load nodeid values from
        latitude_column_name: Column name to load latitude values from
        longitude_column_name: Column name to load longitude values from
        population_column_name: Column name to load population values from

    Returns:
        demographics file as a dictionary
    """
    print("from_gridfile: Reading data.")
    df = pd.read_csv(population_input_file)
    return from_dataframe(df,
                          demographics_filename=demographics_filename,
                          concerns=concerns,
                          res_in_arcsec=res_in_arcsec,
                          node_id_from_lat_long=node_id_from_lat_long,
                          default_population=default_population,
                          load_other_columns_as_attributes=load_other_columns_as_attributes,
                          include_columns=include_columns,
                          exclude_columns=exclude_columns,
                          nodeid_column_name=nodeid_column_name,
                          latitude_column_name=latitude_column_name,
                          longitude_column_name=longitude_column_name,
                          population_column_name=population_column_name)


"""
from_gridfile
    from_dataframe
        __init__
            set_resolution
        generate_demographics
            generate_nodes
            generate_metadata
"""
