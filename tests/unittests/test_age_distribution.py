import unittest

from emod_api.demographics.age_distribution import AgeDistribution

import emod_api.demographics.demographic_exceptions as demog_ex


class TestAgeDistribution(unittest.TestCase):
    def setUp(self):
        self.ages = [0, 10, 20, 50, 100]
        self.fractions = [0.0, 0.2, 0.6, 0.9, 1.0]

        self.age_distribution = AgeDistribution(ages_years=self.ages, cumulative_population_fraction=self.fractions)

        self.age_dict = {
            'ResultScaleFactor': 365.0,
            'ResultValues': [0, 10, 20, 50, 100],
            'DistributionValues': [0.0, 0.2, 0.6, 0.9, 1.0]
        }

    def test_garden_path_works(self):
        self.age_distribution._validate(distribution_dict=self.age_distribution.to_dict(), source_is_dict=False)

    # Ensure proper exceptions are thrown when improper inputs are supplied via building with the constructor

    def test_constructor_validation_age_dimensionality_is_1d(self):
        ages = [[0, 10, 20, 50, 100], [2, 4, 6, 8, 10]]  # 2-d, not 1-d
        self.assertRaises(demog_ex.InvalidDataDimensionality,
                          AgeDistribution,
                          ages_years=ages, cumulative_population_fraction=self.fractions)

    def test_constructor_validation_fraction_dimensionality_is_1d(self):
        fractions = [[0.1, 0.2, 0.3, 0.4, 0.5], [0.6, 0.7, 0.8, 0.9, 1.0]]  # 2-d, not 1-d
        self.assertRaises(demog_ex.InvalidDataDimensionality,
                          AgeDistribution,
                          ages_years=self.ages, cumulative_population_fraction=fractions)

    def test_constructor_validation_age_length_equals_fraction_length(self):
        ages = self.ages + [999999]  # ages list is now one longer than fraction list
        self.assertRaises(demog_ex.InvalidDataDimensionLength,
                          AgeDistribution,
                          ages_years=ages, cumulative_population_fraction=self.fractions)

    def test_constructor_validation_age_range(self):
        self.ages[0] = -1  # invalid age, -1 year
        self.assertRaises(demog_ex.AgeOutOfRangeException,
                          AgeDistribution,
                          ages_years=self.ages, cumulative_population_fraction=self.fractions)

        self.ages[0] = 0
        self.ages[-1] = 2000  # invalid age, 2000 years
        self.assertRaises(demog_ex.AgeOutOfRangeException,
                          AgeDistribution,
                          ages_years=self.ages, cumulative_population_fraction=self.fractions)

    def test_constructor_validation_fraction_range(self):
        self.fractions[0] = -0.1  # invalid cumulative fraction, -0.1
        self.assertRaises(demog_ex.DistributionOutOfRangeException,
                          AgeDistribution,
                          ages_years=self.ages, cumulative_population_fraction=self.fractions)

        self.fractions[0] = 0
        self.fractions[-1] = 100  # invalid cumulative fraction, 100
        self.assertRaises(demog_ex.DistributionOutOfRangeException,
                          AgeDistribution,
                          ages_years=self.ages, cumulative_population_fraction=self.fractions)

    def test_constructor_validation_age_ascending(self):
        self.ages[-1] = self.ages[-2] / 2  # non-monotonically-increasing age
        self.assertRaises(demog_ex.NonMonotonicAgeException,
                          AgeDistribution,
                          ages_years=self.ages, cumulative_population_fraction=self.fractions)

    def test_constructor_validation_fraction_ascending(self):
        self.fractions[-1] = self.fractions[-2] / 2
        self.assertRaises(demog_ex.NonMonotonicDistributionException,
                          AgeDistribution,
                          ages_years=self.ages, cumulative_population_fraction=self.fractions)

    # ensure proper exceptions are thrown when improper inputs are supplied via building with .from_dict()
    # all of these use explicit times

    def test_from_dict_validation_invalid_result_scale_factor(self):
        self.age_dict['ResultScaleFactor'] = 12345.6789
        self.assertRaises(demog_ex.InvalidFixedValueException,
                          AgeDistribution.from_dict, distribution_dict=self.age_dict)

    def test_from_dict_validation_age_dimensionality_is_1d(self):
        self.age_dict['ResultValues'] = [self.ages, self.ages]  # no longer 1-d age
        self.assertRaises(demog_ex.InvalidDataDimensionality,
                          AgeDistribution.from_dict, distribution_dict=self.age_dict)

    def test_from_dict_validation_fraction_dimensionality_is_1d(self):
        self.age_dict['DistributionValues'] = [self.fractions, self.fractions]  # no longer 1-d age
        self.assertRaises(demog_ex.InvalidDataDimensionality,
                          AgeDistribution.from_dict, distribution_dict=self.age_dict)

    def test_from_dict_validation_age_range(self):
        self.age_dict['ResultValues'][0] = -1  # invalid age -1
        self.assertRaises(demog_ex.AgeOutOfRangeException,
                          AgeDistribution.from_dict, distribution_dict=self.age_dict)

        self.age_dict['ResultValues'][0] = 0
        self.age_dict['ResultValues'][-1] = 2000  # invalid age -1
        self.assertRaises(demog_ex.AgeOutOfRangeException,
                          AgeDistribution.from_dict, distribution_dict=self.age_dict)

    def test_from_dict_validation_fraction_range(self):
        self.age_dict['DistributionValues'][0] = -1  # invalid cumulative pop fraction
        self.assertRaises(demog_ex.DistributionOutOfRangeException,
                          AgeDistribution.from_dict, distribution_dict=self.age_dict)

        self.age_dict['DistributionValues'][0] = 0
        self.age_dict['DistributionValues'][0] = 100  # invalid cumulative pop fraction
        self.assertRaises(demog_ex.DistributionOutOfRangeException,
                          AgeDistribution.from_dict, distribution_dict=self.age_dict)

    def test_from_dict_validation_age_ascending(self):
        self.ages[-1] = self.ages[-2] / 2  # non-monotonically-increasing age
        self.age_dict['ResultValues'] = self.ages  # not ascending now
        self.assertRaises(demog_ex.NonMonotonicAgeException,
                          AgeDistribution.from_dict, distribution_dict=self.age_dict)

    def test_from_dict_validation_fraction_ascending(self):
        self.fractions[-1] = self.fractions[-2] / 2  # non-monotonically-increasing age
        self.age_dict['DistributionValues'] = self.fractions  # not ascending now
        self.assertRaises(demog_ex.NonMonotonicDistributionException,
                          AgeDistribution.from_dict, distribution_dict=self.age_dict)

    def test_from_dict_and_to_dict_are_inverses(self):
        test_dict = AgeDistribution.from_dict(distribution_dict=self.age_dict).to_dict(validate=False)
        self.assertEqual(self.age_dict, test_dict)
