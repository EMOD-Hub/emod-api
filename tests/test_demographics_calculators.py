import json
import unittest
from pathlib import Path

from emod_api.demographics.age_distribution import AgeDistribution

class DemographicsTest(unittest.TestCase):

    def test_template_equilibrium_age_dist_from_birth_and_mort_rates_regression(self):
        from emod_api.demographics.calculators import generate_equilibrium_age_distribution

        regression_file = Path(Path(__file__).parent, 'data', 'demographics', 'eq_age_dist.json')
        with open(regression_file, 'r') as f:
            expected = json.load(f)['AgeDistribution']

        distribution = generate_equilibrium_age_distribution(birth_rate=20, mortality_rate=10)

        self.assertTrue(isinstance(distribution, AgeDistribution))
        distribution_as_dict = distribution.to_dict()
        self.assertEqual(distribution_as_dict, expected)
