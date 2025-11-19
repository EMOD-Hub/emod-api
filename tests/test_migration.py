from collections import namedtuple
from contextlib import contextmanager
from datetime import datetime
import json
import numpy as np
import os
import math
from os import close, environ
from pathlib import Path
from platform import system
from tempfile import mkstemp
import unittest
from emod_api.migration.migration import Migration, from_file, from_demog_and_param_gravity, to_csv, examine_file, from_csv
import pandas as pd
import io
from contextlib import redirect_stdout
from tests import manifest


class MigrationTests(unittest.TestCase):

    user = "unknown"
    kenya_regional_migration = None
    guinea_pig = None

    @classmethod
    def setUpClass(cls):

        cls.user = environ["USERNAME"] if system() == "Windows" else environ["USER"]
        filename = os.path.join(manifest.migration_folder, "Kenya_Regional_Migration_from_Census.bin")
        cls.kenya_regional_migration = from_file(filename)
        cls.guinea_pig = Migration()

    def test_defaults(self):
        """
        Changing the defaults is a breaking change.
        """

        migration = Migration()
        self.assertListEqual(migration.AgesYears, [])
        self.assertEqual(migration.Author, self.user)
        self.assertEqual(migration.DatavalueCount, 0)
        # weekday, month, day, year, hour, minute - might fail if minute rolls over
        self.assertEqual(f"{migration.DateCreated:%a %b %d %Y %H:%M}", f"{datetime.now():%a %b %d %Y %H:%M}")
        self.assertEqual(migration.GenderDataType, Migration.SAME_FOR_BOTH_GENDERS)
        self.assertEqual(migration.IdReference, Migration.IDREF_LEGACY)
        self.assertEqual(migration.InterpolationType, Migration.PIECEWISE_CONSTANT)
        self.assertEqual(migration.MigrationType, Migration.LOCAL)
        self.assertEqual(migration.NodeCount, 0)
        self.assertEqual(migration.NodeOffsets, {})
        self.assertEqual(migration.Tool, "emod-api")

        return

    def test_get_agesyears(self):
        """AgesYears from migration [metadata] file is readable."""
        self.assertListEqual(self.kenya_regional_migration.AgesYears,
                             [0.0, 2.5, 7.5, 12.5, 17.5, 22.5, 27.5, 32.5, 37.5, 42.5, 47.5, 52.5, 57.5])
        return

    def test_set_agesyears(self):
        """AgesYears is settable and readable."""
        ages = [0, 5, 20, 125]
        self.guinea_pig.AgesYears = ages
        self.assertListEqual(self.guinea_pig.AgesYears, ages)
        return

    def test_get_author(self):
        """Author from migration [metadata] file is readable."""
        self.assertEqual(self.kenya_regional_migration.Author, "dbridenbecker")
        return

    def test_set_author(self):
        """Author is settable and readable."""
        author = "Rumpelstiltskin"
        self.guinea_pig.Author = author
        self.assertEqual(self.guinea_pig.Author, author)
        return

    def test_get_datavaluecount(self):
        """DatavalueCount from migration [metadata] file is readable."""
        self.assertEqual(self.kenya_regional_migration.DatavalueCount, 7)
        return

    # may not directly set DatavalueCount - derived from internal data
    def test_set_datavaluecount(self):
        """DatavalueCount is _not_ directly settable (derived from underlying data)."""
        with self.assertRaises(AttributeError):
            self.guinea_pig.DatavalueCount = 42
        return

    def test_get_datecreated(self):
        """DateCreated from migration [metadata] file is readable."""
        # Mon May  2 20:30:12 2016
        self.assertEqual(self.kenya_regional_migration.DateCreated,
                         datetime(year=2016, month=5, day=2, hour=20, minute=30, second=12))
        return

    def test_set_datecreated(self):
        """DateCreated is settable and readable."""
        timestamp = datetime.now()
        self.guinea_pig.DateCreated = timestamp
        self.assertEqual(self.guinea_pig.DateCreated, timestamp)
        return

    def test_set_bad_datecreated(self):
        """DateCreated must be a datetime object."""
        with self.assertRaises(RuntimeError) as context:
            self.guinea_pig.DateCreated = "yesterday"
        self.assertTrue("DateCreated must be a datetime" in str(context.exception))
        return

    def test_get_genderdatatype(self):
        """GenderDataType from migration [metadata] file is readable."""
        self.assertEqual(self.kenya_regional_migration.GenderDataType, Migration.ONE_FOR_EACH_GENDER)
        return

    def test_set_genderdatatype(self):
        """GenderDataType is settable and readable."""
        self.guinea_pig.GenderDataType = 1
        self.assertEqual(self.guinea_pig.GenderDataType, Migration.ONE_FOR_EACH_GENDER)
        self.guinea_pig.GenderDataType = "SAME_FOR_BOTH_GENDERS"
        self.assertEqual(self.guinea_pig.GenderDataType, Migration.SAME_FOR_BOTH_GENDERS)
        return

    def test_set_bad_genderdatatype_one(self):
        """GenderDataType must be in the range Migration.SAME_FOR_BOTH_GENDERS (0) ... Migration.ONE_FOR_EACH_GENDER (1)."""
        with self.assertRaises(RuntimeError) as context:
            self.guinea_pig.GenderDataType = -1
        self.assertTrue("Unknown gender data type, -1" in str(context.exception))
        return

    def test_set_bad_genderdatatype_two(self):
        """GenderDataType must be in the range Migration.SAME_FOR_BOTH_GENDERS (0) ... Migration.ONE_FOR_EACH_GENDER (1)."""
        with self.assertRaises(RuntimeError) as context:
            self.guinea_pig.GenderDataType = 13
        self.assertTrue("Unknown gender data type, 13" in str(context.exception))
        return

    def test_set_bad_genderdatatype_three(self):
        """GenderDataType enum must be 'SAME_FOR_BOTH_GENDERS' or 'ONE_FOR_EACH_GENDER'."""
        with self.assertRaises(RuntimeError) as context:
            self.guinea_pig.GenderDataType = "GENDER_NEUTRAL"
        self.assertTrue("Unknown gender data type, GENDER_NEUTRAL" in str(context.exception))
        return

    def test_get_idreference(self):
        """IdReference from migration [metadata] file is readable."""
        self.assertEqual(self.kenya_regional_migration.IdReference, "0")
        return

    def test_set_idreference(self):
        """IdReference is settable and readable."""
        reference = "Cool Custom Test IdReference"
        self.guinea_pig.IdReference = reference
        self.assertEqual(self.guinea_pig.IdReference, reference)
        return

    def test_get_interpolationtype(self):
        """InterpolationType from migration [metadata] file is readable."""
        self.assertEqual(self.kenya_regional_migration.InterpolationType, Migration.PIECEWISE_CONSTANT)
        return

    def test_set_interpolationtype(self):
        """InterpolationType is settable from constant or string."""
        # should be starting at PIECEWISE_CONSTANT (default value)
        self.guinea_pig.InterpolationType = Migration.LINEAR_INTERPOLATION
        self.assertEqual(self.guinea_pig.InterpolationType, Migration.LINEAR_INTERPOLATION)
        self.guinea_pig.InterpolationType = "PIECEWISE_CONSTANT"
        self.assertEqual(self.guinea_pig.InterpolationType, Migration.PIECEWISE_CONSTANT)
        self.guinea_pig.InterpolationType = "LINEAR_INTERPOLATION"
        self.assertEqual(self.guinea_pig.InterpolationType, Migration.LINEAR_INTERPOLATION)
        self.guinea_pig.InterpolationType = Migration.PIECEWISE_CONSTANT
        self.assertEqual(self.guinea_pig.InterpolationType, Migration.PIECEWISE_CONSTANT)
        return

    def test_set_bad_interpolationtype_one(self):
        """InterpolationType must be LINEAR_INTERPOLATION (0) or PIECEWISE_CONSTANT (1)."""
        with self.assertRaises(RuntimeError) as context:
            self.guinea_pig.InterpolationType = -1
        self.assertTrue("Unknown interpolation type, -1" in str(context.exception))
        return

    def test_set_bad_interpolationtype_two(self):
        """InterpolationType must be LINEAR_INTERPOLATION (0) or PIECEWISE_CONSTANT (1)."""
        with self.assertRaises(RuntimeError) as context:
            self.guinea_pig.InterpolationType = 13
        self.assertTrue("Unknown interpolation type, 13" in str(context.exception))
        return

    def test_set_bad_interpolationtype_three(self):
        """InterpolationType must be 'LINEAR_INTERPOLATION' or 'PIECEWISE_CONSTANT'."""
        with self.assertRaises(RuntimeError) as context:
            self.guinea_pig.InterpolationType = "Complex Integration"
        self.assertTrue("Unknown interpolation type, Complex Integration" in str(context.exception))
        return

    def test_get_migrationtype(self):
        """MigrationType from migration [metadata] file is readable."""
        self.assertEqual(self.kenya_regional_migration.MigrationType, Migration.REGIONAL)
        return

    def test_set_migrationtype(self):
        """MigrationType is settable from constant or string."""
        self.guinea_pig.MigrationType = Migration.AIR
        self.assertEqual(self.guinea_pig.MigrationType, Migration.AIR)
        self.guinea_pig.MigrationType = "REGIONAL_MIGRATION"
        self.assertEqual(self.guinea_pig.MigrationType, Migration.REGIONAL)
        self.guinea_pig.MigrationType = 1
        self.assertEqual(self.guinea_pig.MigrationType, Migration.LOCAL)
        self.guinea_pig.MigrationType = Migration.SEA
        self.assertEqual(self.guinea_pig.MigrationType, Migration.SEA)
        self.guinea_pig.MigrationType = "FAMILY_MIGRATION"
        self.assertEqual(self.guinea_pig.MigrationType, Migration.FAMILY)
        self.guinea_pig.MigrationType = 6
        self.assertEqual(self.guinea_pig.MigrationType, Migration.INTERVENTION)
        return

    def test_set_bad_migrationtype_one(self):
        """MigrationType must be one of LOCAL (1), AIR (2), REGIONAL (3), SEA (4), FAMILY (5), or INTERVENTION (6)."""
        with self.assertRaises(RuntimeError) as context:
            self.guinea_pig.MigrationType = -1
        self.assertTrue("Unknown migration type, -1" in str(context.exception))
        return

    def test_set_bad_migrationtype_two(self):
        """MigrationType must be one of LOCAL (1), AIR (2), REGIONAL (3), SEA (4), FAMILY (5), or INTERVENTION (6)."""
        with self.assertRaises(RuntimeError) as context:
            self.guinea_pig.MigrationType = 7
        self.assertTrue("Unknown migration type, 7" in str(context.exception))
        return

    def test_set_bad_migrationtype_three(self):
        """
        MigrationType must be one of 'LOCAL_MIGRATION', 'AIR_MIGRATION', 'REGIONAL_MIGRATION', 'SEA_MIGRATION',
        'FAMILY_MIGRATION', or 'INTERVENTION_MIGRATION'.
        """
        with self.assertRaises(RuntimeError) as context:
            self.guinea_pig.MigrationType = "DISPLACED_MIGRATION"
        self.assertTrue("Unknown migration type, DISPLACED_MIGRATION" in str(context.exception))
        return

    def test_get_nodecount(self):
        """NodeCount from migration file is correct."""
        self.assertEqual(self.kenya_regional_migration.NodeCount, 8)
        return

    def test_set_nodecount(self):
        """NodeCount cannot be set directly, derives from underlying data."""
        with self.assertRaises(AttributeError):
            self.kenya_regional_migration.NodeCount = 42
        return

    def test_get_nodeoffsets(self):
        """NodeOffsets from migration file are correct."""
        offsets = {
            1: int("00000000", 16),
            2: int("00000054", 16),
            3: int("000000A8", 16),
            4: int("000000FC", 16),
            5: int("00000150", 16),
            6: int("000001A4", 16),
            7: int("000001F8", 16),
            8: int("0000024C", 16)
        }
        self.assertDictEqual(self.kenya_regional_migration.NodeOffsets, offsets)
        return

    def test_set_nodeoffsets(self):
        """NodeOffsets cannot be set directly, derives from underlying data."""
        with self.assertRaises(AttributeError):
            self.guinea_pig.NodeOffsets = {0: 0, 1: 12, 2: 24}
        return

    def test_get_tool(self):
        """Tool from migration [metadata] file is readable."""
        self.assertEqual(self.kenya_regional_migration.Tool, "convert_json_to_bin.py")
        return

    def test_set_tool(self):
        """Tool is settable and readable."""
        self.guinea_pig.Tool = Path(__file__).name
        self.assertEqual(self.guinea_pig.Tool, Path(__file__).name)
        return

    def test_set_rates(self):
        """Migration rates can be set and read back for each scenario."""

        # Case 1 - no gender or age differentiation - key is node id
        migration = Migration()
        migration[20201202][19991231] = 0.125
        self.assertEqual(migration._layers[0][20201202][19991231], 0.125)

        # Case 2 - age buckets w/out gender differentiation - key is node id:age
        migration = Migration()
        migration.AgesYears = [5, 20]
        migration[20201202:10][19991231] = 0.125
        migration[20201202, 5][19690720] = 0.25
        self.assertEqual(migration._layers[1][20201202][19991231], 0.125)
        self.assertEqual(migration._layers[0][20201202][19690720], 0.25)

        # Case 3 - by gender w/out age differentiation - key is node id:gender
        migration = Migration()
        migration.GenderDataType = Migration.ONE_FOR_EACH_GENDER
        migration[20201202:Migration.FEMALE][19991231] = 0.125
        migration[20201202, Migration.MALE][19690720] = 0.25
        self.assertEqual(migration._layers[1][20201202][19991231], 0.125)
        self.assertEqual(migration._layers[0][20201202][19690720], 0.25)

        # Case 4 - both gender and age buckets - key is node id:gender:age
        migration = Migration()
        migration.GenderDataType = Migration.ONE_FOR_EACH_GENDER
        migration.AgesYears = [5, 20]
        migration[20201202:Migration.MALE:10][19991231] = 0.125
        migration[20201202, Migration.FEMALE, 25][19690720] = 0.25
        self.assertEqual(migration._layers[1][20201202][19991231], 0.125)
        self.assertEqual(migration._layers[3][20201202][19690720], 0.25)

        return

    def test_no_connection(self):
        """Node 13 is not in the rate map, should return 0."""
        migration = self._three_square()
        self.assertEqual(migration[1][13], 0.0)

        return

    def test_non_integral_node_id(self):
        """"Node IDs must be integers."""
        migration = self._three_square()
        with self.assertRaises(RuntimeError):
            migration[3.14159][5] = 0.125
        return

    def test_non_numeric_node_id(self):
        """Node IDs must be integers."""
        migration = self._three_square()
        with self.assertRaises(RuntimeError):
            migration["three"][5] = 0.125
        return

    def test_warning_on_age_dependency(self):
        """Should get warning if changing age dependency after data has been recorded."""
        migration = Migration()
        migration[0][1] = 0.0625
        migration[0][2] = 0.0625
        migration[0][3] = 0.03125
        with self.assertWarns(UserWarning):
            migration.AgesYears = [0, 5, 10, 15, 20, 125]
        return

    def test_warning_on_gender_dependency(self):
        """Should get warning if changing gender dependency after data has been recorded."""
        migration = Migration()
        migration[0][1] = 0.0625
        migration[0][2] = 0.0625
        migration[0][3] = 0.03125
        with self.assertWarns(UserWarning):
            migration.GenderDataType = Migration.ONE_FOR_EACH_GENDER
        return

    def test_nodes_property(self):
        """Nodes property should return sorted list of all node IDs."""
        migration = self._three_square()
        self.assertListEqual(migration.Nodes, list(range(1, 10)))
        return

    def test_age_dependent_indexing_raises(self):
        """Age dependent migration must have ID:AGE indexing."""
        migration = Migration()
        migration.AgesYears = [0, 5, 10, 15, 20, 125]
        with self.assertRaises(RuntimeError):
            migration[0][1] = 0.0625
        return

    def test_gender_dependent_indexing_raises_one(self):
        """Gender dependent migration must have ID:GENDER indexing."""
        migration = Migration()
        migration.GenderDataType = Migration.ONE_FOR_EACH_GENDER
        with self.assertRaises(RuntimeError):
            migration[0][1] = 0.0625
        return

    def test_gender_dependent_indexing_raises_two(self):
        """Gender dependent migration must have ID:GENDER indexing."""
        migration = Migration()
        migration.GenderDataType = Migration.ONE_FOR_EACH_GENDER
        with self.assertRaises(RuntimeError):
            migration["zero":Migration.MALE][1] = 0.0625
        return

    def test_gender_dependent_indexing_raises_three(self):
        """Gender dependent migration must have ID:GENDER indexing."""
        migration = Migration()
        migration.GenderDataType = Migration.ONE_FOR_EACH_GENDER
        with self.assertRaises(RuntimeError):
            migration[0:13][1] = 0.0625
        return

    def test_age_and_gender_dependent_indexing_raises_one(self):
        """Gender and age dependent migration must have ID:GENDER:AGE indexing."""
        migration = Migration()
        migration.AgesYears = [0, 5, 125]
        migration.GenderDataType = Migration.ONE_FOR_EACH_GENDER
        with self.assertRaises(RuntimeError):
            migration[0][1] = 0.0625
        return

    def test_age_and_gender_dependent_indexing_raises_two(self):
        """Gender and age dependent migration must have ID:GENDER:AGE indexing."""
        migration = Migration()
        migration.AgesYears = [0, 5, 125]
        migration.GenderDataType = Migration.ONE_FOR_EACH_GENDER
        with self.assertRaises(RuntimeError):
            migration["zero":Migration.MALE:25][1] = 0.0625
        return

    def test_age_and_gender_dependent_indexing_raises_three(self):
        """Gender and age dependent migration must have ID:GENDER:AGE indexing."""
        migration = Migration()
        migration.AgesYears = [0, 5, 125]
        migration.GenderDataType = Migration.ONE_FOR_EACH_GENDER
        with self.assertRaises(RuntimeError):
            migration[0:13:25][1] = 0.0625
        return

    @staticmethod
    def _three_square():
        """Create 3x3 grid with migration to N/S/E/W neighbors (not diagonal and not wrapped around)."""
        migration = Migration()
        Link = namedtuple("Link", ["source", "destination", "rate"])
        rates = [
            Link(1, 2, 0.12),   # NW -> N
            Link(1, 4, 0.14),   # NW -> W
            Link(2, 1, 0.21),   # N -> NW
            Link(2, 3, 0.23),   # N -> NE
            Link(2, 5, 0.25),   # N -> center
            Link(3, 2, 0.32),   # NE -> N
            Link(3, 6, 0.36),   # NE -> E
            Link(4, 1, 0.41),   # W -> NW
            Link(4, 5, 0.45),   # W -> center
            Link(4, 7, 0.47),   # W -> SW
            Link(5, 2, 0.52),   # center -> N
            Link(5, 4, 0.54),   # center -> W
            Link(5, 6, 0.56),   # center -> E
            Link(5, 8, 0.58),   # center -> S
            Link(6, 3, 0.63),   # E -> NE
            Link(6, 5, 0.65),   # E -> center
            Link(6, 9, 0.69),   # E -> SE
            Link(7, 5, 0.75),   # SW -> W
            Link(7, 8, 0.78),   # SW -> S
            Link(8, 5, 0.85),   # S -> center
            Link(8, 7, 0.87),   # S -> SW
            Link(8, 9, 0.89),   # S -> SE
            Link(9, 6, 0.96),   # SE -> E
            Link(9, 8, 0.98)    # SE -> S
        ]

        for link in rates:
            migration[link.source][link.destination] = link.rate
        migration.MigrationType = Migration.REGIONAL

        return migration

    @staticmethod
    @contextmanager
    def _temp_filename(prefix: str = "mig-", suffix: str = ".bin"):
        """Create temporary directory for migration file, return filename and matching metadata file name."""
        handle, filename = mkstemp(prefix=prefix, suffix=suffix)
        close(handle)
        filename = Path(filename).absolute()
        metafile = filename.parent / (filename.name + ".json")
        try:
            yield filename, metafile
        finally:
            filename.unlink() if filename.exists() else None
            metafile.unlink() if metafile.exists() else None

        return

    def test_to_file(self):
        """Write migration to file, check metadata and spot check binary data."""
        migration = self._three_square()

        with self._temp_filename() as (filename, metafile):
            migration.to_file(filename)

            metafile = filename.parent / (filename.name + ".json")

            self.assertTrue(metafile.exists())
            with metafile.open("r") as metafile_handle:
                metadata = json.load(metafile_handle)
            self.assertEqual(metadata["Metadata"]["Tool"], "emod-api")
            self.assertEqual(metadata["Metadata"]["IdReference"], "Legacy")
            self.assertEqual(metadata["Metadata"]["MigrationType"], "REGIONAL_MIGRATION")
            self.assertEqual(metadata["Metadata"]["NodeCount"], 9)
            self.assertEqual(metadata["Metadata"]["DatavalueCount"], 4)
            self.assertEqual(metadata["Metadata"]["GenderDataType"], "SAME_FOR_BOTH_GENDERS")

            self.assertTrue(filename.exists())

            expected_size = 9 * 4 * 12  # #nodes x #links x #bytes (4 + 8)
            self.assertEqual(filename.stat().st_size, expected_size)

            with filename.open("rb") as filename_handle:
                destinations = np.fromfile(filename_handle, dtype=np.uint32, count=4)
                values = np.fromfile(filename_handle, dtype=np.float64, count=4)
                self.assertEqual(destinations[0], 2)    # first destination is node 2 (sorted in rate ascending order)
                self.assertEqual(values[1], 0.14)       # rate between nodes 1 and 4 is 0.14

        return

    def test_to_csv(self):
        filename = os.path.join(manifest.migration_folder, "Seattle_30arcsec_local_migration.bin")

        f = io.StringIO()
        with redirect_stdout(f):
            to_csv(filename)
        out = f.getvalue()

        data = io.StringIO(out)
        data_frame = pd.read_csv(data, sep=",")
        self.assertEqual(len(data_frame), 515)
        self.assertEqual(len(data_frame.columns), 3)

        self.assertFalse(data_frame.isnull().values.any())

    def test_examine_file(self):
        filename = os.path.join(manifest.migration_folder, "Seattle_30arcsec_local_migration.bin")
        output = os.path.join(manifest.output_folder, "seattle_csv.csv")

        expected_output = ["Author:", "DatavalueCount:", "DateCreated:", "GenderDataType:", "IdReference:",
                           "InterpolationType:", "MigrationType:", "NodeCount:", "NodeOffsets:", "Tool:", "Nodes:"]

        f = io.StringIO()
        with redirect_stdout(f):
            examine_file(filename)
        output = f.getvalue()

        for expected in expected_output:
            self.assertTrue(expected in output)

    def test_to_file_age_dependent(self):
        """Write migration file with age dependent rates. Check for 'AgesYears' in metadata file."""
        migration = Migration()
        migration.AgesYears = [0, 5, 10, 15, 20, 125]
        for age in migration.AgesYears:
            migration[0:age][1] = 0.125 / age if age else 0
            migration[1:age][0] = 0.125 / age if age else 0
        with self._temp_filename(prefix="age-mig-") as (filename, metafile):
            migration.to_file(filename)
            with metafile.open("r") as file:
                metadata = json.load(file)
            self.assertListEqual(metadata["Metadata"]["AgesYears"], migration.AgesYears)

        return

    def test_limited_datavalues(self):
        """Test limiting datavalues when writing file to disk."""
        # migration = self._three_square()

        # Create SIZExSIZE grid migration data
        SIZE = 5
        migration = Migration()
        for source in range(0, SIZE * SIZE):
            source_x = source % SIZE
            source_y = source // SIZE
            for destination in range(0, SIZE * SIZE):
                if destination == source:
                    continue
                destination_x = destination % SIZE
                destination_y = destination // SIZE
                distance = abs(destination_x - source_x) + abs(destination_y - source_y)   # Manhattan distance
                rate = 0.1 / distance
                migration[source + 1][destination + 1] = rate   # IDs go from 1..(SIZE*SIZE)

        # Ensure setup
        for node in migration.Nodes:
            self.assertTrue(len(migration[node]) == (SIZE * SIZE - 1))  # Nodes have no entry for self

        LIMIT = 3
        with self._temp_filename() as (filename, metafile):
            migration.to_file(filename, value_limit=LIMIT)
            with metafile.open("r") as file:
                metadata = json.load(file)
            self.assertEqual(metadata["Metadata"]["DatavalueCount"], LIMIT)
            actual = from_file(filename)
            self.assertEqual(actual.DatavalueCount, LIMIT)
            for node in actual.Nodes:
                self.assertTrue(len(actual[node]) == LIMIT)

        return

    # TODO - test that when values are truncated in to_file(), see above, the saved values are
    # 1. the largest N from the values in the Migration object and
    # 2. sorted from smallest to largest

    def test_missing_source_nodes_warning(self):
        """Test warning when a source node in one layer has no entries in another layer."""
        migration = Migration()
        migration.GenderDataType = Migration.ONE_FOR_EACH_GENDER
        source = 4
        for destination in range(9):
            if destination != source:
                migration[4:Migration.MALE][destination] = 0.0625
                # note, not setting values in Migration.FEMALE layer
        with self._temp_filename(prefix="gender-mig-") as (filename, metafile):
            with self.assertWarns(UserWarning):
                migration.to_file(filename)

        return

    def test_raise_from_file_missing_binary(self):
        """Test exception for missing binary file in from_file() call."""
        migration = self._three_square()
        with self._temp_filename() as (filename, metafile):
            migration.to_file(filename)
            filename.unlink()
            with self.assertRaises(RuntimeError):
                _ = from_file(filename)

        return

    def test_raise_from_file_missing_metadata(self):
        """Test exception for missing metadata file in from_file() call."""
        migration = self._three_square()
        with self._temp_filename() as (filename, metafile):
            migration.to_file(filename)
            metafile.unlink()
            with self.assertRaises(RuntimeError):
                _ = from_file(filename)

        return

    def test_raise_from_file_bad_nodeoffsets(self):
        """Test exception for NodeOffsets not matching expected size for NodeCount and DatavalueCount."""
        migration = self._three_square()
        with self._temp_filename() as (filename, metafile):
            migration.to_file(filename)
            with metafile.open("r") as file:
                metadata = json.load(file)
            metadata["NodeOffsets"] = "0000004200000000"
            with metafile.open("w") as file:
                json.dump(metadata, file)
            with self.assertRaises(RuntimeError):
                _ = from_file(filename)

        return

    def test_warn_on_datecreated_parsing(self):
        """Test warning when DateCreated field cannot be parsed."""
        migration = self._three_square()
        with self._temp_filename() as (filename, metafile):
            migration.to_file(filename)
            with metafile.open("r") as file:
                metadata = json.load(file)
            metadata["Metadata"]["DateCreated"] = "Thursday December 10th 2020"
            with metafile.open("w") as file:
                json.dump(metadata, file)
            with self.assertWarns(UserWarning):
                _ = from_file(filename)

        return

    def test_from_file(self):
        """Test happy path for from_file()."""
        local = from_file(os.path.join(manifest.migration_folder, "Seattle_30arcsec_local_migration.bin"))
        self.assertEqual(local.Author, "jsteinkraus")
        self.assertEqual(local.DateCreated, datetime(year=2011, month=9, day=26, hour=9, minute=59, second=35))
        self.assertEqual(local.DatavalueCount, 8)
        self.assertEqual(local.IdReference, "Legacy")
        self.assertEqual(local.NodeCount, 124)
        self.assertEqual(local.Tool, "createmigrationheader.py")
        self.assertEqual(local.MigrationType, 1)

        regional = from_file(os.path.join(manifest.migration_folder, "Seattle_30arcsec_regional_migration.bin"))
        self.assertEqual(regional.Author, "jsteinkraus")
        self.assertEqual(regional.DateCreated, datetime(year=2011, month=9, day=26, hour=9, minute=59, second=35))
        self.assertEqual(regional.DatavalueCount, 30)
        self.assertEqual(regional.IdReference, "Legacy")
        self.assertEqual(regional.NodeCount, 124)
        self.assertEqual(regional.Tool, "createmigrationheader.py")
        self.assertEqual(regional.MigrationType, 3)

        return

    def test_to_and_from_file_with_nonstandard_metadata_filename(self):
        """Use options to write and subsequently read from a file with a non-standard metadata filename"""
        memory = self._three_square()
        with self._temp_filename() as (filename, _):
            with self._temp_filename(prefix="meta-", suffix=".json") as (metafile, _):
                memory.to_file(filename, metafile=metafile)
                self.assertTrue(filename.exists())
                self.assertTrue(metafile.exists())
                disk = from_file(filename, metafile=metafile)
                self.assertEqual(disk.Author, memory.Author)
                # self.assertEqual(disk.DateCreated, memory.DateCreated)  # memory includes microseconds != 0
                self.assertEqual(f"{disk.DateCreated:%a %b %d %Y %H:%M}", f"{memory.DateCreated:%a %b %d %Y %H:%M}")
                self.assertEqual(disk.DatavalueCount, memory.DatavalueCount)
                self.assertEqual(disk.IdReference, memory.IdReference)
                self.assertEqual(disk.NodeCount, memory.NodeCount)
                self.assertEqual(disk.Tool, memory.Tool)
                for node in memory.Nodes:
                    self.assertDictEqual(disk[node], memory[node])

        return

    # miscellaneous

    def test_from_demog_and_param_gravity(self):
        demographics_file = os.path.join(manifest.demo_folder, 'Seattle_30arcsec_demographics.json')
        migration = from_demog_and_param_gravity(demographics_file, gravity_params=[0.1, 0.2, 0.3, 0.4],
                                                 id_ref='from_demog_and_param_gravity_test',
                                                 migration_type=Migration.LOCAL)
        self.assertEqual(migration.NodeCount, 124)
        self.assertEqual(migration.DatavalueCount, 123)
        self.assertEqual(migration.IdReference, "from_demog_and_param_gravity_test")
        self.assertEqual(migration.MigrationType, Migration.LOCAL)

    def test_from_demog_and_param_gravity_distance(self):
        def get_distance(lat1, lon1, lat2, lon2):
            r = 6371
            d_lat = deg2rad(lat2 - lat1)

            d_lon = deg2rad(lon2 - lon1)
            a = math.sin(d_lat / 2) * math.sin(d_lat / 2) + \
                math.cos(deg2rad(lat1)) * math.cos(deg2rad(lat2)) * \
                math.sin(d_lon / 2) * math.sin(d_lon / 2)
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
            d = r * c
            return d

        def deg2rad(deg):
            return deg * (math.pi / 180)

        def verify_distance(migration_rate_list, node_locations):
            for rate_val in migration_rate_list[1:-1]:
                rate_val = rate_val.split(',')
                distance = 1 / float(rate_val[-1])
                src = int(rate_val[0])
                des = int(rate_val[1])
                lat1, lon1 = node_locations[src - 1]
                lat2, lon2 = node_locations[des - 1]
                calculated_distance = get_distance(lat1, lon1, lat2, lon2)
                self.assertAlmostEqual(distance, calculated_distance, delta=2)  # km

        id_ref = 'from_demog_and_param_gravity_distance'
        demographics_file = os.path.join(manifest.demo_folder, 'gravity_webservice_vs_local_distance_only.json')
        locations = [[0, 0],
                     [0, 1],
                     [0, 2],
                     [1, 0],
                     [1, 1],
                     [1, 2],
                     [2, 0],
                     [2, 1],
                     [2, 2]]

        # This demographics file is generated with the following code:
        # from emod_api.demographics.Node import Node
        # import emod_api.demographics.Demographics as Demographics
        #
        # nodes = []
        # # Add nodes to demographics
        # n_nodes = 9
        # for idx in range(n_nodes):
        #     nodes.append(Node(forced_id=idx + 1, pop=1, lat=locations[idx][0],
        #                       lon=locations[idx][1]))
        #
        # demog = Demographics.Demographics(nodes=nodes, idref=id_ref)
        # demog.SetDefaultProperties()
        # demog.generate_file(demographics_file)

        migration_local = from_demog_and_param_gravity(demographics_file, gravity_params=[1, 1, 1, -1],
                                                       id_ref=id_ref, migration_type=Migration.REGIONAL)

        migration_local_file = Path(os.path.join(manifest.output_folder, 'gravity_distance.bin'))
        migration_local.to_file(migration_local_file)

        f = io.StringIO()
        with redirect_stdout(f):
            to_csv(migration_local_file)
        migration_rate = f.getvalue().split("\n")

        verify_distance(migration_rate, locations)

    def test_from_demog_and_param_gravity_with_reference(self):
        demographics_file = os.path.join(manifest.demo_folder, 'Seattle_30arcsec_demographics.json')

        migration = from_demog_and_param_gravity(demographics_file, gravity_params=[0.1, 0.2, 0.3, 0.4],
                                                 id_ref='from_demog_and_param_gravity_test',
                                                 migration_type=Migration.LOCAL)

        migration_file = Path(os.path.join(manifest.output_folder, 'test_from_demog_and_param_gravity_with_reference.bin'))
        migration.to_file(migration_file)

        reference_file = Path(os.path.join(manifest.migration_folder, 'migration_gravity_model_reference.bin'))
        self.compare_migration_file_to_reference(migration_file, reference_file, exact_compare=False)

    def test_from_csv(self):
        temp = {'source': [1, 2, 5],
                'destination': [2, 3, 4],
                'rate': [0.1, 0.2, 0.3]}

        csv_file = Path(os.path.join(manifest.output_folder, "test_migration.csv"))
        pd.DataFrame.from_dict(temp).to_csv(csv_file, index=False)
        migration = from_csv(csv_file, id_ref="testing")

        migration_file = os.path.join(manifest.output_folder, "test_migration.bin")
        migration.to_file(migration_file)
        migration_from_bin = from_file(migration_file)

        for source, destination, rate in zip(temp['source'], temp['destination'], temp['rate']):
            self.assertEqual(migration[source][destination], rate)
            self.assertEqual(migration_from_bin[source][destination], rate)

    def test_from_csv_empty_file(self):
        with self.assertRaises(AssertionError):
            from_csv(Path(os.path.join(manifest.migration_folder, "test_migration_without_content.csv")), id_ref="testing")

    def compare_migration_file_to_reference(self, migration_file, migration_reference_file, exact_compare=True):
        self.assertTrue(migration_file.is_file())
        self.assertTrue(migration_reference_file.is_file())
        f = io.StringIO()
        with redirect_stdout(f):
            to_csv(migration_file)
        migration_rate = f.getvalue().split("\n")
        f = io.StringIO()
        with redirect_stdout(f):
            to_csv(migration_reference_file)
        migration_rate_reference = f.getvalue().split("\n")
        if exact_compare:
            self.assertListEqual(migration_rate, migration_rate_reference)
        else:
            # create numpy array [[src, dst, rate]], first and last row does not contain numbers
            migration_rate_from_file = np.array(
                [[float(i) for i in r.split(",")] for r in migration_rate[1:-1]])
            reference_rate_from_file = np.array(
                [[float(i) for i in r.split(",")] for r in migration_rate_reference[1:-1]])

            msg = "The migration rates calculated locally and by the webservice are not equal."
            np.testing.assert_array_almost_equal(migration_rate_from_file, reference_rate_from_file,
                                                 decimal=6, err_msg=msg)

        # compare .json file
        migration_json_file = migration_file.parent / (migration_file.name + '.json')
        reference_json_file = migration_reference_file.parent / (migration_reference_file.name + '.json')

        self.assertTrue(migration_json_file.is_file())
        self.assertTrue(reference_json_file.is_file())
        with migration_json_file.open('r') as migration_json_f:
            migration_json = json.load(migration_json_f)

        with reference_json_file.open('r') as reference_json_f:
            reference_json = json.load(reference_json_f)

        migration_json["Metadata"].pop("Author")
        migration_json["Metadata"].pop("DateCreated")

        reference_json["Metadata"].pop("Author")
        reference_json["Metadata"].pop("DateCreated")
        self.maxDiff = None
        self.assertDictEqual(migration_json, reference_json)


if __name__ == "__main__":
    unittest.main()
