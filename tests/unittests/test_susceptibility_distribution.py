import unittest

from emod_api.demographics.susceptibility_distribution import SusceptibilityDistribution

import emod_api.demographics.demographic_exceptions as demog_ex


class TestSusceptibilityDistribution(unittest.TestCase):
    def setUp(self):
        self.ages = [0, 10, 20, 50, 100]  # ages in years for object-form
        self.fractions = [0.9, 0.7, 0.3, 0.5, 0.8]

        self.susceptibility_distribution = SusceptibilityDistribution(ages_years=self.ages,
                                                                      susceptible_fraction=self.fractions)

        self.susceptibility_dict = {
            'ResultScaleFactor': 1,
            'DistributionValues': [0, 3650, 7300, 18250, 36500],  # ages in days for dict-form
            'ResultValues': [0.9, 0.7, 0.3, 0.5, 0.8]  # susceptible fraction
        }

    def test_garden_path_works(self):
        self.susceptibility_distribution._validate(distribution_dict=self.susceptibility_distribution.to_dict(),
                                                   source_is_dict=False)

    # Ensure proper exceptions are thrown when improper inputs are supplied via building with the constructor

    def test_constructor_validation_age_dimensionality_is_1d(self):
        ages = [self.ages, self.ages]  # 2-d, not 1-d
        self.assertRaises(demog_ex.InvalidDataDimensionality,
                          SusceptibilityDistribution,
                          ages_years=ages, susceptible_fraction=self.fractions)

    def test_constructor_validation_fraction_dimensionality_is_1d(self):
        fractions = [self.fractions, self.fractions]  # 2-d, not 1-d
        self.assertRaises(demog_ex.InvalidDataDimensionality,
                          SusceptibilityDistribution,
                          ages_years=self.ages, susceptible_fraction=fractions)

    def test_constructor_validation_age_length_equals_fraction_length(self):
        ages = self.ages + [999999]  # ages list is now one longer than fraction list
        self.assertRaises(demog_ex.InvalidDataDimensionLength,
                          SusceptibilityDistribution,
                          ages_years=ages, susceptible_fraction=self.fractions)

    def test_constructor_validation_age_range(self):
        self.ages[0] = -1  # invalid age, -1 year
        self.assertRaises(demog_ex.AgeOutOfRangeException,
                          SusceptibilityDistribution,
                          ages_years=self.ages, susceptible_fraction=self.fractions)

        self.ages[0] = 0
        self.ages[-1] = 2000  # invalid age, 2000 years
        self.assertRaises(demog_ex.AgeOutOfRangeException,
                          SusceptibilityDistribution,
                          ages_years=self.ages, susceptible_fraction=self.fractions)

    def test_constructor_validation_fraction_range(self):
        self.fractions[0] = -0.1  # invalid susceptible fraction, -0.1
        self.assertRaises(demog_ex.DistributionOutOfRangeException,
                          SusceptibilityDistribution,
                          ages_years=self.ages, susceptible_fraction=self.fractions)

        self.fractions[0] = 0
        self.fractions[-1] = 100  # invalid susceptible fraction, 100
        self.assertRaises(demog_ex.DistributionOutOfRangeException,
                          SusceptibilityDistribution,
                          ages_years=self.ages, susceptible_fraction=self.fractions)

    def test_constructor_validation_age_ascending(self):
        self.ages[-1] = self.ages[-2] / 2  # non-monotonically-increasing age
        self.assertRaises(demog_ex.NonMonotonicAgeException,
                          SusceptibilityDistribution,
                          ages_years=self.ages, susceptible_fraction=self.fractions)

    # ensure proper exceptions are thrown when improper inputs are supplied via building with .from_dict()
    # all of these use explicit times

    def test_from_dict_validation_invalid_result_scale_factor(self):
        self.susceptibility_dict['ResultScaleFactor'] = 12345.6789
        self.assertRaises(demog_ex.InvalidFixedValueException,
                          SusceptibilityDistribution.from_dict, distribution_dict=self.susceptibility_dict)

    def test_from_dict_validation_age_dimensionality_is_1d(self):
        self.susceptibility_dict['DistributionValues'] = [self.ages, self.ages]  # no longer 1-d age
        self.assertRaises(demog_ex.InvalidDataDimensionality,
                          SusceptibilityDistribution.from_dict, distribution_dict=self.susceptibility_dict)

    def test_from_dict_validation_fraction_dimensionality_is_1d(self):
        self.susceptibility_dict['ResultValues'] = [self.fractions, self.fractions]  # no longer 1-d
        self.assertRaises(demog_ex.InvalidDataDimensionality,
                          SusceptibilityDistribution.from_dict, distribution_dict=self.susceptibility_dict)

    def test_from_dict_validation_age_range(self):
        self.susceptibility_dict['DistributionValues'][0] = -1  # invalid age -1 day
        self.assertRaises(demog_ex.AgeOutOfRangeException,
                          SusceptibilityDistribution.from_dict, distribution_dict=self.susceptibility_dict)

        self.susceptibility_dict['DistributionValues'][0] = 0
        self.susceptibility_dict['DistributionValues'][-1] = 2000 * 365  # invalid age 2000 years (in days)
        self.assertRaises(demog_ex.AgeOutOfRangeException,
                          SusceptibilityDistribution.from_dict, distribution_dict=self.susceptibility_dict)

    def test_from_dict_validation_fraction_range(self):
        self.susceptibility_dict['ResultValues'][0] = -1  # invalid susceptible fraction
        self.assertRaises(demog_ex.DistributionOutOfRangeException,
                          SusceptibilityDistribution.from_dict, distribution_dict=self.susceptibility_dict)

        self.susceptibility_dict['ResultValues'][0] = 0
        self.susceptibility_dict['ResultValues'][0] = 100  # invalid susceptible fraction
        self.assertRaises(demog_ex.DistributionOutOfRangeException,
                          SusceptibilityDistribution.from_dict, distribution_dict=self.susceptibility_dict)

    def test_from_dict_validation_age_ascending(self):
        self.ages[-1] = self.ages[-2] / 2  # non-monotonically-increasing age
        self.susceptibility_dict['DistributionValues'] = self.ages  # not ascending now
        self.assertRaises(demog_ex.NonMonotonicAgeException,
                          SusceptibilityDistribution.from_dict, distribution_dict=self.susceptibility_dict)

    def test_from_dict_and_to_dict_are_inverses(self):
        test_dict = SusceptibilityDistribution.from_dict(distribution_dict=self.susceptibility_dict).to_dict(validate=False)
        self.assertEqual(self.susceptibility_dict, test_dict)
