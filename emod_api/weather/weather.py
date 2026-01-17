#!/usr/bin/env python3

"""
emod-api Weather module - Weather, Metadata, and WeatherNode objects along with IDREF and CLIMATE_UPDATE constants.
"""

from collections import namedtuple
from functools import reduce
import csv
from datetime import datetime
import getpass
import json
import numpy as np
from typing import Dict, List


IDREF_LEGACY = "Legacy"
IDREF_GRUMP30ARCSEC = "Gridded world grump30arcsec"
IDREF_GRUMP2PT5ARCMIN = "Gridded world grump2.5arcmin"
IDREF_GRUMP1DEGREE = "Gridded world grump1degree"

CLIMATE_UPDATE_YEAR = "CLIMATE_UPDATE_YEAR"
CLIMATE_UPDATE_MONTH = "CLIMATE_UPDATE_MONTH"
CLIMATE_UPDATE_WEEK = "CLIMATE_UPDATE_WEEK"
CLIMATE_UPDATE_DAY = "CLIMATE_UPDATE_DAY"
CLIMATE_UPDATE_HOUR = "CLIMATE_UPDATE_HOUR"


class WeatherNode(object):
    """Represents information for a single node: ID and timeseries data."""

    def __init__(self, node_id: int, data):

        self._id = node_id
        self._data = data

        return

    @property
    def id(self) -> int:
        """Node ID"""
        return self._id

    @property
    def data(self):
        """Time series data for this node."""
        return self._data

    # index into node by time step
    def __getitem__(self, item: int) -> float:
        return self._data[item]

    def __setitem__(self, key: int, value: float) -> None:
        self._data[key] = value
        return


def _is_iterable(obj) -> bool:
    try:
        _ = iter(obj)
        return True
    except TypeError:
        return False


def _isinteger(obj) -> bool:
    return obj and isinstance(obj, (int, np.integer))


