from collections import defaultdict
from datetime import datetime
from functools import partial
import json
from numbers import Integral
from os import environ, SEEK_SET
from pathlib import Path
from platform import system
from warnings import warn

import numpy as np
import csv

from emod_api.demographics.demographics import Demographics

# for from_demog_and_param_gravity()
from geographiclib.geodesic import Geodesic


class Layer(dict):

    """
    The Layer object represents a mapping from source node (IDs) to destination node (IDs) for a particular
    age, gender, age+gender combination, or all users if no age or gender dependence. Users will not generally
    interact directly with Layer objects.
    """

    def __init__(self):

        super().__init__()

        return

    @property
    def DatavalueCount(self) -> int:
        """Get (maximum) number of data values for any node in this layer

        Returns:
            Maximum number of data values for any node in this layer

        """
        count = max([len(entry) for entry in self.values()]) if len(self) else 0
        return count

    @property
    def NodeCount(self) -> int:
        """Get the number of (source) nodes with rates in this layer

        Returns:
            Number of (source) nodes with rates in this layer

        """
        return len(self)

    # @property
    # def Nodes(self) -> dict:
    #     return self._nodes

    def __getitem__(self,
                    key: int) -> dict:
        """Allows indexing directly into this object with source node id

        Args:
            key: source node id

        Returns:
            Dictionary of outbound rates for the given node id
        """
        if key not in self:
            if isinstance(key, Integral):
                super().__setitem__(key, defaultdict(float))
            else:
                raise RuntimeError(f"Migration node IDs must be integer values (key = {key}).")
        return super().__getitem__(key)


_METADATA = "Metadata"
_AUTHOR = "Author"
_DATECREATED = "DateCreated"
_TOOLNAME = "Tool"
_IDREFERENCE = "IdReference"
_MIGRATIONTYPE = "MigrationType"
_NODECOUNT = "NodeCount"
_DATAVALUECOUNT = "DatavalueCount"
_GENDERDATATYPE = "GenderDataType"
_AGESYEARS = "AgesYears"
_INTERPOLATIONTYPE = "InterpolationType"
_NODEOFFSETS = "NodeOffsets"
_EMODAPI = "emod-api"


