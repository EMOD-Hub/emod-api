import emod_api.demographics.demographic_exceptions as demog_ex

from emod_api.demographics.updateable import Updateable
from emod_api.utils import check_dimensionality


class SusceptibilityDistribution(Updateable):
    def __init__(self,
                 ages_years: list[float],
                 susceptible_fraction: list[float]):
        """

        A by-age susceptibility to infection distribution in fraction units 0 to 1. This is used whenever an agent is
        created, such as during model initialization and when agents are born.

        For Generic (GENERIC_SIM) simulations only.

        The SusceptibilityDistribution provides a probability each agent will be initialized as susceptible to
        infection (or not). It models the effect of natural immunity in preventing infection entirely in (1-fraction)
        of the population. Those that are allowed to acquire an infection can also be affected by other interventions
        or immunity derived from getting the disease. Agents are identified at creation time as 'susceptible to
        infection' by a uniform random number draw that is compared to the susceptibility distribution value at the
        corresponding agent age. If an agents age lies between two provided ages, its chances of being susceptible to
        infection are linearly interpolated from the two closest corresponding ages. If the agents age lies beyond the
        provided ages, the closest age-corresponding susceptibility will be used.

        WARNING: This complex distribution is different than when using a SimpleDistribution for this feature. The
        complex distribution makes people either completely susceptible or completely immune. In contrast, simple
        distributions give each person a probability of acquiring an infection (i.e. value between 0 and 1 versus
        just 0 or 1).

        Args:
            ages_years: (list[float]) A list of ages (in years) that susceptibility fraction data will be provided for.
                Must be a list of monotonically increasing floats within range 0 <= age <= 200 years.
            susceptible_fraction: (list[float]) A list of susceptibility fractions corresponding to the provided
                ages_years list. These represent the chances an initialized agent at a given age will be susceptible to
                infection. Must be a list of floats within range 0 <= fraction <= 1 .

        Example:
            ages_years: [0, 10, 20, 50, 100]
            susceptible_fraction: [0.9, 0.7, 0.3, 0.5, 0.8]

            Agent age 10 years
                susceptible chance: 0.7
            Agent age 15 years:
                susceptible chance: 0.7 + (15 - 10) * ((0.3-0.7) / (20-10)) = 0.5
            Agent age 1000 years (beyond provided age range)
                susceptible chance: 0.8 (nearest corresponding fraction)
        """
        super().__init__()
        self.ages_years = ages_years
        self.susceptible_fraction = susceptible_fraction
        # This will convert the object to an susceptibility distribution dictionary and then validate it reporting
        # object-relevant messages
        self._validate(distribution_dict=self.to_dict(validate=False), source_is_dict=False)

    @classmethod
    def _rate_scale_factor(cls):
        return 1

    def to_dict(self, validate: bool = True) -> dict:
        # susceptibility distribution dicts MUST be in ages_days. objs must be in ages_years
        distribution_dict = {
            'ResultValues': self.susceptible_fraction,
            'DistributionValues': [years * 365 for years in self.ages_years],
            'ResultScaleFactor': self._rate_scale_factor()
        }
        if validate:
            self._validate(distribution_dict=distribution_dict, source_is_dict=False)
        return distribution_dict

    @classmethod
    def from_dict(cls, distribution_dict: dict):
        # susceptibility distribution dicts MUST be in ages_days. objs must be in ages_years
        cls._validate(distribution_dict=distribution_dict, source_is_dict=True)
        ages_years = [days / 365 for days in distribution_dict['DistributionValues']]
        return cls(ages_years=ages_years,
                   susceptible_fraction=distribution_dict['ResultValues'])

    _validation_messages = {
        'fixed_value_check': {
            True: "key: {0} value: {1} does not match expected value: {2}",
            False: None  # These are all properties of the obj and cannot be made invalid
        },
        'data_dimensionality_check_ages': {
            True: 'DistributionValues must be a 1-d array of floats',
            False: 'ages_years must be a 1-d array of floats'
        },
        'data_dimensionality_check_susceptibility': {
            True: 'ResultValues must be a 1-d array of floats',
            False: 'susceptible_fraction must be a 1-d array of floats'
        },
        'age_and_susceptibility_length_check': {
            True: 'DistributionValues and ResultValues must be the same length but are not',
            False: 'ages_years and susceptible_fraction must be the same length but are not'
        },
        'age_range_check': {
            True: "DistributionValues age values must be: 0 <= age <= 73000 in days. Out-of-range index:values : {0}",
            False: "All ages_years values must be: 0 <= age <= 200 in years. Out-of-range index:values : {0}"
        },
        'susceptibility_range_check': {
            True: "ResultValues susceptible fractions must be: 0 <= fraction <= 1. "
                  "Out-of-range index:values : {0}",
            False: "All susceptible_fraction values must be: 0 <= fraction <= 1. "
                   "Out-of-range index:values : {0}"
        },
        'age_monotonicity_check': {
            True: "DistributionValues ages in days must monotonically increase but do not, index: {0} value: {1}",
            False: "ages_years values must monotonically increase but do not, index: {0} value: {1}"
        }
    }

    @classmethod
    def _validate(cls, distribution_dict: dict, source_is_dict: bool):
        """
        Validate a SusceptibilityDistribution in dict form

        Args:
            distribution_dict: (dict) the susceptibility distribution dict to validate
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
                    message = cls._validation_messages['fixed_value_check'][source_is_dict].format(key, value, expected_value)
                    raise demog_ex.InvalidFixedValueException(message)

        # ensure the ages and distribution values are both 1-d iterables of the same length
        ages = distribution_dict['DistributionValues']
        susceptible_values = distribution_dict['ResultValues']

        is_1d = check_dimensionality(data=ages, dimensionality=1)
        if not is_1d:
            message = cls._validation_messages['data_dimensionality_check_ages'][source_is_dict]
            raise demog_ex.InvalidDataDimensionality(message)
        is_1d = check_dimensionality(data=susceptible_values, dimensionality=1)
        if not is_1d:
            message = cls._validation_messages['data_dimensionality_check_susceptibility'][source_is_dict]
            raise demog_ex.InvalidDataDimensionality(message)

        if len(ages) != len(susceptible_values):
            message = cls._validation_messages['age_and_susceptibility_length_check'][source_is_dict]
            raise demog_ex.InvalidDataDimensionLength(message)

        # ensure the age and susceptibility value lists are ascending and in reasonable ranges
        # record in days for dict-relevant messages, years for obj-relevant messages
        factor = 1 if source_is_dict is True else 1 / 365.0
        out_of_range = [f"{index}:{age * factor}" for index, age in enumerate(ages) if (age < 0 * 365) or (age > 200 * 365)]
        if len(out_of_range) > 0:
            oor_str = ', '.join(out_of_range)
            message = cls._validation_messages['age_range_check'][source_is_dict].format(oor_str)
            raise demog_ex.AgeOutOfRangeException(message)
        out_of_range = [f"{index}:{value}" for index, value in enumerate(susceptible_values)
                        if (value < 0) or (value > 1)]
        if len(out_of_range) > 0:
            oor_str = ', '.join(out_of_range)
            message = cls._validation_messages['susceptibility_range_check'][source_is_dict].format(oor_str)
            raise demog_ex.DistributionOutOfRangeException(message)

        for i in range(1, len(ages)):
            if ages[i] - ages[i - 1] <= 0:
                message = cls._validation_messages['age_monotonicity_check'][source_is_dict].format(i, ages[i])
                raise demog_ex.NonMonotonicAgeException(message)
