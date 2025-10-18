import unittest

class EmodapiMigrationImportTest(unittest.TestCase):
    def setUp(self) -> None:
        self.expected_items = None
        self.found_items = None
        pass

    def verify_expected_items_present(self, namespace):
        self.found_items = dir(namespace)
        for item in self.expected_items:
            self.assertIn(
                item,
                self.found_items
            )

    def tearDown(self) -> None:
        pass

    def test_migration_migration_import(self):
        self.expected_items = [
            'Layer',
            'Migration',
            'from_file',
            'examine_file',
            'from_params',
            'from_demog_and_param_gravity',
            'to_csv'
        ]
        import emod_api.migration.migration as migration
        self.verify_expected_items_present(namespace=migration)
        pass


if __name__ == '__main__':
    unittest.main()
