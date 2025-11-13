from emod_api import schema_to_class as s2c
from emod_api.utils.distributions.base_distribution import BaseDistribution
from emod_api.utils.distributions.demographic_distribution_flag import DemographicDistributionFlag
from emod_api.utils.distributions.distribution_type import DistributionType


class ExponentialDistribution(BaseDistribution):
    """
    This class represents an exponential distribution, a type of statistical distribution
    where the probability of an event decreases exponentially with time.
    An exponential distribution is defined by a single parameter: the mean, which represents the average time
    between events.

    Args:
        mean (float):
            - The mean, also the scale parameter of the exponential distribution.
            - It's the 1/rate parameter.
            - This value is set during the initialization of the class instance. It can be updated using the 'update_attribute()' method.
            - The value should not be negative.

    Raises:
        ValueError: If 'mean' argument is negative.

    Example:
        >>> # Create an ExponentialDistribution object.
        >>> ed = ExponentialDistribution(1)
        >>> # The mean attribute can be accessed and updated.
        >>> ed.mean
        1
        >>> ed.mean = 2
        >>> ed.mean
        2
    """
    DEMOGRAPHIC_DISTRIBUTION_FLAG = DemographicDistributionFlag.EXPONENTIAL.value

    def __init__(self, mean: float):
        super().__init__()
        if mean < 0:
            raise ValueError("The 'mean' argument should not be negative.")
        self.mean = mean

    def set_intervention_distribution(self, intervention_object: s2c.ReadOnlyDict, prefix: str):
        """
        Set the distribution parameters to the object.

        Args:
            intervention_object (s2c.ReadOnlyDict):
                - The object to set.
            prefix (str):
                - The prefix of the parameters.
        """
        self._set_parameters(intervention_object, f"{prefix}_Distribution",
                             DistributionType.EXPONENTIAL_DISTRIBUTION.value)
        self._set_parameters(intervention_object, f"{prefix}_Exponential", self.mean)

    def get_demographic_distribution_parameters(self) -> dict:
        """
        Yield the flag and relevant values necessary for setting a demographics exponential distribution

        Returns:
            a dict of the form: {'flag': X, 'value1': Y, 'value2': Z}
        """
        return {"flag": self.DEMOGRAPHIC_DISTRIBUTION_FLAG, "value1": self.mean, "value2": None}  # value2 not used