class Migration(object):

    """Represents migration data in a mapping from source node (IDs) to destination node (IDs) with rates for each pairing.

    Migration data may be age dependent, gender dependent, both, or the same for all ages and genders.
    A migration file (along with JSON metadata) can be loaded from the static method Migration.from_file() and
    inspected and/or modified.
    Migration objects can be started from scratch with Migration(), and populated with appropriate source-dest rate data
    and saved to a file with the to_file() method.
    Given migration = Migration(), syntax is as follows:

    age and gender agnostic:  `migration[source_id][dest_id]`
    age dependent:            `migration[source_id:age]`          # age should be >= 0, ages > last bucket value use last bucket value
    gender dependent:         `migration[source_id:gender]`       # gender one of Migration.MALE or Migration.FEMALE
    age and gender dependent: `migration[source_id:gender:age]`   # gender one of Migration.MALE or Migration.FEMALE

    EMOD/DTK format migration files (and associated metadata files) can be written with migration.to_file(<filename>).
    EMOD/DTK format migration files (with associated metadata files) can be read with migration.from_file(<filename>).
    """

    SAME_FOR_BOTH_GENDERS = 0
    ONE_FOR_EACH_GENDER = 1

    LINEAR_INTERPOLATION = 0
    PIECEWISE_CONSTANT = 1

    LOCAL = 1
    AIR = 2
    REGIONAL = 3
    SEA = 4
    FAMILY = 5
    INTERVENTION = 6

    IDREF_LEGACY = "Legacy"
    IDREF_GRUMP30ARCSEC = "Gridded world grump30arcsec"
    IDREF_GRUMP2PT5ARCMIN = "Gridded world grump2.5arcmin"
    IDREF_GRUMP1DEGREE = "Gridded world grump1degree"

    MALE = 0
    FEMALE = 1

    MAX_AGE = 125

    def __init__(self):

        self._agesyears = []
        try:
            self._author = _author()
        except Exception:
            self._author = "Mystery Guest"
        self._datecreated = datetime.now()
        self._genderdatatype = self.SAME_FOR_BOTH_GENDERS
        self._idreference = self.IDREF_LEGACY
        self._interpolationtype = self.PIECEWISE_CONSTANT
        self._migrationtype = self.LOCAL
        self._tool = _EMODAPI

        self._create_layers()

        return

    def _create_layers(self):

        self._layers = []
        for gender in range(0, self._genderdatatype + 1):
            for age in range(0, len(self.AgesYears) if self.AgesYears else 1):
                self._layers.append(Layer())

        return

    @property
    def AgesYears(self) -> list:
        """
        List of ages - ages < first value use first bucket, ages > last value use last bucket.
        """
        return self._agesyears

    @AgesYears.setter
    def AgesYears(self, ages: list) -> None:
        """
        List of ages - ages < first value use first bucket, ages > last value use last bucket.
        """
        if sorted(ages) != self.AgesYears:
            if self.NodeCount > 0:
                warn("Changing age buckets clears existing migration information.", category=UserWarning)
            self._agesyears = sorted(ages)
            self._create_layers()
        return

    @property
    def Author(self) -> str:
        """str: Author value for metadata for this migration datafile"""
        return self._author

    @Author.setter
    def Author(self, author: str) -> None:
        self._author = author
        return

    @property
    def DatavalueCount(self) -> int:
        """int: Maximum data value count for any layer in this migration datafile"""
        count = max([layer.DatavalueCount for layer in self._layers])
        return count

    @property
    def DateCreated(self) -> datetime:
        """datetime: date/time stamp of this datafile"""
        return self._datecreated

    @DateCreated.setter
    def DateCreated(self, value) -> None:
        if not isinstance(value, datetime):
            raise RuntimeError(f"DateCreated must be a datetime value (got {type(value)}).")
        self._datecreated = value
        return

    @property
    def GenderDataType(self) -> int:
        """int: gender data type for this datafile - SAME_FOR_BOTH_GENDERS or ONE_FOR_EACH_GENDER"""
        return self._genderdatatype

    @GenderDataType.setter
    def GenderDataType(self, value: int) -> None:

        # integer value
        if value in Migration._GENDER_DATATYPE_ENUMS.keys():
            value = int(value)
        # string value
        elif value in Migration._GENDER_DATATYPE_LOOKUP.keys():
            value = Migration._GENDER_DATATYPE_LOOKUP[value]
        else:
            expected = [f"{key}/{value}" for key, value in Migration._GENDER_DATATYPE_LOOKUP.items()]
            raise RuntimeError(f"Unknown gender data type, {value}, expected one of {expected}.")

        if (self.NodeCount > 0) and (value != self._genderdatatype):
            warn("Changing gender data type clears existing migration information.", category=UserWarning)

        if value != self._genderdatatype:
            self._genderdatatype = int(value)
            self._create_layers()
        return

    @property
    def IdReference(self) -> str:
        """str: ID reference metadata value"""
        return self._idreference

    @IdReference.setter
    def IdReference(self, value: str) -> None:
        self._idreference = str(value)
        return

    @property
    def InterpolationType(self) -> int:
        """int: interpolation type for this migration data file - LINEAR_INTERPOLATION or PIECEWISE_CONSTANT"""
        return self._interpolationtype

    @InterpolationType.setter
    def InterpolationType(self, value: int) -> None:

        # integer value
        if value in Migration._INTERPOLATION_TYPE_ENUMS.keys():
            self._interpolationtype = int(value)
        # string value
        elif value in Migration._INTERPOLATION_TYPE_LOOKUP.keys():
            self._interpolationtype = Migration._INTERPOLATION_TYPE_LOOKUP[value]
        else:
            expected = [f"{key}/{value}" for key, value in Migration._INTERPOLATION_TYPE_LOOKUP.items()]
            raise RuntimeError(f"Unknown interpolation type, {value}, expected one of {expected}.")
        return

    @property
    def MigrationType(self) -> int:
        """int: migration type for this migration data file - LOCAL | AIR | REGIONAL | SEA | FAMILY | INTERVENTION"""
        return self._migrationtype

    @MigrationType.setter
    def MigrationType(self, value: int) -> None:

        # integer value
        if value in Migration._MIGRATION_TYPE_ENUMS.keys():
            self._migrationtype = int(value)
        elif value in Migration._MIGRATION_TYPE_LOOKUP.keys():
            self._migrationtype = Migration._MIGRATION_TYPE_LOOKUP[value]
        else:
            expected = [f"{key}/{value}" for key, value in Migration._MIGRATION_TYPE_LOOKUP.items()]
            raise RuntimeError(f"Unknown migration type, {value}, expected one of {expected}.")
        return

    @property
    def Nodes(self) -> list:
        node_ids = set()
        for layer in self._layers:
            node_ids |= set(layer.keys())
        node_ids = sorted(node_ids)
        return node_ids

    @property
    def NodeCount(self) -> int:
        """int: maximum number of source nodes in any layer of this migration data file"""
        count = max([layer.NodeCount for layer in self._layers])
        return count

    def get_node_offsets(self, limit: int = 100) -> dict:
        nodes = set()
        for layer in self._layers:
            nodes |= set(key for key in layer.keys())
        count = min(self.DatavalueCount, limit)
        # offsets = {}
        # for index, node in enumerate(sorted(nodes)):
        #     offsets[node] = index * 12 * count
        offsets = {node: 12 * index * count for index, node in enumerate(sorted(nodes))}
        return offsets

    @property
    def NodeOffsets(self) -> dict:
        """dict: mapping from source node id to offset to destination and rate data in binary data"""
        return self.get_node_offsets()

    @property
    def Tool(self) -> str:
        """str: tool metadata value"""
        return self._tool

    @Tool.setter
    def Tool(self, value: str) -> None:
        self._tool = str(value)
        return

    def __getitem__(self, key):
        """allows indexing on this object to read/write rate data
        Args:
            key (slice): source node id:gender:age (gender and age depend on GenderDataType and AgesYears properties)
        Returns:
            dict for specified node/gender/age
        """
        if self.GenderDataType == Migration.SAME_FOR_BOTH_GENDERS:
            if not self.AgesYears:
                # Case 1 - no gender or age differentiation - key (integer) == node id
                return self._layers[0][key]
            else:
                # Case 3 - age buckets, no gender differentiation - key (tuple or slice) == node id:age
                if isinstance(key, tuple):
                    node_id, age = key
                elif isinstance(key, slice):
                    node_id, age = key.start, key.stop
                else:
                    raise RuntimeError(f"Invalid indexing for migration - {key}")
                layer_index = self._index_for_gender_and_age(None, age)
                return self._layers[layer_index][node_id]
        else:
            if not self.AgesYears:
                # Case 2 - by gender, no age differentiation - key (tuple or slice) == node id:gender
                if isinstance(key, tuple):
                    node_id, gender = key
                elif isinstance(key, slice):
                    node_id, gender = key.start, key.stop
                else:
                    raise RuntimeError(f"Invalid indexing for migration - {key}")
                if gender not in [Migration.SAME_FOR_BOTH_GENDERS, Migration.ONE_FOR_EACH_GENDER]:
                    raise RuntimeError(f"Invalid gender ({gender}) for migration.")
                layer_index = self._index_for_gender_and_age(gender, None)
                return self._layers[layer_index][node_id]
            else:
                # Case 4 - by gender and age - key (slice) == node id:gender:age
                if isinstance(key, tuple):
                    node_id, gender, age = key
                elif isinstance(key, slice):
                    node_id, gender, age = key.start, key.stop, key.step
                else:
                    raise RuntimeError(f"Invalid indexing for migration - {key}")
                if gender not in [Migration.SAME_FOR_BOTH_GENDERS, Migration.ONE_FOR_EACH_GENDER]:
                    raise RuntimeError(f"Invalid gender ({gender}) for migration.")
                layer_index = self._index_for_gender_and_age(gender, age)
                return self._layers[layer_index][node_id]

        # raise RuntimeError("Invalid state.")

    def _index_for_gender_and_age(self, gender: int, age: float) -> int:
        """
        Use age to determine age bucket, 0 if no age differentiation.
        Use gender data type to offset by # age buckets if gender data type is one for each gender and gender is female
        Ages < first value use first bucket, ages > last value use last bucket.
        """
        age_offset = 0
        for age_offset, edge in enumerate(self.AgesYears):
            if edge >= age:
                break
        gender_span = len(self.AgesYears) if self.AgesYears else 1
        gender_offset = gender * gender_span if self.GenderDataType == Migration.ONE_FOR_EACH_GENDER else 0
        index = gender_offset + age_offset
        return index

    def __iter__(self):
        return iter(self._layers)

    _MIGRATION_TYPE_ENUMS = {
        LOCAL: "LOCAL_MIGRATION",
        AIR: "AIR_MIGRATION",
        REGIONAL: "REGIONAL_MIGRATION",
        SEA: "SEA_MIGRATION",
        FAMILY: "FAMILY_MIGRATION",
        INTERVENTION: "INTERVENTION_MIGRATION"
    }

    _GENDER_DATATYPE_ENUMS = {
        SAME_FOR_BOTH_GENDERS: "SAME_FOR_BOTH_GENDERS",
        ONE_FOR_EACH_GENDER: "ONE_FOR_EACH_GENDER"
    }

    _INTERPOLATION_TYPE_ENUMS = {
        LINEAR_INTERPOLATION: "LINEAR_INTERPOLATION",
        PIECEWISE_CONSTANT: "PIECEWISE_CONSTANT"
    }

    def to_file(self, binaryfile: Path, metafile: Path = None, value_limit: int = 100):
        """Write current data to given file (and .json metadata file)

        Args:
            binaryfile (Path): path to output file (metadata will be written to same path with ".json" appended)
            metafile (Path): override standard metadata file naming
            value_limit (int): limit on number of destination values to write for each source node (default = 100)

        Returns:
            (Path): path to binary file
        """
        binaryfile = Path(binaryfile).absolute()
        metafile = metafile if metafile else binaryfile.parent / (binaryfile.name + ".json")

        actual_datavalue_count = min(self.DatavalueCount, value_limit)  # limited to 100 destinations

        node_ids = set()
        for layer in self._layers:
            node_ids |= set(layer.keys())
        node_ids = sorted(node_ids)

        offsets = self.get_node_offsets(actual_datavalue_count)
        node_offsets_string = ''.join([f"{node:08x}{offsets[node]:08x}" for node in sorted(offsets.keys())])

        metadata = {
            _METADATA: {
                _AUTHOR: self.Author,
                _DATECREATED: f"{self.DateCreated:%a %b %d %Y %H:%M:%S}",
                _TOOLNAME: self.Tool,
                _IDREFERENCE: self.IdReference,
                _MIGRATIONTYPE: self._MIGRATION_TYPE_ENUMS[self.MigrationType],
                _NODECOUNT: self.NodeCount,
                _DATAVALUECOUNT: actual_datavalue_count,
                # could omit this if SAME_FOR_BOTH_GENDERS since it is the default
                _GENDERDATATYPE: self._GENDER_DATATYPE_ENUMS[self.GenderDataType],
                # _AGESYEARS: self.AgesYears,    # see below
                _INTERPOLATIONTYPE: self._INTERPOLATION_TYPE_ENUMS[self.InterpolationType]
            },
            _NODEOFFSETS: node_offsets_string
        }
        if self.AgesYears:
            # older versions of Eradication do not handle empty AgesYears lists robustly
            metadata[_METADATA][_AGESYEARS] = self.AgesYears

        print(f"Writing metadata to '{metafile}'")
        with metafile.open("w") as handle:
            json.dump(metadata, handle, indent=4, separators=(",", ": "))

        def key_func(k, d=None):
            return d[k]

        # layers are in age bucket order by gender, e.g. male 0-5, 5-10, 10+, female 0-5, 5-10, 10+
        # see _index_for_gender_and_age()
        print(f"Writing binary data to '{binaryfile}'")
        with binaryfile.open("wb") as file:
            for layer in self:
                for node in node_ids:
                    destinations = np.zeros(actual_datavalue_count, dtype=np.uint32)
                    rates = np.zeros(actual_datavalue_count, dtype=np.float64)
                    if node in layer:

                        # Sort keys descending on rate and ascending on node ID.
                        # That way if we are truncating the list, we include the "most important" nodes.
                        keys = sorted(layer[node].keys())   # sorted ascending on node ID
                        keys = sorted(keys, key=partial(key_func, d=layer[node]), reverse=True)  # descending on rate

                        if len(keys) > actual_datavalue_count:
                            keys = keys[0:actual_datavalue_count]
                        # save rates in ascending order so small rates are not lost when looking at the cumulative sum
                        keys = list(reversed(keys))
                        destinations[0:len(keys)] = keys
                        rates[0:len(keys)] = [layer[node][key] for key in keys]
                    else:
                        warn(f"No destination nodes found for node {node}", category=UserWarning)
                    destinations.tofile(file)
                    rates.tofile(file)

        return binaryfile

    _MIGRATION_TYPE_LOOKUP = {
        "LOCAL_MIGRATION": LOCAL,
        "AIR_MIGRATION": AIR,
        "REGIONAL_MIGRATION": REGIONAL,
        "SEA_MIGRATION": SEA,
        "FAMILY_MIGRATION": FAMILY,
        "INTERVENTION_MIGRATION": INTERVENTION
    }

    _GENDER_DATATYPE_LOOKUP = {
        "SAME_FOR_BOTH_GENDERS": SAME_FOR_BOTH_GENDERS,
        "ONE_FOR_EACH_GENDER": ONE_FOR_EACH_GENDER
    }

    _INTERPOLATION_TYPE_LOOKUP = {
        "LINEAR_INTERPOLATION": LINEAR_INTERPOLATION,
        "PIECEWISE_CONSTANT": PIECEWISE_CONSTANT
    }


