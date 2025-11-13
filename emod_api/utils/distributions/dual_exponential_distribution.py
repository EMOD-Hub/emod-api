from emod_api import schema_to_class as s2c
from emod_api.utils.distributions.base_distribution import BaseDistribution
from emod_api.utils.distributions.distribution_type import DistributionType


class DualExponentialDistribution(BaseDistribution):
    """
    This class represents a dual exponential distribution, a type of statistical distribution where the outcomes are
    distributed between two exponential distributions based on a proportion. A dual exponential distribution is defined
    by three parameters: the proportion, the first mean, and the second mean.

    This distribution is not supported in EMOD demographics.

    Args:
        proportion (float):
            - The proportion of the first exponential distribution.
            - This value should be between 0 and 1.

        mean_1 (float):
            - The mean of the first exponential distribution.
            - This value should be positive.

        mean_2 (float):
            - The mean of the second exponential distribution.
            - This value should be positive.

    Raises:
        ValueError: If 'proportion' argument is not between 0 and 1 or 'mean_1' or 'mean_2' arguments are negative.

    Example:
        >>> # Create a DualExponentialDistribution object.
        >>> # In the follow example, there will be 20% of the first exponential distribution and 80% of the second.
        >>> ded = DualExponentialDistribution(0.2, 1, 2)
        >>> # The proportion, mean_1, and mean_2 attributes can be accessed and updated.
        >>> ded.proportion
        0.2
        >>> ded.mean_1
        1
        >>> ded.mean_2
        2
        >>> ded.proportion = 0.6
        >>> ded.proportion
        0.6
    """
    def __init__(self, proportion: float, mean_1: float, mean_2: float):
        if proportion < 0 or proportion > 1:
            raise ValueError("The 'proportion' argument should be between 0 and 1.")
        if mean_1 <= 0 or mean_2 <= 0:
            raise ValueError("The 'mean_1' and 'mean_2' arguments should be positive.")
        super().__init__()
        self.proportion = proportion
        self.mean_1 = mean_1
        self.mean_2 = mean_2

    def set_intervention_distribution(self, intervention_object: s2c.ReadOnlyDict, prefix: str):
        """
        Set the distribution parameters to the object.

        Args:
            intervention_object (s2c.ReadOnlyDict):
                - The object to set.
            prefix (str):
                - The prefix of the parameters.
        """
        self._set_parameters(intervention_object, f"{prefix}_Distribution", DistributionType.DUAL_EXPONENTIAL_DISTRIBUTION.value)
        self._set_parameters(intervention_object, f"{prefix}_Proportion_1", self.proportion)
        self._set_parameters(intervention_object, f"{prefix}_Mean_1", self.mean_1)
        self._set_parameters(intervention_object, f"{prefix}_Mean_2", self.mean_2)

    def get_demographic_distribution_parameters(self) -> None:
        """
        This function is not supported in the demographic object. Raise NotImplementedError if called.
        """
        raise NotImplementedError("DualExponentialDistribution does not support demographic distribution. Please use "
                                  "other distributions.")