from emod_api import schema_to_class as s2c
from emod_api.utils.distributions.base_distribution import BaseDistribution
from emod_api.utils.distributions.demographic_distribution_flag import DemographicDistributionFlag
from emod_api.utils.distributions.distribution_type import DistributionType


class WeibullDistribution(BaseDistribution):
    """
    This class represents a Weibull distribution, a type of statistical distribution where the probability density
    function is defined by two parameters: the shape parameter (kappa) and the scale parameter (lambda).

    Args:
        weibull_kappa (float):
            - The shape parameter of the Weibull distribution.
            - This value should be positive.

        weibull_lambda (float):
            - The scale parameter of the Weibull distribution.
            - This value should be positive.

    Raises:
        ValueError: If 'weibull_kappa' or 'weibull_lambda' arguments are not positive.

    Example:
        >>> # Create a WeibullDistribution object.
        >>> wd = WeibullDistribution(1, 2)
        >>> # The weibull_kappa and weibull_lambda attributes can be accessed and updated.
        >>> wd.weibull_kappa
        1
        >>> wd.weibull_lambda
        2
        >>> wd.weibull_kappa = 3
        >>> wd.weibull_kappa
        3
    """
    DEMOGRAPHIC_DISTRIBUTION_FLAG = DemographicDistributionFlag.WEIBULL.value

    def __init__(self, weibull_kappa: float, weibull_lambda: float):
        if weibull_kappa <= 0 or weibull_lambda <= 0:
            raise ValueError("The 'weibull_kappa' and 'weibull_lambda' arguments should be positive.")
        super().__init__()
        self.weibull_kappa = weibull_kappa
        self.weibull_lambda = weibull_lambda

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
                             DistributionType.WEIBULL_DISTRIBUTION.value)
        # scale parameter is lambda, shape parameter is kappa
        self._set_parameters(intervention_object, f"{prefix}_Kappa", self.weibull_kappa)
        self._set_parameters(intervention_object, f"{prefix}_Lambda", self.weibull_lambda)

    def get_demographic_distribution_parameters(self) -> dict:
        """
        Yield the flag and relevant values necessary for setting a demographics weibull distribution

        Returns:
            a dict of the form: {'flag': X, 'value1': Y, 'value2': Z}
        """
        # scale parameter is lambda, shape parameter is kappa
        return {"flag": self.DEMOGRAPHIC_DISTRIBUTION_FLAG, "value1": self.weibull_lambda, "value2": self.weibull_kappa}