def from_file(binaryfile: Path,
              metafile: Path = None) -> Migration:
    """Reads migration data file from given binary (and associated JSON metadata file)

    Args:
        binaryfile (Path): path to binary file (metadata file is assumed to be at same location with ".json" suffix)
        metafile (Path): use given metafile rather than inferring metafile name from the binary file name

    Returns:
        Migration object representing binary data in the given file.
    """
    binaryfile = Path(binaryfile).absolute()
    metafile = metafile if metafile else binaryfile.parent / (binaryfile.name + ".json")

    if not binaryfile.exists():
        raise RuntimeError(f"Cannot find migration binary file '{binaryfile}'")
    if not metafile.exists():
        raise RuntimeError(f"Cannot find migration metadata file '{metafile}'.")
    with metafile.open("r") as file:
        jason = json.load(file)

    # these are the minimum required entries to load a migration file
    assert _METADATA in jason, f"Metadata file '{metafile}' does not have a 'Metadata' entry."
    metadata = jason[_METADATA]
    assert _NODECOUNT in metadata, f"Metadata file '{metafile}' does not have a 'NodeCount' entry."
    assert _DATAVALUECOUNT in metadata, f"Metadata file '{metafile}' does not have a 'DatavalueCount' entry."
    assert _NODEOFFSETS in jason, f"Metadata file '{metafile}' does not have a 'NodeOffsets' entry."

    migration = Migration()
    migration.Author = _value_with_default(metadata, _AUTHOR, _author())
    migration.DateCreated = _try_parse_date(metadata[_DATECREATED]) if _DATECREATED in metadata else datetime.now()
    migration.Tool = _value_with_default(metadata, _TOOLNAME, _EMODAPI)
    migration.IdReference = _value_with_default(metadata, _IDREFERENCE, Migration.IDREF_LEGACY)
    migration.MigrationType = Migration._MIGRATION_TYPE_LOOKUP[_value_with_default(metadata,
                                                                                   _MIGRATIONTYPE,
                                                                                   "LOCAL_MIGRATION")]
    migration.GenderDataType = Migration._GENDER_DATATYPE_LOOKUP[_value_with_default(metadata,
                                                                                     _GENDERDATATYPE,
                                                                                     "SAME_FOR_BOTH_GENDERS")]
    migration.AgesYears = _value_with_default(metadata, _AGESYEARS, [])
    migration.InterpolationType = Migration._INTERPOLATION_TYPE_LOOKUP[_value_with_default(metadata,
                                                                                           _INTERPOLATIONTYPE,
                                                                                           "PIECEWISE_CONSTANT")]

    node_count = metadata[_NODECOUNT]
    node_offsets = jason[_NODEOFFSETS]
    if len(node_offsets) != 16 * node_count:
        raise RuntimeError(f"Length of node offsets string {len(node_offsets)} != 16 * node count {node_count}.")
    offsets = _parse_node_offsets(node_offsets, node_count)
    datavalue_count = metadata[_DATAVALUECOUNT]
    with binaryfile.open("rb") as file:
        for gender in range(1 if migration.GenderDataType == Migration.SAME_FOR_BOTH_GENDERS else 2):
            for age in migration.AgesYears if migration.AgesYears else [0]:
                layer = migration._layers[migration._index_for_gender_and_age(gender, age)]
                for node, offset in offsets.items():
                    file.seek(offset, SEEK_SET)
                    destinations = np.fromfile(file, dtype=np.uint32, count=datavalue_count)
                    rates = np.fromfile(file, dtype=np.float64, count=datavalue_count)
                    for destination, rate in zip(destinations, rates):
                        if rate > 0:
                            layer[node][destination] = rate

    return migration


