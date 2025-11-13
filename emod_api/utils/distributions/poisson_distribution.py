from emod_api import schema_to_class as s2c
from emod_api.utils.distributions.base_distribution import BaseDistribution
from emod_api.utils.distributions.demographic_distribution_flag import DemographicDistributionFlag
from emod_api.utils.distributions.distribution_type import DistributionType


class PoissonDistribution(BaseDistribution):
    """
    This class represents a Poisson distribution, a type of statistical distribution where the probability of a given
    number of events occurring in a fixed interval of time or space is proportional to the mean number of events.

    Args:
        mean (float):
            - The mean of the Poisson distribution.
            - This value should not be negative.

    Raises:
        ValueError: If 'mean' argument is negative.

    Example:
        >>> # Create a PoissonDistribution object.
        >>> pd = PoissonDistribution(1)
        >>> # The mean attribute can be accessed and updated.
        >>> pd.mean
        1
        >>> pd.mean = 2
        >>> pd.mean
        2
    """
    DEMOGRAPHIC_DISTRIBUTION_FLAG = DemographicDistributionFlag.POISSON.value

    def __init__(self, mean: float):
        if mean < 0:
            raise ValueError("The 'mean' argument should not be negative.")
        super().__init__()
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
                             DistributionType.POISSON_DISTRIBUTION.value)
        self._set_parameters(intervention_object, f"{prefix}_Poisson_Mean", self.mean)

    def get_demographic_distribution_parameters(self) -> dict:
        """
        Yield the flag and relevant values necessary for setting a demographics poisson distribution

        Returns:
            a dict of the form: {'flag': X, 'value1': Y, 'value2': Z}
        """
        return {"flag": self.DEMOGRAPHIC_DISTRIBUTION_FLAG, "value1": self.mean, "value2": None}  # value2 not used