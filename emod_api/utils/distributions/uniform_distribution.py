from emod_api import schema_to_class as s2c
from emod_api.utils.distributions.base_distribution import BaseDistribution
from emod_api.utils.distributions.demographic_distribution_flag import DemographicDistributionFlag
from emod_api.utils.distributions.distribution_type import DistributionType


class UniformDistribution(BaseDistribution):
    """
    This class represents a uniform distribution, which is a type of statistical distribution
    where all outcomes are equally likely within a specified range. A uniform distribution is defined by two parameters:
    the minimum and maximum values that define the range of outcomes.

    Args:
        uniform_min (float):
            - The minimum value of the range for this distribution.
            - The value should not be negative.

        uniform_max (float):
            - The maximum value of the range for this distribution.
            - The value should not be negative.

    Raises:
        ValueError: If 'uniform_min' or 'uniform_max' arguments are negative.

    Example:
        >>> # Create  a UniformDistribution object.
        >>> ud = UniformDistribution(0, 10)
        >>> # The uniform_min and uniform_max attributes can be accessed and updated.
        >>> ud.uniform_min
        0
        >>> ud.uniform_max
        10
        >>> ud.uniform_min = 5
        >>> ud.uniform_min
        5
    """
    DEMOGRAPHIC_DISTRIBUTION_FLAG = DemographicDistributionFlag.UNIFORM.value

    def __init__(self, uniform_min: float, uniform_max: float):
        super().__init__()
        if uniform_min < 0 or uniform_max < 0:
            raise ValueError("The 'uniform_min' and 'uniform_max' arguments should not be negative.")
        if uniform_min > uniform_max:
            raise ValueError("The 'uniform_min' argument should be less than 'uniform_max'.")
        self.uniform_min = uniform_min
        self.uniform_max = uniform_max

    def set_intervention_distribution(self, intervention_object: s2c.ReadOnlyDict, prefix: str):
        """
        Set the distribution parameters to the object.

        Args:
            intervention_object (s2c.ReadOnlyDict):
                - The object to set.

            prefix (str):
                - The prefix of the parameters.
        """
        self._set_parameters(intervention_object, f"{prefix}_Distribution", DistributionType.UNIFORM_DISTRIBUTION.value)
        self._set_parameters(intervention_object, f"{prefix}_Min", self.uniform_min)
        self._set_parameters(intervention_object, f"{prefix}_Max", self.uniform_max)

    def get_demographic_distribution_parameters(self) -> dict:
        """
        Yield the flag and relevant values necessary for setting a demographics uniform distribution

        Returns:
            a dict of the form: {'flag': X, 'value1': Y, 'value2': Z}
        """
        return {"flag": self.DEMOGRAPHIC_DISTRIBUTION_FLAG, "value1": self.uniform_min, "value2": self.uniform_max}