def examine_file(filename):

    def name_for_gender_datatype(e: int) -> str:
        return Migration._GENDER_DATATYPE_ENUMS[e] if e in Migration._GENDER_DATATYPE_ENUMS else "unknown"

    def name_for_interpolation(e: int) -> str:
        return Migration._INTERPOLATION_TYPE_ENUMS[e] if e in Migration._INTERPOLATION_TYPE_ENUMS else "unknown"

    def name_for_migration_type(e: int) -> str:
        return Migration._MIGRATION_TYPE_ENUMS[e] if e in Migration._MIGRATION_TYPE_ENUMS else "unknown"

    migration = from_file(filename)
    print(f"Author:            {migration.Author}")
    print(f"DatavalueCount:    {migration.DatavalueCount}")
    print(f"DateCreated:       {migration.DateCreated:%a %B %d %Y %H:%M}")
    print(f"GenderDataType:    {migration.GenderDataType} ({name_for_gender_datatype(migration.GenderDataType)})")
    print(f"IdReference:       {migration.IdReference}")
    print(f"InterpolationType: {migration.InterpolationType} ({name_for_interpolation(migration.InterpolationType)})")
    print(f"MigrationType:     {migration.MigrationType} ({name_for_migration_type(migration.MigrationType)})")
    print(f"NodeCount:         {migration.NodeCount}")
    print(f"NodeOffsets:       {migration.NodeOffsets}")
    print(f"Tool:              {migration.Tool}")
    print(f"Nodes:             {migration.Nodes}")

    return


