import unittest

from emod_api.config.default_from_schema_no_validation import get_default_config_from_schema
from emod_api.demographics.demographics import Demographics

from tests import manifest


class DemoConfigTest(unittest.TestCase):
    # This test suite simply verifies that implicit functions from demographics objects are applied to the config
    # appropriately. Further details, like the contents of the distributions being set (and covering all distribution
    # use cases e.g. mortality) are covered in test_self.demographics.py .

    def setUp(self) -> None:
        print(f"\n{self._testMethodName} started...")
        self.config = self.reset_config()
        self.demographics = Demographics(nodes=[])

    def reset_config(self):
        schema_name = manifest.generic_schema_path
        config_obj = get_default_config_from_schema(schema_name, as_rod=True)
        return config_obj

    def test_demographic_implicits_are_applied(self):
        # simple case to ensure a implicit functions actually apply to configs. test_self.demographics.py ensures the
        # RIGHT implicit functions are set.
        from emod_api.demographics.implicit_functions import _set_age_simple, _set_suscept_complex
        from emod_api.demographics.susceptibility_distribution import SusceptibilityDistribution
        from emod_api.utils.distributions.exponential_distribution import ExponentialDistribution

        self.assertEqual(self.config.parameters.Age_Initialization_Distribution_Type, "DISTRIBUTION_OFF")
        self.assertEqual(self.config.parameters.Susceptibility_Initialization_Distribution_Type, "DISTRIBUTION_OFF")

        # setting up the test
        age_distribution = ExponentialDistribution(mean=0.0001)
        self.demographics.set_age_distribution(distribution=age_distribution)
        susceptibility_distribution = SusceptibilityDistribution(ages_years=[0, 10, 20],
                                                                 susceptible_fraction=[0.5, 0.25, 0.125])
        self.demographics.set_susceptibility_distribution(distribution=susceptibility_distribution)

        # ensure we have the implicits we expect, then apply them.
        self.assertEqual(len(self.demographics.implicits), 2)
        self.assertIn(_set_age_simple, self.demographics.implicits)
        self.assertIn(_set_suscept_complex, self.demographics.implicits)
        for implicit in self.demographics.implicits:
            implicit(self.config)

        # Ensure we have the right config items set now.
        self.assertEqual(self.config.parameters.Age_Initialization_Distribution_Type, "DISTRIBUTION_SIMPLE")
        self.assertEqual(self.config.parameters.Susceptibility_Initialization_Distribution_Type, "DISTRIBUTION_COMPLEX")


if __name__ == '__main__':
    unittest.main()
