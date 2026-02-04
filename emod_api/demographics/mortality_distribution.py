import emod_api.demographics.demographic_exceptions as demog_ex
from emod_api.demographics.Updateable import Updateable
from emod_api.utils import check_dimensionality


class MortalityDistribution(Updateable):
    def __init__(self,
                 ages_years: list[float],
                 mortality_rate_matrix: list[list[float]] | list[float],
                 calendar_years: list[float] = None):
        """
        A natural mortality distribution for one gender in units of "annual death rate for an individual". If the
        distribution is time-dependent, pass in a list of times (calendar_years).

        The MortalityDistribution provides a rate (probability) at which each agent will die naturally on any given
        model day given their current age. EMOD uses double linear interpolation (bilinear) of an agent's age and the
        current calendar year to determine the exact probability of their death.
        - See https://www.wikihow.com/Do-a-Double-Linear-Interpolation

        Mortality at any age or any year that preceeds or exceeds the supplied data will be equal to the value at
        the nearest age and/or timepoint of supplied data.

        Args:
            ages_years: (list[float]) A list of ages (in years) that mortality data will be provided for. Must be a
                list of monotonically increasing floats within range 0 <= age <= 200 .
            mortality_rate_matrix: (list[list[float]] or list[float]) A 2-d grid of mortality rates in units of
                "annual death rate for an individual". The first data dimension (index) is by age, the second data
                dimension is by calendar year. For M ages (in years) and N calendars years, the dimensionality of this
                matrix must be MxN . Alternately, a 1-d array of mortality rates may be given and will be interpreted
                as a time-independent "for all time" distribution. This option is only available if the calendar_years
                argument is not used.
            calendar_years: (list[float]) (optional) A list of times (in calendar years) that mortality data will be
                provided for. Must be a list of monotonically increasing floats within range 1900 <= year <= 2200 .
                If not provided, a default single calendar year (1900) will be used that effectively means
                "for all time".

        Example:
            ages_years: [0, 10, 20, 50, 100]   # M ages
            calendar_years: [1950, 1970, 1990] # N times. If not supplied, one time "forever" is used and N below is 1.
            mortality_rate_matrix: dimensionality: MxN
                [[0.2,  0.15, 0.1 ],  # These are mortality rates at age 0, the three time points above
                 [0.12, 0.08, 0.06],  # These are mortality rates at age 10
                 [0.05, 0.03, 0.01],  # These are mortality rates at age 20
                 [0.15, 0.1,  0.05],  # These are mortality rates at age 50
                 [0.3,  0.25, 0.2 ]]  # These are mortality rates at age 100

            Mortality at age 5 at 1960, bilinearly interpolated (shown in steps):
                0.2 + (1960-1950) * ((0.15-0.2) / (1970-1950)) = 0.175 (age 0 mortality rate at 1960)
                0.12 + (1960-1950) * ((0.08-0.12) / (1970-1950)) = 0.1 (age 10 mortality rate at 1960)
                0.175 + (5-0) * ((0.1-0.175) / (10-0)) = 0.1375 (age 5 mortality rate at 1960)
            Mortality at age 5 at 2100 (beyond supplied times), bilinearly interpolated: (shown in steps)
                (compute the value at the closest time possible, 1970, then report it for year 2100)
                0.1 (age 0 mortality rate at 1970 (also 2100))
                0.06 (age 10 mortality rate at 1970 (also 2100))
                0.1 + (5-0) * ((0.06-0.1) / (10-0)) = 0.08 (age 5 mortality rate at 1970 (also 2100))
        """
        super().__init__()
        self.ages_years = ages_years

        if calendar_years is None:
            self.calendar_years = [self._default_calendar_year]
            # Here we convert a 1-d array of values to a (trivial) 2-d array. Only allowed if time not passed.
            if check_dimensionality(data=mortality_rate_matrix, dimensionality=1) is True:
                mortality_rate_matrix = [[item] for item in mortality_rate_matrix]
        else:
            self.calendar_years = calendar_years
        self.mortality_rate_matrix = mortality_rate_matrix

        # This will convert the object to a mortality dictionary and then validate it reporting object-relevant messages
        self._validate(distribution_dict=self.to_dict(validate=False), source_is_dict=False)

    @property
    def _population_groups(self):
        return [self.ages_years, self.calendar_years]

    @classmethod
    def _rate_scale_factor(cls):
        return 1 / 365.0  # convert from per-year to per-day

    @classmethod
    def _rate_scale_units(cls):
        return "annual death rate for an individual"

    @property
    def _default_calendar_year(self):
        return 1900

    @classmethod
    def _axis_names(cls):
        return ['age', 'year']

    @classmethod
    def _axis_scale_factors(cls):
        return [365.0, 1]

    def to_dict(self, validate: bool = True) -> dict:
        distribution_dict = {
            'AxisNames': self._axis_names(),
            'AxisScaleFactors': self._axis_scale_factors(),
            'PopulationGroups': self._population_groups,
            'ResultScaleFactor': self._rate_scale_factor(),
            'ResultUnits': self._rate_scale_units(),
            'ResultValues': self.mortality_rate_matrix
        }
        if validate:
            self._validate(distribution_dict=distribution_dict, source_is_dict=False)
        return distribution_dict

    @classmethod
    def from_dict(cls, distribution_dict: dict):
        cls._validate(distribution_dict=distribution_dict, source_is_dict=True)
        return cls(ages_years=distribution_dict['PopulationGroups'][0],
                   mortality_rate_matrix=distribution_dict['ResultValues'],
                   calendar_years=distribution_dict['PopulationGroups'][1])

    # True means message relevant to verifying a mortality dictionary, False means messages relevant to verifying an obj
    _validation_messages = {
        'fixed_value_check': {
            True: "key: {0} value: {1} does not match expected value: {2}",
            False: None  # These are all properties of the obj and cannot be made invalid
        },
        'population_group_length_check': {
            True: "PopulationGroups expected to be a 2-d array of floats. The first dimension length must be two, but "
                  "is length {0}",
            False: None  # This is a property of the obj and cannot be made invalid
        },
        'data_dimensionality_check': {
            True: "ResultValues is expected to be a 2-d matrix of data but it is not.",
            False: "mortality_rate_matrix has an improper dimensionality. It must be a 2-d matrix if calendar_years is "
                   "given. If calendar_years is NOT given, it MAY be a 1-d list of values."
        },
        'data_dimensionality_check_dim0': {
            True: "ResultValues first dimension length {0} does not match the PopulationGroups[0] age bin count {1}",
            False: "mortality_rate_matrix first dimension length: {0} does not match the ages_years length: {1}"
        },
        'data_dimensionality_check_dim1': {
            True: "ResultValues second dimension length {0} does not match the PopulationGroups[1] time bin count: {1}",
            False: "mortality_rate_matrix second dimension length: {0} does not match the calendar_years length: {1}"
        },
        'age_range_check': {
            True: "PopulationGroups[0] age values must be: 0 <= age <= 200 in years",
            False: "All ages_years values must be: 0 <= age <= 200 in years"
        },
        'time_range_check': {
            True: "PopulationGroups[1] time values must be: 1900 <= time <= 2200 calendar year",
            False: "All calendar_years values must be: 1900 <= time <= 2200 calendar year"
        },
        'age_monotonicity_check': {
            True: "PopulationGroups[0] ages in years must monotonically increase but do not, index: {0} value: {1}",
            False: "ages_years values must monotonically increase but do not, index: {0} value: {1}"
        },
        'time_monotonicity_check': {
            True: "PopulationGroups[1] times in calendar years must monotonically increase but do not, index: {0} value: {1}",
            False: "calendar_years values must monotonically increase but do not, index: {0} value: {1}"
        }
    }

    @classmethod
    def _validate(cls, distribution_dict: dict, source_is_dict: bool):
        """
        Validate a MortalityDistribution in dict form

        Args:
            distribution_dict: (dict) the mortality dict to validate
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
                    message = cls._validation_messages['fixed_value_check'][source_is_dict].format(key, value, expected_value)
                    raise demog_ex.InvalidFixedValueException(message)

        # ensure the data table is MxN for the population groups == [M, N]
        population_groups = distribution_dict['PopulationGroups']
        data_table = distribution_dict['ResultValues']
        if source_is_dict is True:
            if len(population_groups) != 2:
                message = cls._validation_messages['population_group_length_check'][source_is_dict].format(len(population_groups))
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
            message = cls._validation_messages['data_dimensionality_check_dim0'][source_is_dict].format(len(data_table), n_ages)
            raise demog_ex.InvalidDataDimensionDim0Exception(message)
        for i in range(len(data_table)):
            if len(data_table[i]) != n_times:
                message = cls._validation_messages['data_dimensionality_check_dim1'][source_is_dict].format(len(data_table[i]), n_times)
                raise demog_ex.InvalidDataDimensionDim1Exception(message)

        # ensure the age and time lists are ascending and in reasonable ranges
        if any([(age < 0) or (age > 200) for age in ages]):
            message = cls._validation_messages['age_range_check'][source_is_dict]
            raise demog_ex.AgeOutOfRangeException(message)
        if any([(time < 1900) or (time > 2200) for time in times]):
            message = cls._validation_messages['time_range_check'][source_is_dict]
            raise demog_ex.TimeOutOfRangeException(message)

        for i in range(1, len(ages)):
            if ages[i] - ages[i - 1] <= 0:
                message = cls._validation_messages['age_monotonicity_check'][source_is_dict].format(i, ages[i])
                raise demog_ex.NonMonotonicAgeException(message)
        for i in range(1, len(times)):
            if times[i] - times[i - 1] <= 0:
                message = cls._validation_messages['time_monotonicity_check'][source_is_dict].format(i, times[i])
                raise demog_ex.NonMonotonicTimeException(message)