def _author() -> str:
    username = "Unknown"
    if system() == "Windows":
        username = environ["USERNAME"]
    elif "USER" in environ:
        username = environ["USER"]
    return username


def _parse_node_offsets(string: str, count: int) -> dict:

    assert len(string) == 16 * count, f"Length of node offsets string {len(string)} != 16 * node count {count}."

    offsets = {}
    for index in range(count):
        base = 16 * index
        offset = base + 8
        offsets[int(string[base:base + 8], 16)] = int(string[offset:offset + 8], 16)

    return offsets


def _try_parse_date(string: str) -> datetime:

    patterns = [
        "%a %b %d %Y %H:%M:%S",
        "%a %b %d %H:%M:%S %Y",
        "%m/%d/%Y",
        "%Y-%m-%d %H:%M:%S.%f"
    ]

    for pattern in patterns:
        try:
            timestamp = datetime.strptime(string, pattern)
            return timestamp
        except ValueError:
            pass

    timestamp = datetime.now()
    warn(f"Could not parse date stamp '{string}', using datetime.now() ({timestamp})")

    return timestamp


def _value_with_default(dictionary: dict, key: str, default: object) -> object:
    return dictionary[key] if key in dictionary else default


"""
utility functions emodpy-utils?
"""


def from_demog_and_param_gravity(demographics_file_path, gravity_params, id_ref, migration_type=Migration.LOCAL):
    demog = Demographics.from_file(demographics_file_path)
    return _from_demog_and_param_gravity(demog, gravity_params, id_ref, migration_type)