class Metadata(object):

    """
    Metadata:

    * [DateCreated]
    * [Author]
    * [OriginalDataYears]
    * [StartDayOfYear]
    * [DataProvenance]
    * IdReference
    * NodeCount
    * DatavalueCount
    * UpdateResolution
    * NodeOffsets
    """

    def __init__(
        self,
        node_ids: List[int],
        datavalue_count: int,
        author: str = None,
        created: datetime = None,
        frequency: str = None,
        provenance: str = None,
        reference: str = None,
    ):

        assert int(datavalue_count) > 0, "datavalue_count must be > 0"
        self._data_count = int(datavalue_count)
        self._author = f"{author}" if author else getpass.getuser()
        self._creation = (
            created if created and isinstance(created, datetime) else datetime.now()
        )
        self._id_reference = f"{reference}" if reference else IDREF_LEGACY
        self._provenance = f"{provenance}" if provenance else "unknown"
        self._update_frequency = f"{frequency}" if frequency else CLIMATE_UPDATE_DAY

        assert _is_iterable(node_ids), "node_ids must be iterable"
        concrete = list(node_ids)  # if node_ids is a generator, make a concrete list
        assert len(concrete) > 0, "node_ids must not be empty"
        assert all(
            map(lambda i: isinstance(i, int), concrete)
        ), "node_ids must be integers"
        assert len(set(concrete)) == len(concrete), "node_ids must be unique"
        sorted_ids = sorted(concrete)
        self._nodes = {
            node_id: datavalue_count * sorted_ids.index(node_id) * 4
            for node_id in sorted_ids
        }

        return

    @property
    def author(self) -> str:
        """Author of this file."""
        return self._author

    @property
    def creation_date(self) -> datetime:
        """Creation date of this file."""
        return self._creation

    @property
    def datavalue_count(self) -> int:
        """Number of data values in each timeseries, should be > 0."""
        return self._data_count

    @property
    def id_reference(self) -> str:
        """
        'Schema' for node IDs. Commonly `Legacy`, `Gridded world grump2.5arcmin`, and `Gridded world grump30arcsec`.

        `Legacy` usually indicates a 0 or 1 based scheme with increasing ID numbers.

        `Gridded world grump2.5arcmin` and `Gridded world grump30arcsec` encode latitude and longitude values in the node ID with the following formula::

            latitude  = (((nodeid - 1) & 0xFFFF) * resolution) -  90
            longitude = ((nodeid >> 16)          * resolution) - 180
            # nodeid = 90967271 @ 2.5 arcmin resolution
            # longitude = -122.1667, latitude = 47.5833
        """
        return self._id_reference

    @property
    def node_count(self) -> int:
        return len(self.nodes)

    @property
    def node_ids(self) -> List[int]:
        return sorted(self.nodes.keys())

    @property
    def provenance(self) -> str:
        return self._provenance

    @property
    def update_resolution(self) -> str:
        return self._update_frequency

    @property
    def nodes(self) -> Dict[int, int]:
        """WeatherNodes offsets keyed by node id."""
        return self._nodes

    def write_file(self, filename: str) -> None:

        metadata = dict(
            DateCreated=f"{self.creation_date:%a %B %d %Y %H:%M:%S}",
            Author=self.author,
            DataProvenance=self.provenance,
            IdReference=self.id_reference,
            NodeCount=len(self.nodes),
            DatavalueCount=self.datavalue_count,
            UpdateResolution=self.update_resolution,
        )

        node_offsets = reduce(
            lambda s, n: s + f"{n:08X}{self.nodes[n]:08X}", self.node_ids, ""
        )

        jason = dict(Metadata=metadata, NodeOffsets=node_offsets)

        with open(filename, "wt") as file:
            json.dump(jason, file, indent=2, separators=(",", ": "))

        return

    @classmethod
    def from_file(cls, filename: str):
        """
        Read weather metadata file.
        Metadata' and 'NodeOffsets' keys required.
        DatavalueCount', 'UpdateResolution', and 'IdReference' required in 'Metadata'.
        """
        with open(filename, "rb") as file:
            jason = json.load(file)

        meta = jason["Metadata"]
        offsets = jason["NodeOffsets"]
        node_ids = sorted(
            [int(offsets[(i * 16):(i * 16 + 8)], 16) for i in range(len(offsets) // 16)]
        )

        metadata = Metadata(
            node_ids,
            meta["DatavalueCount"],
            author=meta["Author"] if "Author" in meta else None,
            created=meta["DateCreated"] if "DateCreated" in meta else None,
            frequency=meta["UpdateResolution"],
            provenance=meta["DataProvenance"] if "DataProvenance" in meta else None,
            reference=meta["IdReference"],
        )

        return metadata


class Weather(object):
    def __init__(
        self,
        filename: str = None,
        node_ids: List[int] = None,
        datavalue_count: int = None,
        author: str = None,
        created: datetime = None,
        frequency: str = None,
        provenance: str = None,
        reference: str = None,
        data: np.array = None,
    ):

        if filename and isinstance(filename, str):
            self._from_file(filename)
        else:
            # create "empty" Weather object
            assert _is_iterable(node_ids), "node_ids must be provided and be iterable"
            assert _isinteger(datavalue_count), "datavalue_count must be provided"
            assert datavalue_count > 0, "datavalue_count must be >= 1"

            self._metadata = Metadata(
                node_ids,
                datavalue_count,
                author,
                created,
                frequency,
                provenance,
                reference,
            )
            node_ids = self._metadata.node_ids
            self._data = (
                data
                if data is not None
                else np.zeros(
                    (len(node_ids), self._metadata.datavalue_count), dtype=np.float32
                )
            )
            self._nodes_and_map()

        return

    def _nodes_and_map(self):
        node_ids = self._metadata.node_ids
        self._node_id_to_index_map = {node_ids[n]: n for n in range(len(node_ids))}
        self._nodes = {
            node_id: WeatherNode(
                node_id, self._data[self._node_id_to_index_map[node_id], :]
            )
            for node_id in node_ids
        }
        return

    @property
    def data(self) -> np.array:
        """Raw data as numpy array[node index, time step]."""
        return self._data

    @property
    def metadata(self) -> Metadata:
        return self._metadata

    # begin pass-through

    @property
    def author(self) -> str:
        return self._metadata.author

    @property
    def creation_date(self) -> datetime:
        return self._metadata.creation_date

    @property
    def datavalue_count(self) -> int:
        """>= 1"""
        return self._metadata.datavalue_count

    @property
    def id_reference(self) -> str:
        return self._metadata.id_reference

    @property
    def node_count(self) -> int:
        """>= 1"""
        return self._metadata.node_count

    @property
    def node_ids(self) -> List[int]:
        return self._metadata.node_ids

    @property
    def provenance(self) -> str:
        return self._metadata.provenance

    @property
    def update_resolution(self) -> str:
        return self._metadata.update_resolution

    # end pass-through

    @property
    def nodes(self) -> Dict[int, WeatherNode]:
        """WeatherNodes indexed by node id."""
        return self._nodes

    # retrieve node by node id
    def __getitem__(self, item: int):
        return self._nodes[item]

    def write_file(self, filename: str) -> None:
        """Writes data to filename and metadata to filename.json."""
        self.metadata.write_file(filename + ".json")

        with open(filename, "wb") as file:
            self._data.tofile(file)

        return

    def _from_file(self, filename: str):
        """Reads metadata from filename.json and data from filename."""
        self._metadata = Metadata.from_file(filename + ".json")
        data = np.fromfile(filename, dtype=np.float32)
        expected = self._metadata.node_count * self._metadata.datavalue_count
        assert (
            len(data) == expected
        ), f"length of data ({len(data)}) != #nodes * #values ({expected})"
        self._data = data.reshape(
            self._metadata.node_count, self._metadata.datavalue_count
        )
        self._nodes_and_map()

        return

    @classmethod
    def from_csv(
        cls,
        filename: str,
        var_column: str = "airtemp",
        id_column: str = "node_id",
        step_column: str = "step",
        author: str = None,
        provenance: str = None,
    ):
        """
        Create weather from CSV file with specified variable column, node id column, and time step column.

        Note:
            * Column order in the CSV file is not significant, but columns names must match what is passed to this function.
            * Because a CSV might hold air temperature (may be negative and well outside 0-1 values), relative humidity (must _not_ be negative, must be in the interval [0-1]), or rainfall (must _not_ be negative, likely > 1), this function does not validate incoming data.
        """
        Entry = namedtuple("Entry", ["id", "step", "value"])

        with open(filename) as csv_file:
            reader = csv.DictReader(csv_file)
            entries = [
                Entry(
                    int(row[id_column]), int(row[step_column]), float(row[var_column])
                )
                for row in reader
            ]

        node_ids = set([entry.id for entry in entries])
        steps_list = [
            sorted([entry.step for entry in entries if entry.id == node_id])
            for node_id in sorted(node_ids)
        ]

        for i in range(1, len(steps_list)):
            test = len(steps_list[i])
            expected = len(steps_list[0])
            assert (
                test == expected
            ), f"number of data values for nodes is not consistent ({len(steps_list[i]) != {len(steps_list[0])}})"
            test = steps_list[i]
            expected = steps_list[0]
            assert (
                test == expected
            ), f"time steps for node {sorted(node_ids)[i]} != time steps for node {sorted(node_ids)[0]}"

        steps = sorted(steps_list[0])
        expected = [i for i in range(1, len(steps) + 1)]
        assert steps == expected, f"time steps do not cover all values 1...{len(steps)}"

        data_count = len(steps)

        w = Weather(
            node_ids=node_ids,
            datavalue_count=data_count,
            author=author,
            provenance=provenance,
        )
        for node_id in node_ids:

            sorted_entries_for_node = sorted(
                [entry for entry in entries if entry.id == node_id],
                key=lambda e: e.step,
            )
            data_for_node = [entry.value for entry in sorted_entries_for_node]

            w.nodes[node_id][:] = data_for_node

        return w
