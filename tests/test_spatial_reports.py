import unittest
import numpy as np
import os
import pathlib
import tempfile
from emod_api.spatialreports.spatial import SpatialReport, SpatialNode

from tests import manifest


class TestSpatialNode(unittest.TestCase):
    def test_ctor(self):

        _NODE_ID = 42
        _DATA = [1, 1, 2, 3, 5, 8]
        node = SpatialNode(_NODE_ID, _DATA)

        self.assertEqual(node.id, _NODE_ID)
        self.assertListEqual(node.data, _DATA)

        for i in range(len(_DATA)):
            self.assertEqual(node[i], _DATA[i])

        return


class TestSpatial(unittest.TestCase):
    def test_ctor(self):

        _NUM_TIME_STEPS = 365
        _NUM_NODES = 8
        ids = [i for i in range(1, _NUM_NODES + 1)]
        data = np.zeros((_NUM_TIME_STEPS, _NUM_NODES), dtype=np.float32)
        for step in range(_NUM_TIME_STEPS):
            for node in range(0, _NUM_NODES):
                data[step, node] = ((node + 1) << 16) + step
        report = SpatialReport(node_ids=ids, data=data)

        self.assertEqual(report.data[0, 0], 0x10000)
        self.assertEqual(report.data[1, 0], 0x10001)
        self.assertEqual(report.data[0, 1], 0x20000)
        self.assertEqual(report.data[1, 1], 0x20001)
        self.assertEqual(report.data[0, 7], 0x80000)
        self.assertEqual(report.data[9, 7], 0x80009)

        self.assertEqual(len(report.node_ids), _NUM_NODES)
        self.assertEqual(sorted(report.node_ids), ids)

        self.assertEqual(report.nodes[1].id, 1)
        self.assertEqual(report.nodes[8].id, 8)

        self.assertEqual(report[4].id, 4)
        self.assertEqual(report[4][180], 0x400B4)

        self.assertEqual(report.node_count, _NUM_NODES)
        self.assertEqual(report.time_steps, _NUM_TIME_STEPS)

    def test_nodeIdsNotIterable(self):

        self.assertRaises(
            AssertionError, SpatialReport, None, np.zeros((365, 4), np.float32)
        )

        return

    def test_nodeIdsEmpty(self):

        self.assertRaises(
            AssertionError, SpatialReport, [], np.zeros((365, 4), np.float32)
        )

        return

    def test_nodeIdsNotIntegers(self):

        self.assertRaises(
            AssertionError, SpatialReport, [1, "two", 3], np.zeros((365, 3), np.float32)
        )

        return

    def test_nodeIdsNotUnique(self):

        self.assertRaises(
            AssertionError,
            SpatialReport,
            [1, 2, 3, 2, 1],
            np.zeros((365, 3), np.float32),
        )

        return

    def test_dataIsNotFloat32(self):

        self.assertRaises(
            AssertionError, SpatialReport, [1, 2, 3], np.zeros((365, 3), np.float64)
        )

        return

    def test_dataIsWrongShape(self):

        self.assertRaises(
            AssertionError, SpatialReport, [1, 2, 3], np.zeros((365, 5), np.float32)
        )

        return

    def test_fromFile(self):

        report = SpatialReport(os.path.join(manifest.spatrep_folder, "SpatialReport_Prevalence.bin"))

        NUM_TIME_STEPS = 730
        NUM_NODES = 1423
        START_STEP = 0
        SAMPLE_INTERVAL = 1

        self.assertEqual(report.data.shape, (NUM_TIME_STEPS, NUM_NODES))
        self.assertEqual(len(report.node_ids), NUM_NODES)
        self.assertEqual(len(report.nodes), NUM_NODES)
        self.assertEqual(report.node_count, NUM_NODES)
        self.assertEqual(report.time_steps, NUM_TIME_STEPS)
        self.assertEqual(report.start, START_STEP)
        self.assertEqual(report.interval, SAMPLE_INTERVAL)

        node_id = report.node_ids[0]
        self.assertEqual(node_id, 0x587E2FF6)  # first node id from file
        node = report.nodes[node_id]
        self.assertAlmostEqual(node[0], 0.27906978)  # prevalence on time step 0
        self.assertEqual(node[729], 0.0)  # prevalence on time step 729

        self.assertAlmostEqual(node[180], 0.39795917)  # prevalence on time step 180
        self.assertAlmostEqual(
            report.nodes[0x58D12FFA][180], 0.43820226
        )  # prevalence in last node on time step 180

        return

    def test_writefile(self):

        NUM_TIME_STEPS = 3
        NUM_NODES = 4
        NODE_IDS = [x + 1 for x in range(NUM_NODES)]
        data = np.zeros((NUM_TIME_STEPS, NUM_NODES), dtype=np.float32)
        report = SpatialReport(node_ids=NODE_IDS, data=data)
        for node_id in NODE_IDS:
            for time_step in range(NUM_TIME_STEPS):
                report.nodes[node_id][time_step] = (10 * node_id) + time_step

        with tempfile.TemporaryDirectory() as temp:
            path = pathlib.Path(temp)
            filename = path / "spatial_report.bin"
            report.write_file(str(filename))

            test = SpatialReport(str(filename))
            self.assertEqual(test.data.shape, (NUM_TIME_STEPS, NUM_NODES))
            self.assertListEqual(list(test.node_ids), NODE_IDS)
            node = test.nodes[NODE_IDS[0]]
            self.assertEqual(node.id, NODE_IDS[0])
            self.assertEqual(len(node.data), NUM_TIME_STEPS)
            self.assertAlmostEqual(node.data[0], (10 * NODE_IDS[0]))
            node = test[NODE_IDS[1]]
            self.assertEqual(node.id, NODE_IDS[1])
            self.assertEqual(len(node.data), NUM_TIME_STEPS)
            self.assertAlmostEqual(node.data[1], (10 * NODE_IDS[1]) + 1)
            self.assertEqual(test.node_count, NUM_NODES)
            self.assertEqual(test.time_steps, NUM_TIME_STEPS)

        return

    def test_filtered_report(self):

        report = SpatialReport(os.path.join(manifest.spatrep_folder, "SpatialReportMalariaFiltered_Adult_Vectors.bin"))

        NUM_TIME_STEPS = 45
        NUM_NODES = 1423
        START_STEP = 8
        SAMPLE_INTERVAL = 16

        self.assertEqual(report.data.shape, (NUM_TIME_STEPS, NUM_NODES))
        self.assertEqual(len(report.node_ids), NUM_NODES)
        self.assertEqual(len(report.nodes), NUM_NODES)
        self.assertEqual(report.node_count, NUM_NODES)
        self.assertEqual(report.time_steps, NUM_TIME_STEPS)
        self.assertEqual(report.start, START_STEP)
        self.assertEqual(report.interval, SAMPLE_INTERVAL)

        return