def _from_demog_and_param_gravity(demographics, gravity_params, id_ref, migration_type=Migration.LOCAL):
    """
    Create migration files from a gravity model and an input demographics file.
    """

    def _compute_migr_prob(grav_params, home_pop, dest_pop, dist):
        """
        Utility function for computing migration probabilities for gravity model.
        """

        # If home/dest node has 0 pop, assume this node is the regional work node-- no local migration allowed
        if home_pop == 0 or dest_pop == 0:
            return 0.
        else:
            num_trips = grav_params[0] * home_pop ** grav_params[1] * dest_pop ** grav_params[2] * dist ** grav_params[3]
            prob_trip = np.min([1., num_trips / home_pop])
            return prob_trip

    def _compute_migr_dict(node_list, grav_params, **kwargs):
        """
        Utility function for computing migration value map.
        """

        excluded_nodes = set(kwargs["exclude_nodes"]) if "exclude_nodes" in kwargs else set()

        mig = Migration()
        geodesic = Geodesic.WGS84

        for source_node in node_list:

            source_id = source_node["NodeID"]
            src_lat = source_node["NodeAttributes"]["Latitude"]
            src_long = source_node["NodeAttributes"]["Longitude"]
            src_pop = source_node["NodeAttributes"]["InitialPopulation"]

            if source_id in excluded_nodes:
                continue

            for destination_node in node_list:

                if destination_node == source_node:
                    continue

                dest_id = destination_node["NodeID"]

                if dest_id in excluded_nodes:
                    continue

                dst_lat = destination_node["NodeAttributes"]["Latitude"]
                dst_long = destination_node["NodeAttributes"]["Longitude"]
                dst_pop = destination_node["NodeAttributes"]["InitialPopulation"]

                distance = geodesic.Inverse(src_lat, src_long, dst_lat, dst_long, Geodesic.DISTANCE)['s12'] / 1000  # km
                probability = _compute_migr_prob(grav_params, src_pop, dst_pop, distance)

                mig[source_id][dest_id] = probability

        return mig

    # load
    nodes = [node.to_dict() for node in demographics.nodes]
    migration = _compute_migr_dict(nodes, gravity_params)
    migration.IdReference = id_ref
    migration.MigrationType = migration_type

    return migration


