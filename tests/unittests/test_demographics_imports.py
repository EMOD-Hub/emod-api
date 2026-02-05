

class EmodapiDemographicsImportTest():
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
        pass

    def test_demog_demog_import(self):
        self.expected_items = [
            'Demographics',
            'Node',
            'from_csv',
            'from_file',
            'from_params',
            'get_node_ids_from_file',
            'get_node_pops_from_params',
            '_node_id_from_lat_lon_res'
        ]
        import emod_api.demographics.Demographics as eaddf
        self.verify_expected_items_present(namespace=eaddf)
        pass

    def test_demog_node_import(self):
        self.expected_items = [
            'basicNode',
            'get_xpix_ypix',
            'lat_lon_from_nodeid',
            'nodeid_from_lat_lon',
            'nodes_for_DTK',
            'xpix_ypix_from_lat_lon'
        ]
        import emod_api.demographics.Node as eadn
        self.verify_expected_items_present(namespace=eadn)
        pass

    def test_demog_templates_import(self):
        self.expected_items = [
            'AgeStructureUNWPP', '_ConstantMortality', 'DefaultSusceptibilityDistribution',
            '_EquilibriumAgeDistFromBirthAndMortRates', 'EveryoneInitiallySusceptible', 'FullRisk', 'InitAgeUniform',
            'InitRiskUniform', 'InitSusceptConstant', 'MortalityRateByAge', 'MortalityStructureNigeriaDHS',
            'NoInitialPrevalence', 'NoRisk', 'SimpleSusceptibilityDistribution',
            '_set_age_complex', '_set_age_simple', '_set_init_prev', '_set_suscept_complex',
            '_set_suscept_simple'
        ]
        import emod_api.demographics.DemographicsTemplates as eaddt
        self.verify_expected_items_present(namespace=eaddt)
        pass
