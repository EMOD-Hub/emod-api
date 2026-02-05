import datetime
import json
import math
import numpy as np
import os
import pathlib
import random
import tempfile
import emod_api.weather.weather as weather
from emod_api.weather.weather import Weather, Metadata, WeatherNode

from tests import manifest


class TestWeatherNode():
    def test_ctor(self):
        _NODE_ID = 42
        _NUM_VALUES = 365
        _DATA = np.zeros(_NUM_VALUES, dtype=np.float32)
        for i in range(_NUM_VALUES):
            _DATA[i] = random.random()
        node = WeatherNode(_NODE_ID, _DATA)

        self.assertEqual(node.id, _NODE_ID)
        self.assertListEqual(list(node.data), list(_DATA))
        self.assertListEqual([node[i] for i in range(_NUM_VALUES)], list(_DATA))

        return


class TestMetadata():
    def test_ctor(self):

        _NODE_IDS = [i for i in range(1, 9)]
        _NUM_VALUES = 365
        _AUTHOR = "joefaux"
        _TIMESTAMP = datetime.datetime.now()
        _FREQUENCY = "CLIMATE_UPDATE_FORTNIGHTLY"
        _PROVENANCE = "Fabrikam (c) 2019"
        _REFERENCE = "https://www.idmod.org"

        meta = Metadata(
            _NODE_IDS,
            _NUM_VALUES,
            _AUTHOR,
            _TIMESTAMP,
            _FREQUENCY,
            _PROVENANCE,
            _REFERENCE,
        )

        self.assertEqual(meta.author, _AUTHOR)
        self.assertEqual(meta.creation_date, _TIMESTAMP)
        self.assertEqual(meta.datavalue_count, _NUM_VALUES)
        self.assertEqual(meta.id_reference, _REFERENCE)
        self.assertEqual(meta.node_count, len(_NODE_IDS))
        self.assertListEqual(sorted(meta.node_ids), _NODE_IDS)
        self.assertEqual(meta.provenance, _PROVENANCE)
        self.assertEqual(meta.update_resolution, _FREQUENCY)
        self.assertEqual(len(meta.nodes), len(_NODE_IDS))
        self.assertEqual(set(meta.nodes.keys()), set(_NODE_IDS))

        return

    def test_invalidDatavalueCount(self):

        self.assertRaises(AssertionError, Metadata, [1, 3, 5, 7], -1)

        return

    def test_nodeIdsNone(self):

        # actually fails on isiterable()
        self.assertRaises(AssertionError, Metadata, None, 365)

        return

    def test_nodeIdsIsEmpty(self):

        self.assertRaises(AssertionError, Metadata, [], 365)

        return

    def test_nodeIdsNotIntegers(self):

        self.assertRaises(AssertionError, Metadata, [1, 3, "five", 7], 365)

        return

    def test_nodeIdsNotUnique(self):

        self.assertRaises(AssertionError, Metadata, [1, 3, 5, 7, 5, 3, 1], 365)

        return