# by gender, by age
_mapping_fns = {
    (False, False): lambda m, i, g, a: m[i],
    (False, True): lambda m, i, g, a: m[i:a],
    (True, False): lambda m, i, g, a: m[i:g],
    (True, True): lambda m, i, g, a: m[i:g:a]
}

# by gender, by age
_display_fns = {
    (False, False): lambda i, g, a, d, r: f"{i},{d},{r}",       # id only
    (False, True): lambda i, g, a, d, r: f"{i},{a},{d},{r}",    # id:age
    (True, False): lambda i, g, a, d, r: f"{i},{g},{d},{r}",    # id:gender
    (True, True): lambda i, g, a, d, r: f"{i},{g},{a},{d},{r}"  # id:gender:age
}


def to_csv(filename: Path):

    migration = from_file(filename)

    mapping = _mapping_fns[(migration.GenderDataType == Migration.ONE_FOR_EACH_GENDER, bool(migration.AgesYears))]
    display = _display_fns[(migration.GenderDataType == Migration.ONE_FOR_EACH_GENDER, bool(migration.AgesYears))]

    print(display("node", "gender", "age", "destination", "rate"))
    for gender in range(1 if migration.GenderDataType == Migration.SAME_FOR_BOTH_GENDERS else 2):
        for age in migration.AgesYears if migration.AgesYears else [0]:
            for node in migration.Nodes:
                for destination, rate in mapping(migration, node, gender, age).items():
                    print(display(node, gender, age, destination, rate))


def from_csv(filename: Path,
             id_ref,
             mig_type=None) -> Migration:
    """Create migration from csv file. The file should have columns 'source' for the source node, 'destination' for the destination node, and 'rate' for the migration rate.

    Args:
        filename: csv file

    Returns:
        Migration object
    """
    migration = Migration()
    migration.IdReference = id_ref
    if not mig_type:
        mig_type = Migration.LOCAL
    else:
        migration._migrationtype = mig_type
    with filename.open("r") as csvfile:
        reader = csv.DictReader(csvfile)
        csv_data_read = False
        for row in reader:
            csv_data_read = True
            migration[int(row['source'])][int(row['destination'])] = float(row['rate'])
        assert csv_data_read, "Csv file %s does not contain migration data." % filename

    return migration
