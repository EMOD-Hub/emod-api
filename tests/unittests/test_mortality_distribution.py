from emod_api.demographics.mortality_distribution import MortalityDistribution

import emod_api.demographics.demographic_exceptions as demog_ex


class TestMortalityDistribution():
    def setUp(self):
        self.ages = [0, 10, 20, 50, 100]
        self.explicit_times = [1950, 1970, 1990]
        self.rates = [[100.0, 75.0, 50.0],    # These are mortality rates at age 0, the three time points above
                      [10.0, 5.0, 1.0],       # These are mortality rates for age 10
                      [5.0, 3.0, 1.0],        # These are mortality rates for age 20
                      [30.0, 20.0, 10.0],     # These are mortality rates for age 50
                      [300.0, 250.0, 200.0]]  # These are mortality rates for age 100
        self.md_explicit_times = MortalityDistribution(ages_years=self.ages,
                                                       calendar_years=self.explicit_times,
                                                       mortality_rate_matrix=self.rates)
        self.rates_time_independent_2d = [[100.0],  # mortality rate at age 0, for all time
                                          [10.0],   # mortality rate at age 10, for all time
                                          [5.0],    # mortality rate at age 20, for all time
                                          [30.0],   # mortality rate at age 50, for all time
                                          [300.0]]  # mortality rate at age 100, for all time
        self.md_implicit_time = MortalityDistribution(ages_years=self.ages,
                                                      mortality_rate_matrix=self.rates_time_independent_2d)

        self.rates_time_independent_1d = [100.0, 10.0, 5.0, 30.0, 300.0]
        self.md_implicit_time_1d_rates = MortalityDistribution(ages_years=self.ages,
                                                               mortality_rate_matrix=self.rates_time_independent_1d)

        self.mortality_dict = {
            'AxisNames': ['age', 'year'],
            'AxisScaleFactors': [365, 1],
            'PopulationGroups': [
                [0, 10, 20, 50, 100],
                [1950, 1970, 1990]
            ],
            'ResultScaleFactor': 1 / 365.0,
            'ResultUnits': 'annual death rate for an individual',
            'ResultValues': [
                [100.0, 75.0, 50.0],
                [10.0, 5.0, 1.0],
                [5.0, 3.0, 1.0],
                [30.0, 20.0, 10.0],
                [300.0, 250.0, 200.0]
            ]
        }

    def test_explicit_times_works(self):
        MortalityDistribution._validate(distribution_dict=self.md_explicit_times.to_dict(), source_is_dict=False)

    def test_implicit_time_works(self):
        MortalityDistribution._validate(distribution_dict=self.md_implicit_time.to_dict(), source_is_dict=False)

    def test_1d_mortality_should_work_when_no_time_given(self):
        MortalityDistribution._validate(distribution_dict=self.md_implicit_time_1d_rates.to_dict(),
                                        source_is_dict=False)

    # Ensure proper exceptions are thrown when improper inputs are supplied via building with the constructor

    def test_constructor_validation_age_dimension_of_data(self):
        ages = [0, 10, 20, 50]  # no longer matches self.rates dimensionality
        self.assertRaises(demog_ex.InvalidDataDimensionDim0Exception,
                          MortalityDistribution,
                          ages_years=ages, calendar_years=self.explicit_times, mortality_rate_matrix=self.rates)

    def test_constructor_validation_time_dimension_of_data(self):
        times = [1950, 1970]  # no longer matches self.rates dimensionality
        self.assertRaises(demog_ex.InvalidDataDimensionDim1Exception,
                          MortalityDistribution,
                          ages_years=self.ages, calendar_years=times, mortality_rate_matrix=self.rates)

    def test_constructor_validation_age_range(self):
        ages = [-1, 10, 20, 50, 100]  # invalid age, -1 year
        self.assertRaises(demog_ex.AgeOutOfRangeException,
                          MortalityDistribution,
                          ages_years=ages, calendar_years=self.explicit_times, mortality_rate_matrix=self.rates)

        ages = [0, 10, 20, 50, 2000]  # invalid age, 2000 years
        self.assertRaises(demog_ex.AgeOutOfRangeException,
                          MortalityDistribution,
                          ages_years=ages, calendar_years=self.explicit_times, mortality_rate_matrix=self.rates)

    def test_constructor_validation_time_range(self):
        times = [1, 1970, 1990]  # invalid calendar year, 1
        self.assertRaises(demog_ex.TimeOutOfRangeException,
                          MortalityDistribution,
                          ages_years=self.ages, calendar_years=times, mortality_rate_matrix=self.rates)

        times = [1, 1970, 3000]  # invalid calendar year, 3000
        self.assertRaises(demog_ex.TimeOutOfRangeException,
                          MortalityDistribution,
                          ages_years=self.ages, calendar_years=times, mortality_rate_matrix=self.rates)

    def test_constructor_validation_age_ascending(self):
        ages = [0, 10, 50, 20, 100]  # non-monotonically-increasing age
        self.assertRaises(demog_ex.NonMonotonicAgeException,
                          MortalityDistribution,
                          ages_years=ages, calendar_years=self.explicit_times, mortality_rate_matrix=self.rates)

    def test_constructor_validation_time_ascending(self):
        times = [1950, 1990, 1970]  # non-monotonically-increasing time/calendar year
        self.assertRaises(demog_ex.NonMonotonicTimeException,
                          MortalityDistribution,
                          ages_years=self.ages, calendar_years=times, mortality_rate_matrix=self.rates)

    # ensure proper exceptions are thrown when improper inputs are supplied via building with .from_dict()
    # all of these use explicit times

    def test_from_dict_validation_invalid_axis_names(self):
        self.mortality_dict['AxisNames'] = ['not', 'valid']
        self.assertRaises(demog_ex.InvalidFixedValueException,
                          MortalityDistribution.from_dict, distribution_dict=self.mortality_dict)

    def test_from_dict_validation_invalid_axis_scale_factors(self):
        self.mortality_dict['AxisScaleFactors'] = [-1, -1]
        self.assertRaises(demog_ex.InvalidFixedValueException,
                          MortalityDistribution.from_dict, distribution_dict=self.mortality_dict)

    def test_from_dict_validation_invalid_result_scale_factor(self):
        self.mortality_dict['ResultScaleFactor'] = 12345.6789
        self.assertRaises(demog_ex.InvalidFixedValueException,
                          MortalityDistribution.from_dict, distribution_dict=self.mortality_dict)

    def test_from_dict_validation_invalid_result_units(self):
        self.mortality_dict['ResultUnits'] = 'This is a test of the emergency broadcast system. This is only a test.'
        self.assertRaises(demog_ex.InvalidFixedValueException,
                          MortalityDistribution.from_dict, distribution_dict=self.mortality_dict)

    def test_from_dict_invalid_population_group_length(self):
        self.mortality_dict['PopulationGroups'] = [1, 2, 3, 4, 5, 6, 8, 9, 10]
        self.assertRaises(demog_ex.InvalidPopulationGroupLengthException,
                          MortalityDistribution.from_dict, distribution_dict=self.mortality_dict)

    def test_from_dict_validation_age_dimension_of_data(self):
        self.mortality_dict['PopulationGroups'][0] = [0, 10, 20, 50]  # no longer matches mortality rate dimensionality
        self.assertRaises(demog_ex.InvalidDataDimensionDim0Exception,
                          MortalityDistribution.from_dict, distribution_dict=self.mortality_dict)

    def test_from_dict_validation_time_dimension_of_data(self):
        self.mortality_dict['PopulationGroups'][1] = [1950, 1970]  # no longer matches mortality rate dimensionality
        self.assertRaises(demog_ex.InvalidDataDimensionDim1Exception,
                          MortalityDistribution.from_dict, distribution_dict=self.mortality_dict)

    def test_from_dict_validation_age_range(self):
        self.mortality_dict['PopulationGroups'][0][0] = -1  # invalid age -1
        self.assertRaises(demog_ex.AgeOutOfRangeException,
                          MortalityDistribution.from_dict, distribution_dict=self.mortality_dict)

        self.mortality_dict['PopulationGroups'][0][0] = 123456789  # invalid age
        self.assertRaises(demog_ex.AgeOutOfRangeException,
                          MortalityDistribution.from_dict, distribution_dict=self.mortality_dict)

    def test_from_dict_validation_time_range(self):
        self.mortality_dict['PopulationGroups'][1][0] = 1  # invalid time, calendar year 1
        self.assertRaises(demog_ex.TimeOutOfRangeException,
                          MortalityDistribution.from_dict, distribution_dict=self.mortality_dict)

        self.mortality_dict['PopulationGroups'][1][-1] = 3000  # invalid time, calendar year 3000
        self.assertRaises(demog_ex.TimeOutOfRangeException,
                          MortalityDistribution.from_dict, distribution_dict=self.mortality_dict)

    def test_from_dict_validation_age_ascending(self):
        self.mortality_dict['PopulationGroups'][0][-1] = 1  # not ascending now
        self.assertRaises(demog_ex.NonMonotonicAgeException,
                          MortalityDistribution.from_dict, distribution_dict=self.mortality_dict)

    def test_from_dict_validation_time_ascending(self):
        self.mortality_dict['PopulationGroups'][1][-1] = 1910  # not ascending now
        self.assertRaises(demog_ex.NonMonotonicTimeException,
                          MortalityDistribution.from_dict, distribution_dict=self.mortality_dict)

    def test_from_dict_and_to_dict_are_inverses(self):
        test_dict = MortalityDistribution.from_dict(distribution_dict=self.mortality_dict).to_dict(validate=False)
        self.assertEqual(self.mortality_dict, test_dict)

    def test_from_dict_validation_1d_rates_should_fail_when_time_given(self):
        # ... by the time validation is reached. 1d should be converted to 2d under appropriate situations already
        # This test is ONLY valid via building from the constructor directly, as from_dict() should never allow
        # a 1-d rate matrix, because the json/dict structure DOES NOT support 1d data for mortality.
        self.assertRaises(
            demog_ex.InvalidDataDimensionality,
            MortalityDistribution,
            ages_years=self.ages,
            calendar_years=self.explicit_times,
            mortality_rate_matrix=self.rates_time_independent_1d
        )

    def test_from_dict_validation_1d_rates_from_dict_should_fail(self):
        self.mortality_dict['ResultValues'] = [1, 2, 3]  # 1-d is never allowed in dict/json representation
        self.assertRaises(
            demog_ex.InvalidDataDimensionality,
            MortalityDistribution.from_dict,
            distribution_dict=self.mortality_dict
        )

    def test_from_dict_validation_0d_rates_should_fail(self):
        self.assertRaises(
            demog_ex.InvalidDataDimensionality,
            MortalityDistribution,
            ages_years=self.ages,
            calendar_years=self.explicit_times,
            mortality_rate_matrix=0.5  # 0-dimensional!
        )