class TestWeather():
    def test_ctor(self):

        USERNAME = "testuser"
        NUMVALUES = 365  # one year
        UPDATERESOLUTION = weather.CLIMATE_UPDATE_DAY
        PROVENANCE = "weather_test"
        IDREFERENCE = weather.IDREF_LEGACY
        NUMNODES = 16
        NODEIDS = [i for i in range(NUMNODES)]

        w = Weather(
            node_ids=NODEIDS,
            datavalue_count=NUMVALUES,
            author=USERNAME,
            frequency=UPDATERESOLUTION,
            provenance=PROVENANCE,
            reference=IDREFERENCE,
        )

        self.assertEqual(w.author, USERNAME)
        self.assertEqual(w.datavalue_count, NUMVALUES)
        self.assertEqual(w.id_reference, IDREFERENCE)
        self.assertEqual(w.provenance, PROVENANCE)
        self.assertEqual(w.update_resolution, UPDATERESOLUTION)
        self.assertEqual(len(w.nodes), NUMNODES)
        self.assertEqual(w.node_ids, NODEIDS)

        return

    def test_build(self):

        NUMVALUES = 365  # one year
        NUMNODES = 3
        NODEIDS = [i + 1 for i in range(NUMNODES)]

        w = Weather(node_ids=NODEIDS, datavalue_count=NUMVALUES)
        for i in range(NUMNODES):
            node = w[i + 1]
            for j in range(NUMVALUES):
                node.data[j] = 20.0 + i + math.sin(2.0 * math.pi * j / NUMVALUES)

        self.assertEqual(len(w.nodes), 3)
        self.assertEqual(w.nodes[1].data[0], 20.0)
        self.assertEqual(w.nodes[2].data[0], 21.0)
        self.assertEqual(w.nodes[3].data[0], 22.0)

        return

    def test_fromFile(self):

        NUMNODES = 35
        NUMVALUES = 365  # one year

        w = Weather(os.path.join(manifest.weather_folder, "Kenya_Nairobi_2.5arcmin_air_temperature_daily.bin"))

        self.assertEqual(w.datavalue_count, NUMVALUES)  # one year of data
        self.assertEqual(len(w.nodes), NUMNODES)  # expecting 35 nodes
        self.assertAlmostEqual(
            w.nodes[340789328][000], 18.711098, 5
        )  # temperature for day 001, first node
        self.assertAlmostEqual(
            w.nodes[340789329][179], 15.900291, 5
        )  # temperature for day 180, second node
        self.assertAlmostEqual(
            w.nodes[341444690][364], 20.573992, 5
        )  # temperature for day 365, last node

        return

    def test_badMetadata(self):

        # TODO create .json file where #nodes * #values != size of data
        # self.assertRaises(AssertionError, Weather.fromFile, os.path.join(WORKING_DIRECTORY, 'test', 'filename'))
        return

    def test_fromCsv(self):

        NUMNODES = 8
        NUMVALUES = 365

        w = Weather.from_csv(os.path.join(manifest.weather_folder, "airtemp.csv"))

        self.assertEqual(w.datavalue_count, NUMVALUES)
        self.assertEqual(len(w.nodes), NUMNODES)
        self.assertAlmostEqual(
            w.nodes[1][0], 28.031484603881836
        )  # temperature for day 001, node 1
        self.assertAlmostEqual(
            w.nodes[2][1], 20.600126266479492
        )  # temperature for day 002, node 2
        self.assertAlmostEqual(
            w.nodes[3][2], 24.253694534301758
        )  # temperature for day 003, node 3
        self.assertAlmostEqual(
            w.nodes[4][3], 24.54370880126953
        )  # temperature for day 004, node 4
        self.assertAlmostEqual(
            w.nodes[5][361], 29.559690475463867
        )  # temperature for day 362, node 5
        self.assertAlmostEqual(
            w.nodes[6][362], 27.812746047973633
        )  # temperature for day 363, node 6
        self.assertAlmostEqual(
            w.nodes[7][363], 19.86736297607422
        )  # temperature for day 364, node 7
        self.assertAlmostEqual(
            w.nodes[8][364], 27.268556594848633
        )  # temperature for day 365, node 8

        return

    def test_badCsvStepIndicesDoNotMatch(self):

        # TODO create .csv where different nodes have different step indices, e.g., [ 0, 1, 2 ] and [ 1, 2, 3 ]
        # self.assertRaises(AssertionError, Weather.fromCsv, os.path.join(WORKING_DIRECTORY, 'test', 'filename'))
        return

    def test_badCsvNumberOfValues(self):

        # TODO create .csv where #values for nodes differs, e.g., [ 0, 1, 2, 3 ] and [ 0, 1, 2 ]
        # self.assertRaises(AssertionError, Weather.fromCsv, os.path.join(WORKING_DIRECTORY, 'test', 'filename'))
        return

    def test_writeFile(self):

        USERNAME = "testuser"
        PROVENANCE = "Python unittests"
        NUMNODES = 8
        NUMVALUES = 365
        CHARSPERID = 8
        CHARSPEROFFSET = 8
        IDREFERENCE = weather.IDREF_LEGACY
        UPDATERESOLUTION = weather.CLIMATE_UPDATE_DAY

        w = Weather.from_csv(os.path.join(manifest.weather_folder, "rainfall.csv"),
            var_column="rainfall",
            author=USERNAME,
            provenance=PROVENANCE,
        )
        with tempfile.TemporaryDirectory() as temp:
            path = pathlib.Path(temp)
            filename = path / "weathertest.bin"
            w.write_file(str(filename))

            # verify metadata in .json file
            with open(str(filename) + ".json", "r") as file:
                jason = json.load(file)

            self.assertEqual(jason["Metadata"]["Author"], USERNAME)
            self.assertEqual(jason["Metadata"]["DataProvenance"], PROVENANCE)
            self.assertEqual(jason["Metadata"]["IdReference"], IDREFERENCE)
            self.assertEqual(jason["Metadata"]["NodeCount"], NUMNODES)
            self.assertEqual(jason["Metadata"]["DatavalueCount"], NUMVALUES)
            self.assertEqual(jason["Metadata"]["UpdateResolution"], UPDATERESOLUTION)
            self.assertEqual(
                len(jason["NodeOffsets"]), ((CHARSPERID + CHARSPEROFFSET) * NUMNODES)
            )

            # verify binary file
            data = np.fromfile(str(filename), dtype=np.float32)

            self.assertEqual(
                len(data), NUMVALUES * NUMNODES
            )  # verify size of .bin file
            self.assertAlmostEqual(data[0], 0.017921853810548782)  # node 1, first value
            self.assertAlmostEqual(
                data[363], 0.0006026369519531727
            )  # node 1, 364th value
            self.assertAlmostEqual(data[2559], 0.0985349640250206)  # node 8, 5th value
            self.assertAlmostEqual(
                data[2919], 0.057558413594961166
            )  # node 8, last value

        return
