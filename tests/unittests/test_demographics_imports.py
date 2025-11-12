import unittest


class EmodapiDemographicsImportTest(unittest.TestCase):
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

    def test_demog_demog_utils_import(self):
        self.expected_items = [
            'apply_to_defaults_or_nodes',
            'set_demog_distributions',
            'set_growing_demographics',
            'set_immune_mod',
            'set_risk_mod',
            'set_static_demographics'
        ]
        '''
            'distribution_types',
            'params',
        '''
        import emod_api.demographics.demographics_utils as eaddu
        self.verify_expected_items_present(namespace=eaddu)

    def test_demographics_class_api(self):
        self.expected_items = [
            'from_csv',
            'from_pop_raster_csv',
            'from_template_node',
            '_node_id_from_lat_lon_res',
            'to_file',
            'to_dict'  # from DemographicsBase
        ]
        from emod_api.demographics.demographics import Demographics
        self.verify_expected_items_present(namespace=Demographics)

    def test_demog_node_import(self):
        self.expected_items = [
            'basicNode',
            'get_xpix_ypix',
            'lat_lon_from_nodeid',
            'nodeid_from_lat_lon',
            'nodes_for_DTK',
            'xpix_ypix_from_lat_lon'
        ]
        import emod_api.demographics.node as eadn
        self.verify_expected_items_present(namespace=eadn)

    def test_demog_templates_import(self):
        self.expected_items = [
            'AgeStructureUNWPP', '_ConstantMortality', 'DefaultSusceptibilityDistribution',
            '_EquilibriumAgeDistFromBirthAndMortRates', 'EveryoneInitiallySusceptible', 'FullRisk', 'InitAgeUniform',
            'InitRiskUniform', 'InitSusceptConstant', 'MortalityRateByAge', 'MortalityStructureNigeriaDHS',
            'NoInitialPrevalence', 'NoRisk', 'SimpleSusceptibilityDistribution',
            '_set_age_complex', '_set_age_simple', '_set_init_prev', '_set_suscept_complex',
            '_set_suscept_simple'
        ]
        import emod_api.demographics.demographics_templates as eaddt
        self.verify_expected_items_present(namespace=eaddt)
