from typing import List, Dict

from emod_api.demographics.demographic_exceptions import *
from emod_api.demographics.Updateable import Updateable
from emod_api.utils import check_dimensionality


class AgeDistribution(Updateable):
    def __init__(self,
                 ages_years: List[float],
                 cumulative_population_fraction: List[float]):
        """
        A cumulative population age distribution in fraction units 0 to 1. This is used as part of initializing the
        population in an EMOD simulation.

        The AgeDistribution provides a probability each agent at the beginning of a simulation will be
        initialized with a given age. A uniform random number is drawn for each agent and checked against the
        provided cumulative population fractions directly, with the corresponding age entry selected for the agent. If
        the drawn number lies between two values, the selected agent age is linearly interpolated from the two closest
        corresponding ages. If the drawn number lies beyond the provided cumulative population fraction range, the
        closest corresponding age will be selected.

        Args:
            ages_years: (List[float]) A list of ages (in years) that population fraction data will be provided for.
                Must be a list of monotonically increasing floats within range 0 <= age <= 200 .
            cumulative_population_fraction: (List[float]) A list of cumulative population fractions corresponding to
                the provided ages_years list. Must be a list of monotonically increasing floats within range
                0 <= fraction <= 1 .

        Example:
            ages_years: [5, 10, 20, 50, 100]
            cumulative_population_fraction: [0.1, 0.2, 0.5, 0.8, 1.0]

            Uniform random number draw: 0.8
                Selected age: 50 years
            Uniform random number draw: 0.35
                Selected age: 10 + (0.35 - 0.2) * ((20-10) / (0.5-0.2)) = 15 years
            Uniform random number draw: 0.05 (beyond provided fraction range)
                Selected age: 1 year (nearest corresponding age)
        """
        super().__init__()
        self.ages_years = ages_years
        self.cumulative_population_fraction = cumulative_population_fraction
        # This will convert the object to an age distribution dictionary and then validate it reporting object-relevant
        # messages
        self._validate(distribution_dict=self.to_dict(validate=False), source_is_dict=False)

    @classmethod
    def _rate_scale_factor(cls):
        return 365.0  # convert ages in years to days

    def to_dict(self, validate: bool = True) -> Dict:
        distribution_dict = {
            'ResultValues': self.ages_years,
            'DistributionValues': self.cumulative_population_fraction,
            'ResultScaleFactor': self._rate_scale_factor()
        }
        if validate:
            self._validate(distribution_dict=distribution_dict, source_is_dict=False)
        return distribution_dict

    @classmethod
    def from_dict(cls, distribution_dict: Dict):
        cls._validate(distribution_dict=distribution_dict, source_is_dict=True)
        return cls(ages_years=distribution_dict['ResultValues'],
                   cumulative_population_fraction=distribution_dict['DistributionValues'])

    _validation_messages = {
        'fixed_value_check': {
            True: "key: %s value: %s does not match expected value: %s",
            False: None  # These are all properties of the obj and cannot be made invalid
        },
        'data_dimensionality_check_ages': {
            True: 'ResultValues must be a 1-d array of floats',
            False: 'ages_years must be a 1-d array of floats'
        },
        'data_dimensionality_check_distributions': {
            True: 'DistributionValues must be a 1-d array of floats',
            False: 'cumulative_population_fraction must be a 1-d array of floats'
        },
        'age_and_distribution_length_check': {
            True: 'ResultValues and DistributionValues must be the same length but are not',
            False: 'ages_years and cumulative_population_fraction must be the same length but are not'
        },
        'age_range_check': {
            True: "ResultValues age values must be: 0 <= age <= 200 in years. Out-of-range index:values : %s",
            False: "All ages_years values must be: 0 <= age <= 200 in years. Out-of-range index:values : %s"
        },
        'distribution_range_check': {
            True: "DistributionValues cumulative fractions must be: 0 <= fraction <= 1. "
                  "Out-of-range index:values : %s",
            False: "All cumulative_population_fraction values must be: 0 <= fraction <= 1. "
                   "Out-of-range index:values : %s"
        },
        'age_monotonicity_check': {
            True: "ResultValues ages in years must monotonically increase but do not, index: %d value: %s",
            False: "ages_years values must monotonically increase but do not, index: %d value: %s"
        },
        'distribution_monotonicity_check': {
            True: "DistributionValues cumulative fractions must monotonically increase but do not, index: %d value: %s",
            False: "cumulative_population_fraction values must monotonically increase but do not, index: %d value: %s"
        },
    }

    @classmethod
    def _validate(cls, distribution_dict: Dict, source_is_dict: bool):
        """
        Validate an AgeDistribution in dict form

        Args:
            distribution_dict: (dict) the age distribution dict to validate
            source_is_dict: (bool) If true, report dict-relevant error messages. If false, report obj-relevant messages.

        Returns:
            Nothing
        """
        if source_is_dict is True:
            expected_values = {
                'ResultScaleFactor': cls._rate_scale_factor()
            }
            for key, expected_value in expected_values.items():
                value = distribution_dict[key]
                if value != expected_value:
                    message = cls._validation_messages['fixed_value_check'][source_is_dict] % \
                              (key, value, expected_value)
                    raise InvalidFixedValueException(message)

        # ensure the ages and distribution values are both 1-d iterables of the same length
        ages = distribution_dict['ResultValues']
        distribution_values = distribution_dict['DistributionValues']

        is_1d = check_dimensionality(data=ages, dimensionality=1)
        if not is_1d:
            message = cls._validation_messages['data_dimensionality_check_ages'][source_is_dict]
            raise InvalidDataDimensionality(message)
        is_1d = check_dimensionality(data=distribution_values, dimensionality=1)
        if not is_1d:
            message = cls._validation_messages['data_dimensionality_check_distributions'][source_is_dict]
            raise InvalidDataDimensionality(message)

        if len(ages) != len(distribution_values):
            message = cls._validation_messages['age_and_distribution_length_check'][source_is_dict]
            raise InvalidDataDimensionLength(message)

        # ensure the age and distribution value lists are ascending and in reasonable ranges
        out_of_range = [f"{index}:{age}" for index, age in enumerate(ages) if (age < 0) or (age > 200)]
        if len(out_of_range) > 0:
            oor_str = ', '.join(out_of_range)
            message = cls._validation_messages['age_range_check'][source_is_dict] % oor_str
            raise AgeOutOfRangeException(message)
        out_of_range = [f"{index}:{value}" for index, value in enumerate(distribution_values)
                        if (value < 0) or (value > 1)]
        if len(out_of_range) > 0:
            oor_str = ', '.join(out_of_range)
            message = cls._validation_messages['distribution_range_check'][source_is_dict] % oor_str
            raise DistributionOutOfRangeException(message)

        for i in range(1, len(ages)):
            if ages[i] - ages[i-1] <= 0:
                message = cls._validation_messages['age_monotonicity_check'][source_is_dict] % (i, ages[i])
                raise NonMonotonicAgeException(message)
        for i in range(1, len(distribution_values)):
            if distribution_values[i] - distribution_values[i-1] <= 0:
                message = cls._validation_messages['distribution_monotonicity_check'][source_is_dict] % \
                          (i, distribution_values[i])
                raise NonMonotonicDistributionException(message)
