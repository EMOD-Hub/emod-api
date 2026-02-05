#!/usr/bin/env python3

"""emod-api spatial report module. Exposes SpatialReport and SpatialNode objects."""

from pathlib import Path
import numpy as np


class SpatialNode(object):

    """
    Class representing a single node of a spatial report.
    """

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

    def __getitem__(self, item: int) -> float:
        """index into node data by time step"""
        return self._data[item]

    def __setitem__(self, key: int, value: float) -> None:
        """index into node data by time step"""
        self._data[key] = value
        return


NUM_STEPS_INDEX = 0
NUM_NODES_INDEX = 1


class SpatialReport(object):

    """
    Class for reading (and, optionally, writing) spatial reports in EMOD/DTK format.
    "Filtered" reports will have start > 0 and/or reporting interval > 1.
    """

    def __init__(self, filename: str = None, node_ids: list[int] = None, data: np.array = None, start: int = 0, interval: int = 1):

        """
        Args:
            filename: file from which to read data
            node_ids: list of node ids, must be integer values
            data: NumPy array of data, shape must be (#values, #nodes)
            start: time step of first sample (used with filtered reports)
            interval: # of time steps between samples (used with filtered reports)
        """

        if isinstance(filename, str):
            self._from_file(filename)
        else:
            self._from_node_ids_and_data(node_ids, data, start, interval)

        return

    @property
    def data(self) -> np.array:
        """Returns full 2 dimensional NumPy array with report data. Shape is (#values, #nodes)."""
        return self._data

    @property
    def node_ids(self) -> list[int]:
        """Returns list of node IDs (integers) for nodes in the report."""
        return self._node_ids

    @property
    def nodes(self) -> dict[int, SpatialNode]:
        """Returns dictionary of SpatialNodes keyed on node ID."""
        return self._nodes

    # index into report by node id
    def __getitem__(self, item: int) -> SpatialNode:
        return self._nodes[item]

    @property
    def node_count(self) -> int:
        """Number of nodes in the report."""
        return self.data.shape[NUM_NODES_INDEX]

    @property
    def time_steps(self) -> int:
        """Number of samples in the report."""
        return self.data.shape[NUM_STEPS_INDEX]

    @property
    def start(self) -> int:
        """Time step of first sample."""
        return self._start

    @property
    def interval(self) -> int:
        """Interval, in time steps, between samples."""
        return self._interval

    def write_file(self, filename: str):

        """Save current nodes and timeseries data to given file."""

        with open(filename, "wb") as file:
            np.array([self.node_count], dtype=np.uint32).tofile(file)
            np.array([self.time_steps], dtype=np.uint32).tofile(file)
            if self.start != 0 or self.interval != 1:
                np.array([self.start], dtype=np.float32).tofile(file)
                np.array([self.interval], dtype=np.float32).tofile(file)
            np.array([self.node_ids], dtype=np.uint32).tofile(file)
            self.data.tofile(file)

        return

    def _from_file(self, filename: str):
        """
        Read binary spatial report file.
        #nodes,
        #time steps,
        node ids (#nodes values),
        data (#nodes x #time steps values)
        """
        # File format:
        # number of nodes      - uint32 * 1
        # number of time steps - uint32 * 1
        # OPTIONAL:
        #     starting time step - float32 * 1 (integral value in reality)
        #     time step interval - float32 * 1 (integral value in reality)
        # node ids             - uint32 * number of nodes
        # data                 - (float32 * number of nodes) * number of time_steps

        file_size = Path(filename).stat().st_size

        with open(filename, "rb") as file:
            num_nodes = np.fromfile(file, dtype=np.uint32, count=1)[0]
            num_time_steps = np.fromfile(file, dtype=np.uint32, count=1)[0]

            simple_size = (2 + num_nodes + (num_nodes * num_time_steps)) * 4    # num_nodes, num_time_steps, node_ids, and data
            filtered_size = simple_size + 8     # include starting time step and time step interval

            if file_size == simple_size:
                self._start = 0
                self._interval = 1
            elif file_size == filtered_size:
                self._start = int(np.fromfile(file, dtype=np.float32, count=1)[0])
                self._interval = int(np.fromfile(file, dtype=np.float32, count=1)[0])
                assert self.start >= 0
                assert self.interval >= 1
            else:
                raise RuntimeError(f"Unexpected file size {file_size}, expected {simple_size} (standard spatial report) or {filtered_size} (filtered spatial report).")

            node_ids = np.fromfile(file, dtype=np.uint32, count=num_nodes)
            data = np.fromfile(file, dtype=np.float32, count=num_nodes * num_time_steps)

        # let us index data[step, node]
        data = data.reshape((num_time_steps, num_nodes))
        self._from_node_ids_and_data(node_ids, data, self._start, self._interval)

        return

    def _from_node_ids_and_data(self, node_ids: list, data: np.array, start: int, interval: int) -> None:

        assert _is_iterable(node_ids), "node_ids must be specified and iterable"
        concrete = list(node_ids)
        assert len(concrete) > 0, "node_ids must not be empty"
        assert all(map(lambda i: _isinteger(i), concrete)), "node_ids must be integers"
        assert len(set(concrete)) == len(concrete), "node_ids must be unique"
        self._node_ids = sorted(concrete)
        assert data.dtype is np.dtype("float32"), "data must be np.float32"
        assert data.shape[1] == len(
            self._node_ids
        ), "data shape must be (#values, #nodes)"
        self._data = data

        self._node_id_to_index_map = {
            node_ids[n]: n for n in range(data.shape[NUM_NODES_INDEX])
        }
        self._nodes = {
            node_id: SpatialNode(node_id, data[:, self._node_id_to_index_map[node_id]])
            for node_id in node_ids
        }

        assert int(start) >= 0, "start sample time must be >= 0"
        self._start = int(start)
        assert int(interval) >= 1, "sample interval must be >= 1"
        self._interval = int(interval)

        return


def _is_iterable(obj) -> bool:
    try:
        _ = iter(obj)
        return True
    except TypeError:
        return False


def _isinteger(item) -> bool:
    return isinstance(item, (int, np.integer))
