import unittest


class EmodapiDemographicsImportTest(unittest.TestCase):
    def setUp(self) -> None:
        self.expected_items = None
        self.found_items = None

    def verify_expected_items_present(self, namespace):
        self.found_items = dir(namespace)
        for item in self.expected_items:
            self.assertIn(
                item,
                self.found_items
            )

    def tearDown(self) -> None:
        pass


    def test_demographics_class_api(self):
        self.expected_items = [
            'from_csv',
            'from_pop_raster_csv',
            'from_template_node',
            '_node_id_from_lat_lon_res',
            'to_file',
            # from DemographicsBase below here
            'to_dict',
            'set_birth_rate',
            'set_age_distribution',
            'set_susceptibility_distribution',
            'set_prevalence_distribution',
            'set_migration_heterogeneity_distribution',
            'set_mortality_distribution',
            'add_individual_property',

        ]
        from emod_api.demographics.demographics import Demographics
        self.verify_expected_items_present(namespace=Demographics)

    def test_demog_node_import(self):
        self.expected_items = [
            'get_xpix_ypix',
            'lat_lon_from_nodeid',
            'nodeid_from_lat_lon',
            'xpix_ypix_from_lat_lon'
        ]
        import emod_api.demographics.node as eadn
        self.verify_expected_items_present(namespace=eadn)
