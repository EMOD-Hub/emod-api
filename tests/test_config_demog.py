import pytest
import emod_api.demographics.Demographics as Demographics
import emod_api.demographics.PreDefinedDistributions as Distributions

from emod_api.config import default_from_schema_no_validation as dfs
from tests import manifest


class TestDemoConfig():
    @pytest.fixture(autouse=True)
    # Set-up and tear-down for each test
    def run_every_test(self, request) -> None:
        self.reset_config()

    def get_config_as_object(self):
        schema_name = manifest.generic_schema_path
        config_obj = dfs.get_default_config_from_schema(schema_name, as_rod=True)
        return config_obj

    def reset_config(self):
        self.config = self.get_config_as_object()

    # Tests that if overdispersion is set, Enable_Infection_Rate_Overdispersion is True
    def test_age_dependent_transmission_config(self):
        for index in range(2):
            demog = Demographics.from_template_node()
            demog.SetDefaultProperties()
            if index:
                demog.SetOverdispersion(0.75)
            assert(len(demog.implicits)==(5 + index))
            demog.implicits[-1](self.config)
            if not index:
                assert(self.config.parameters.Enable_Infection_Rate_Overdispersion==0)
            else:
                assert(self.config.parameters.Enable_Infection_Rate_Overdispersion==1)

    def test_set_birth_rate_config(self):
        demog = Demographics.from_template_node()
        self.config.parameters.Enable_Birth = 0  # since it is 1 by default
        demog.SetBirthRate(0.7)
        assert(len(demog.implicits)==2)
        demog.implicits[-1](self.config)
        assert(self.config.parameters.Birth_Rate_Dependence=="POPULATION_DEP_RATE")

    def test_set_mortality_rate_config(self):
        for index in range(2):
            demog = Demographics.from_template_node()
            if index:
                demog.SetMortalityRate(0.75)
            demog.implicits[-1](self.config)

    def test_set_mortality_distribution(self):
        demog = Demographics.from_template_node()

        mortality_distribution = Distributions.SEAsia_Diag
        demog.SetMortalityDistribution(mortality_distribution)
        assert(len(demog.implicits)==2)
        demog.implicits[-1](self.config)
        demog.implicits[-2](self.config)
        assert(self.config.parameters.Death_Rate_Dependence=="NONDISEASE_MORTALITY_BY_AGE_AND_GENDER")

    def test_set_age_distribution(self):
        demog = Demographics.from_template_node()
        assert(self.config.parameters.Age_Initialization_Distribution_Type=="DISTRIBUTION_OFF")
        age_distribution = Distributions.SEAsia_Diag
        demog.SetAgeDistribution(age_distribution)
        assert(len(demog.implicits)==2)
        demog.implicits[-1](self.config)
        assert(self.config.parameters.Age_Initialization_Distribution_Type=="DISTRIBUTION_COMPLEX")
