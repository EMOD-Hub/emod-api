from emod_api import schema_to_class as s2c
from emod_api.utils.distributions.base_distribution import BaseDistribution
from emod_api.utils.distributions.demographic_distribution_flag import DemographicDistributionFlag
from emod_api.utils.distributions.distribution_type import DistributionType


class LogNormalDistribution(BaseDistribution):
    """
    This class represents a log-normal distribution, a type of statistical distribution where the logarithm of the
    values is normally distributed. A log-normal distribution is defined by two parameters: the mean and the standard
    deviation.

    Args:
        mean (float):
            - The mean/mu of the log-normal distribution.

        std_dev (float):
            - The standard deviation/sigma/width of the log-normal distribution.

    Example:
        >>> # Create a LogNormalDistribution object.
        >>> lnd = LogNormalDistribution(0, 1)
        >>> # The mean and std_dev attributes can be accessed and updated.
        >>> lnd.mean
        0
        >>> lnd.std_dev
        1
        >>> lnd.mean = 5
        >>> lnd.mean
        5
    """
    DEMOGRAPHIC_DISTRIBUTION_FLAG = DemographicDistributionFlag.LOG_NORMAL.value

    def __init__(self, mean: float, std_dev: float):
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
                             DistributionType.LOG_NORMAL_DISTRIBUTION.value)
        self._set_parameters(intervention_object, f"{prefix}_Log_Normal_Mu", self.mean)
        self._set_parameters(intervention_object, f"{prefix}_Log_Normal_Sigma", self.std_dev)

    def get_demographic_distribution_parameters(self) -> dict:
        """
        Yield the flag and relevant values necessary for setting a demographics log normal distribution

        Returns:
            a dict of the form: {'flag': X, 'value1': Y, 'value2': Z}
        """
        return {"flag": self.DEMOGRAPHIC_DISTRIBUTION_FLAG, "value1": self.mean, "value2": self.std_dev}
