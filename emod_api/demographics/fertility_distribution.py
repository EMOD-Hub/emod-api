from typing import List, Dict

import emod_api.demographics.demographic_exceptions as demog_ex

from emod_api.demographics.Updateable import Updateable
from emod_api.utils import check_dimensionality


class FertilityDistribution(Updateable):
    def __init__(self,
                 ages_years: List[float],
                 calendar_years: List[float],
                 pregnancy_rate_matrix: List[List[float]]):
        """
        A pregancies/births distribution in units of "annual birth rate per 1000 women". For alternative representations
        of fertlity/birth in EMOD, see config parameter Birth_Rate_Dependence for more details.

        The FertilityDistribution is used to determine the rate of pregnancies that a "possible mother" will have based
        on the individual's age and the calendar year. A woman is a possible mother if her age is between (14.0, 45.0)
        non-inclusive and is not already pregnant. Once a woman becomes pregnant, she will be pregnant for 40 weeks and
        then give birth.

        EMOD uses double linear interpolation (bilinear) of a 'possible mothers' age and the current calendar year to
        determine her probability of becoming pregnant. At every time step, 'possible mothers' are identified and are
        then probabilistically checked to determine if they become pregnant.
        - See https://www.wikihow.com/Do-a-Double-Linear-Interpolation

        Fertility at any age or any year that preceeds or exceeds the supplied data will be equal to the value at
        the nearest age and/or timepoint of supplied data.

        In order to model the transfer of immunity or infection from mother to child, one must model pregnancies.

        NOTE: In the limit of low birth rate, the probability of becoming pregnant is equivalent to the birth rate.
        However, at higher birth rates, some fraction of possible mothers will already be pregnant.
        Roughly speaking, if we want women to give birth every other year, and they gestate for one year,
        then the expected time between pregnancy has to be one year, not two.
        Hence, the maximum possible birth rate is 1 child per woman per gestation period.

        To determine if a woman becomes pregnant, the following logic is used:

            birthrate = FertilityDistribution.draw_value( age, calendar_year )
            birthrate = birthrate / (1.0 - birthrate * DAYSPERWEEK(7) * WEEKS_FOR_GESTATION(40))
            birth_probability = birthrate * dt * x_Birth
            is_pregnant = uniform_random_number < birth_probability

        Args:
            ages_years (list[float]): A list of ages (in years) that fertility data will be provided for. Must be a
                list of monotonically increasing floats. Regardless of the provided ages and data, women in EMOD can
                only be possible mothers if their age is between (14.0, 45.0) non-inclusive.

            calendar_years (list[float]): A list of times (in calendar years) that fertility data will be
                provided for. Must be a list of monotonically increasing floats within range 1900 <= year <= 2200 .

            pregnancy_rate_matrix (list[list[float]]): A 2-d grid of fertility rates in units of
                "annual birth rate per 1000 women". The first data dimension (index) is by age, the second data
                dimension is by calendar year. For M ages (in years) and N calendars years, the dimensionality of this
                matrix must be MxN .

        Example:
            ages_years: [15.0, 24.999, 25.0, 34.999, 35.0, 44.999, 45.0, 125.0]     # M ages
            calendar_years: [2010.0, 2014.999, 2015.0, 2019.999, 2020.0, 2024.999]  # N times
            pregnancy_rate_matrix: dimensionality MxN, units: fertility/year/1000 women
                [[103.3, 103.3, 77.5, 77.5, 65.5, 65.5],     # fertility rates at age 15.0, the six timepoints above
                 [103.3, 103.3, 77.5, 77.5, 65.5, 65.5],     # fertility rates at age 24.999
                 [265.0, 265.0, 278.7, 278.7, 275.4, 275.4], # fertility rates at age 25.0
                 [265.0, 265.0, 278.7, 278.7, 275.4, 275.4], # fertility rates at age 34.999
                 [152.4, 152.4, 129.2, 129.2, 115.9, 115.9], # fertility rates at age 35.0
                 [152.4, 152.4, 129.2, 129.2, 115.9, 115.9], # fertility rates at age 44.999
                 [19.9, 19.9, 14.6, 14.6, 12.1, 12.1],       # fertility rates at age 45.0
                 [19.9, 19.9, 14.6, 14.6, 12.1, 12.1]]       # fertility rates at age 125.0

            A 30 year-old woman who is not pregnant at time/year 2022.5 bilinearly interpolated (shown in steps):
                275.4 + (2022.5-2020.0) * ((275.4-275.4) / (2024.999-2020.0)) = 275.4 (age 25.0 fertility at 2022.5)
                275.4 + (2022.5-2020.0) * ((275.4-275.4) / (2024.999-2020.0)) = 275.4 (age 34.99 fertility at 2022.5)
                275.4 + (30-25.0) * ((275.4-275.4) / (34.999-25)) = 275.4 (age 30 fertility at 2022.5)
                scale result to fertility/woman/day: 275.4 / (365 * 1000) = 0.0007545 (birth probability)
        """
        super().__init__()
        self.ages_years = ages_years
        self.calendar_years = calendar_years
        self.pregnancy_rate_matrix = pregnancy_rate_matrix

        # This will convert the object to a fertility dictionary and then validate it reporting object-relevant messages
        self._validate(distribution_dict=self.to_dict(validate=False), source_is_dict=False)

    @property
    def _population_groups(self):
        return [self.ages_years, self.calendar_years]

    @classmethod
    def _rate_scale_factor(cls):
        return 1 / 365.0 / 1000  # convert from per-year, per 1000 women to per/woman/day

    @classmethod
    def _rate_scale_units(cls):
        return "annual birth rate per 1000 women"

    @classmethod
    def _axis_names(cls):
        return ['age', 'year']

    @classmethod
    def _axis_scale_factors(cls):
        return [365.0, 1]

    def to_dict(self, validate: bool = True) -> Dict:
        distribution_dict = {
            'AxisNames': self._axis_names(),
            'AxisScaleFactors': self._axis_scale_factors(),
            'PopulationGroups': self._population_groups,
            'ResultScaleFactor': self._rate_scale_factor(),
            'ResultUnits': self._rate_scale_units(),
            'ResultValues': self.pregnancy_rate_matrix
        }
        if validate:
            self._validate(distribution_dict=distribution_dict, source_is_dict=False)
        return distribution_dict

    @classmethod
    def from_dict(cls, distribution_dict: dict):
        cls._validate(distribution_dict=distribution_dict, source_is_dict=True)
        return cls(ages_years=distribution_dict['PopulationGroups'][0],
                   calendar_years=distribution_dict['PopulationGroups'][1],
                   pregnancy_rate_matrix=distribution_dict['ResultValues'])

    # True means message relevant to verifying a fertility dictionary, False means messages relevant to verifying an obj
    _validation_messages = {
        'fixed_value_check': {
            True: "key: %s value: %s does not match expected value: %s",
            False: None  # These are all properties of the obj and cannot be made invalid
        },
        'population_group_length_check': {
            True: "PopulationGroups expected to be a 2-d array of floats. The first dimension length must be two, but "
                  "is length %d",
            False: None  # This is a property of the obj and cannot be made invalid
        },
        'data_dimensionality_check': {
            True: "ResultValues is expected to be a 2-d matrix of data but it is not.",
            False: "pregnancy_rate_matrix has an improper dimensionality. It must be a 2-d matrix."
        },
        'data_dimensionality_check_dim0': {
            True: "ResultValues first dimension length %d does not match the PopulationGroups[0] age bin count %d",
            False: "pregnancy_rate_matrix first dimension length: %d does not match the ages_years length: %d"
        },
        'data_dimensionality_check_dim1': {
            True: "ResultValues second dimension length %d does not match the PopulationGroups[1] time bin count: %d",
            False: "pregnancy_rate_matrix second dimension length: %d does not match the calendar_years length: %d"
        },
        'age_range_check': {
            True: "PopulationGroups[0] age values must be: 0 <= age <= 200 in years. Out-of-range index:values : %s",
            False: "All ages_years values must be: 0 <= age <= 200 in years. Out-of-range index:values : %s"
        },
        'time_range_check': {
            True: "PopulationGroups[1] time values must be: 1900 <= time <= 2200 calendar year",
            False: "All calendar_years values must be: 1900 <= time <= 2200 calendar year"
        },
        'age_monotonicity_check': {
            True: "PopulationGroups[0] ages in years must monotonically increase but do not, index: %d value: %s",
            False: "ages_years values must monotonically increase but do not, index: %d value: %s"
        },
        'time_monotonicity_check': {
            True: "PopulationGroups[1] times in calendar years must monotonically increase but do not, index: %d value: %s",
            False: "calendar_years values must monotonically increase but do not, index: %d value: %s"
        }
    }

    @classmethod
    def _validate(cls, distribution_dict: Dict, source_is_dict: bool):
        """
        Validate a FertilityDistribution in dict form

        Args:
            distribution_dict: (dict) the fertility dict to validate
            source_is_dict: (bool) If true, report dict-relevant error messages. If false, report obj-relevant messages.

        Returns:
            Nothing
        """
        if source_is_dict is True:
            expected_values = {
                'AxisNames': cls._axis_names(),
                'AxisScaleFactors': cls._axis_scale_factors(),
                'ResultScaleFactor': cls._rate_scale_factor(),
                'ResultUnits': cls._rate_scale_units()
            }
            for key, expected_value in expected_values.items():
                value = distribution_dict[key]
                if value != expected_value:
                    message = cls._validation_messages['fixed_value_check'][source_is_dict] % (key, value, expected_value)
                    raise demog_ex.InvalidFixedValueException(message)

        # ensure the data table is MxN for the population groups == [M, N]
        population_groups = distribution_dict['PopulationGroups']
        data_table = distribution_dict['ResultValues']
        if source_is_dict is True:
            if len(population_groups) != 2:
                message = cls._validation_messages['population_group_length_check'][source_is_dict] % (len(population_groups))
                raise demog_ex.InvalidPopulationGroupLengthException(message)

        # ensure the data table has the correct dimensionality. It must be 2-d.
        is_2d = check_dimensionality(data=data_table, dimensionality=2)
        if not is_2d:
            message = cls._validation_messages['data_dimensionality_check'][source_is_dict]
            raise demog_ex.InvalidDataDimensionality(message)

        # continue checking dimension lengths
        ages = population_groups[0]
        times = population_groups[1]
        n_ages = len(ages)
        n_times = len(times)
        if len(data_table) != n_ages:
            message = cls._validation_messages['data_dimensionality_check_dim0'][source_is_dict] % (len(data_table), n_ages)
            raise demog_ex.InvalidDataDimensionDim0Exception(message)
        for i in range(len(data_table)):
            if len(data_table[i]) != n_times:
                message = cls._validation_messages['data_dimensionality_check_dim1'][source_is_dict] % (len(data_table[i]), n_times)
                raise demog_ex.InvalidDataDimensionDim1Exception(message)

        # ensure the age and time lists are ascending and in reasonable ranges
        out_of_range = [f"{index}:{age}" for index, age in enumerate(ages) if (age < 0) or (age > 200)]
        if len(out_of_range) > 0:
            oor_str = ', '.join(out_of_range)
            message = cls._validation_messages['age_range_check'][source_is_dict] % oor_str
            raise demog_ex.AgeOutOfRangeException(message)

        if any([(time < 1900) or (time > 2200) for time in times]):
            message = cls._validation_messages['time_range_check'][source_is_dict]
            raise demog_ex.TimeOutOfRangeException(message)

        for i in range(1, len(ages)):
            if ages[i] - ages[i - 1] <= 0:
                message = cls._validation_messages['age_monotonicity_check'][source_is_dict] % (i, ages[i])
                raise demog_ex.NonMonotonicAgeException(message)
        for i in range(1, len(times)):
            if times[i] - times[i - 1] <= 0:
                message = cls._validation_messages['time_monotonicity_check'][source_is_dict] % (i, times[i])
                raise demog_ex.NonMonotonicTimeException(message)
