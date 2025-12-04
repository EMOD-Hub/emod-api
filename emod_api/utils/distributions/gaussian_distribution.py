from emod_api import schema_to_class as s2c
from emod_api.utils.distributions.base_distribution import BaseDistribution
from emod_api.utils.distributions.demographic_distribution_flag import DemographicDistributionFlag
from emod_api.utils.distributions.distribution_type import DistributionType


class GaussianDistribution(BaseDistribution):
    """
    This class represents a Gaussian distribution, a type of statistical distribution where the values are distributed
    symmetrically around the mean. A Gaussian distribution is defined by two parameters: the mean and the standard
    deviation.

    Args:
        mean (float):
            - The mean of the Gaussian distribution.
            - This value should not be negative.

        std_dev (float):
            - The standard deviation of the Gaussian distribution.
            - This value should be positive.

    Raises:
        ValueError: If 'mean' argument is negative or 'std_dev' argument is not positive.

    Example:
        >>> # Create a GaussianDistribution object.
        >>> gd = GaussianDistribution(0, 1)
        >>> # The mean and std_dev attributes can be accessed and updated.
        >>> gd.mean
        0
        >>> gd.std_dev
        1
        >>> gd.mean = 5
        >>> gd.mean
        5
    """
    DEMOGRAPHIC_DISTRIBUTION_FLAG = DemographicDistributionFlag.GAUSSIAN.value

    def __init__(self, mean: float, std_dev: float):
        if mean < 0 or std_dev <= 0:
            raise ValueError("The 'mean' argument should not be negative and the 'std_dev' argument should be "
                             "positive.")
        super().__init__()
        self.mean = mean
        self.std_dev = std_dev

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
                             DistributionType.GAUSSIAN_DISTRIBUTION.value)
        self._set_parameters(intervention_object, f"{prefix}_Gaussian_Mean", self.mean)
        self._set_parameters(intervention_object, f"{prefix}_Gaussian_Std_Dev", self.std_dev)

    def get_demographic_distribution_parameters(self) -> dict:
        """
        Yield the flag and relevant values necessary for setting a demographics gaussian distribution

        Returns:
            a dict of the form: {'flag': X, 'value1': Y, 'value2': Z}
        """
        return {"flag": self.DEMOGRAPHIC_DISTRIBUTION_FLAG, "value1": self.mean, "value2": self.std_dev}
