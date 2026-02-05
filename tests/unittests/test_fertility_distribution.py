from emod_api.demographics.fertility_distribution import FertilityDistribution

import emod_api.demographics.demographic_exceptions as demog_ex


class TestFertilityDistribution():
    def setUp(self):
        self.ages = [15, 20, 42, 44.99]
        self.times = [1950, 1970, 1990]
        self.rates = [[100.0, 75.0, 50.0],    # These are fertility rates at age 15, the three time points above
                      [10.0, 5.0, 1.0],       # These are fertility rates for age 20
                      [5.0, 3.0, 1.0],        # These are fertility rates for age 42
                      [30.0, 20.0, 10.0]]     # These are fertility rates for age 44.99
        self.md_explicit_times = FertilityDistribution(ages_years=self.ages,
                                                       calendar_years=self.times,
                                                       pregnancy_rate_matrix=self.rates)

        self.fertility_dict = {
            'AxisNames': ['age', 'year'],
            'AxisScaleFactors': [365, 1],
            'PopulationGroups': [
                [15, 20, 42, 44.99],
                [1950, 1970, 1990]
            ],
            'ResultScaleFactor': 1 / 365.0 / 1000,
            'ResultUnits': 'annual birth rate per 1000 women',
            'ResultValues': [
                [100.0, 75.0, 50.0],
                [10.0, 5.0, 1.0],
                [5.0, 3.0, 1.0],
                [30.0, 20.0, 10.0]
            ]
        }

    def test_garden_path_works(self):
        FertilityDistribution._validate(distribution_dict=self.md_explicit_times.to_dict(), source_is_dict=False)

    # Ensure proper exceptions are thrown when improper inputs are supplied via building with the constructor

    def test_constructor_validation_age_dimension_of_data(self):
        self.ages = self.ages + [50]  # no longer matches self.rates dimensionality
        self.assertRaises(demog_ex.InvalidDataDimensionDim0Exception,
                          FertilityDistribution,
                          ages_years=self.ages, calendar_years=self.times, pregnancy_rate_matrix=self.rates)

    def test_constructor_validation_time_dimension_of_data(self):
        self.times = self.times[:-2]  # no longer matches self.rates dimensionality
        self.assertRaises(demog_ex.InvalidDataDimensionDim1Exception,
                          FertilityDistribution,
                          ages_years=self.ages, calendar_years=self.times, pregnancy_rate_matrix=self.rates)

    def test_constructor_validation_age_range(self):
        self.ages[0] = -1  # invalid age, -1 year
        self.assertRaises(demog_ex.AgeOutOfRangeException,
                          FertilityDistribution,
                          ages_years=self.ages, calendar_years=self.times, pregnancy_rate_matrix=self.rates)

        self.ages[0] = 15
        self.ages[-1] = 201  # invalid age, 200 years
        self.assertRaises(demog_ex.AgeOutOfRangeException,
                          FertilityDistribution,
                          ages_years=self.ages, calendar_years=self.times, pregnancy_rate_matrix=self.rates)

    def test_constructor_validation_time_range(self):
        self.times[0] = 1  # invalid calendar year, 1
        self.assertRaises(demog_ex.TimeOutOfRangeException,
                          FertilityDistribution,
                          ages_years=self.ages, calendar_years=self.times, pregnancy_rate_matrix=self.rates)

        self.times[0] = 1950
        self.times[-1] = 3000  # invalid calendar year, 3000
        self.assertRaises(demog_ex.TimeOutOfRangeException,
                          FertilityDistribution,
                          ages_years=self.ages, calendar_years=self.times, pregnancy_rate_matrix=self.rates)

    def test_constructor_validation_age_ascending(self):
        self.ages[-1] = self.ages[-2] / 2  # non-monotonically-increasing age
        self.assertRaises(demog_ex.NonMonotonicAgeException,
                          FertilityDistribution,
                          ages_years=self.ages, calendar_years=self.times, pregnancy_rate_matrix=self.rates)

    def test_constructor_validation_time_ascending(self):
        self.times[-1] = self.times[-2] - 1  # non-monotonically-increasing age  # non-monotonically-increasing time/calendar year
        self.assertRaises(demog_ex.NonMonotonicTimeException,
                          FertilityDistribution,
                          ages_years=self.ages, calendar_years=self.times, pregnancy_rate_matrix=self.rates)

    # ensure proper exceptions are thrown when improper inputs are supplied via building with .from_dict()
    # all of these use explicit times

    def test_from_dict_validation_invalid_axis_names(self):
        self.fertility_dict['AxisNames'] = ['not', 'valid']
        self.assertRaises(demog_ex.InvalidFixedValueException,
                          FertilityDistribution.from_dict, distribution_dict=self.fertility_dict)

    def test_from_dict_validation_invalid_axis_scale_factors(self):
        self.fertility_dict['AxisScaleFactors'] = [-1, -1]
        self.assertRaises(demog_ex.InvalidFixedValueException,
                          FertilityDistribution.from_dict, distribution_dict=self.fertility_dict)

    def test_from_dict_validation_invalid_result_scale_factor(self):
        self.fertility_dict['ResultScaleFactor'] = 12345.6789
        self.assertRaises(demog_ex.InvalidFixedValueException,
                          FertilityDistribution.from_dict, distribution_dict=self.fertility_dict)

    def test_from_dict_validation_invalid_result_units(self):
        self.fertility_dict['ResultUnits'] = 'This is a test of the emergency broadcast system. This is only a test.'
        self.assertRaises(demog_ex.InvalidFixedValueException,
                          FertilityDistribution.from_dict, distribution_dict=self.fertility_dict)

    def test_from_dict_invalid_population_group_length(self):
        self.fertility_dict['PopulationGroups'] = [1, 2, 3, 4, 5, 6, 8, 9, 10]
        self.assertRaises(demog_ex.InvalidPopulationGroupLengthException,
                          FertilityDistribution.from_dict, distribution_dict=self.fertility_dict)

    def test_from_dict_validation_age_dimension_of_data(self):
        self.fertility_dict['PopulationGroups'][0] = [15, 20, 25, 30, 35]  # no longer matches fertility rate dimensionality
        self.assertRaises(demog_ex.InvalidDataDimensionDim0Exception,
                          FertilityDistribution.from_dict, distribution_dict=self.fertility_dict)

    def test_from_dict_validation_time_dimension_of_data(self):
        self.fertility_dict['PopulationGroups'][1] = [1950, 1970]  # no longer matches fertility rate dimensionality
        self.assertRaises(demog_ex.InvalidDataDimensionDim1Exception,
                          FertilityDistribution.from_dict, distribution_dict=self.fertility_dict)

    def test_from_dict_validation_age_range(self):
        self.fertility_dict['PopulationGroups'][0][0] = -1  # invalid age -1
        self.assertRaises(demog_ex.AgeOutOfRangeException,
                          FertilityDistribution.from_dict, distribution_dict=self.fertility_dict)

        self.fertility_dict['PopulationGroups'][0][0] = 201  # invalid age 201
        self.assertRaises(demog_ex.AgeOutOfRangeException,
                          FertilityDistribution.from_dict, distribution_dict=self.fertility_dict)

    def test_from_dict_validation_time_range(self):
        self.fertility_dict['PopulationGroups'][1][0] = 1  # invalid time, calendar year 1
        self.assertRaises(demog_ex.TimeOutOfRangeException,
                          FertilityDistribution.from_dict, distribution_dict=self.fertility_dict)

        self.fertility_dict['PopulationGroups'][1][-1] = 3000  # invalid time, calendar year 3000
        self.assertRaises(demog_ex.TimeOutOfRangeException,
                          FertilityDistribution.from_dict, distribution_dict=self.fertility_dict)

    def test_from_dict_validation_age_ascending(self):
        self.fertility_dict['PopulationGroups'][0][-1] = 15  # not ascending now
        self.assertRaises(demog_ex.NonMonotonicAgeException,
                          FertilityDistribution.from_dict, distribution_dict=self.fertility_dict)

    def test_from_dict_validation_time_ascending(self):
        self.fertility_dict['PopulationGroups'][1][-1] = 1910  # not ascending now
        self.assertRaises(demog_ex.NonMonotonicTimeException,
                          FertilityDistribution.from_dict, distribution_dict=self.fertility_dict)

    def test_from_dict_and_to_dict_are_inverses(self):
        test_dict = FertilityDistribution.from_dict(distribution_dict=self.fertility_dict).to_dict(validate=False)
        self.assertEqual(self.fertility_dict, test_dict)

    def test_from_dict_validation_0d_rates_should_fail(self):
        self.assertRaises(
            demog_ex.InvalidDataDimensionality,
            FertilityDistribution,
            ages_years=self.ages,
            calendar_years=self.times,
            pregnancy_rate_matrix=0.5  # 0-dimensional!
        )
