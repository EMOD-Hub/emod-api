import unittest
import emod_api.demographics.Demographics as Demographics
import json
import emod_api.demographics.PreDefinedDistributions as Distributions

from emod_api.config import default_from_schema_no_validation as dfs
from tests import manifest

class DemoConfigTest(unittest.TestCase):
    def setUp(self) -> None:
        print(f"\n{self._testMethodName} started...")
        self.reset_config()

    def get_config_as_object(self):
        schema_name = manifest.generic_schema_path
        config_obj = dfs.get_default_config_from_schema(schema_name, as_rod=True)
        return config_obj

    def reset_config(self):
        self.config = self.get_config_as_object()

    # Tests that if property is not in whitelist, then whitelist is disabled in config
    def test_add_individual_property_config(self):
        for index, property in enumerate(["Risk", "Color"]):
            demog = Demographics.from_template_node()
            demog.SetDefaultProperties()
            if index > 0:
                values = ["Red", "Green"]
            else:
                values = ["high", "low"]
            demog.AddIndividualPropertyAndHINT(property, values)
        
            self.assertEqual(len(demog.implicits), 5+index)
            demog.implicits[-1](self.config)
            if index == 0:
                self.assertTrue("Disable_IP_Whitelist" not in self.config.parameters)
            else:
                self.assertEqual(self.config.parameters.Disable_IP_Whitelist, 1)
            self.reset_config()

    # Tests that if transmission matrix is defined, Enable_Heterogeneous_Intranode_Transmission 
    # is enabled 
    def test_add_ind_property_transmission_matrix(self):
        i = 0 # can't unpack None with enumerate()
        for tranmission_matrix in [None, [[1, 2, 3], [4, 5, 6], [7, 8, 9]]]:
            demog = Demographics.from_template_node()
            demog.SetDefaultProperties()
            demog.AddIndividualPropertyAndHINT("Risk", ["High", "Low"], TransmissionMatrix = tranmission_matrix)
            self.assertEqual(len(demog.implicits), 5+i)
            demog.implicits[-1](self.config)
            if i == 0:
                self.assertEqual(self.config.parameters.Enable_Heterogeneous_Intranode_Transmission, 0)
            else:
                self.assertEqual(self.config.parameters.Enable_Heterogeneous_Intranode_Transmission, 1)
            i=+1
    
    # Tests that if overdispersion is set, Enable_Infection_Rate_Overdispersion is True
    def test_age_dependent_transmission_config(self):
        for index in range(2):
            demog = Demographics.from_template_node()
            demog.SetDefaultProperties()
            if index:
                demog.SetOverdispersion(0.75)
            self.assertEqual(len(demog.implicits), 5+index)
            demog.implicits[-1](self.config)
            if not index:
                self.assertEqual(self.config.parameters.Enable_Infection_Rate_Overdispersion, 0)
            else:
                self.assertEqual(self.config.parameters.Enable_Infection_Rate_Overdispersion, 1)

    def test_set_birth_rate_config(self):
        demog = Demographics.from_template_node()
        self.config.parameters.Enable_Birth = 0 # since it is 1 by default
        demog.SetBirthRate(0.7)
        self.assertEqual(len(demog.implicits), 2)
        demog.implicits[-1](self.config)
        #self.assertEqual(self.config.parameters.Enable_Birth, 1) # This should get set also during finalize
        self.assertEqual(self.config.parameters.Birth_Rate_Dependence, "POPULATION_DEP_RATE")

    def test_set_mortality_rate_config(self):
        for index in range(2):
            demog = Demographics.from_template_node()
            if index:
                demog.SetMortalityRate(0.75)
            # self.assertEqual(len(demog.implicits), 1+index) # why are there 3 implicits?
            demog.implicits[-1](self.config)

    def test_set_mortality_distribution(self):
        demog = Demographics.from_template_node()
        self.config.parameters.Death_Rate_Dependence = "NONDISEASE_MORTALITY_BY_YEAR_AND_AGE_FOR_EACH_GENDER"

        mortality_distribution = Distributions.SEAsia_Diag
        demog.SetMortalityDistribution(mortality_distribution)
        self.assertEqual(len(demog.implicits), 2)
        demog.implicits[-1](self.config)
        demog.implicits[-2](self.config)
        self.assertEqual(self.config.parameters.Death_Rate_Dependence, "NONDISEASE_MORTALITY_BY_AGE_AND_GENDER")

    def test_set_age_distribution(self):
        demog = Demographics.from_template_node()
        self.assertEqual(self.config.parameters.Age_Initialization_Distribution_Type, "DISTRIBUTION_OFF")
        age_distribution = Distributions.SEAsia_Diag
        demog.SetAgeDistribution(age_distribution)
        self.assertEqual(len(demog.implicits), 2)
        demog.implicits[-1](self.config)
        self.assertEqual(self.config.parameters.Age_Initialization_Distribution_Type, "DISTRIBUTION_COMPLEX")
