import unittest


class EmodapiConfigImportTest(unittest.TestCase):
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

    def test_config_import(self):
        self.expected_items = [
            'default_from_schema',
            'default_from_schema_no_validation'
        ]
        import emod_api.config as eac
        self.verify_expected_items_present(namespace=eac)
        pass

    def test_config_default_from_schema_import(self):
        self.expected_items = [
            'write_default_from_schema'
        ]
        import emod_api.config.default_from_schema as eacdfs
        self.verify_expected_items_present(eacdfs)
        pass
