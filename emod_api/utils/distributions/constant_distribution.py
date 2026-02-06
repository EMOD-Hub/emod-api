from emod_api import schema_to_class as s2c
from emod_api.utils.distributions.base_distribution import BaseDistribution
from emod_api.utils.distributions.demographic_distribution_flag import DemographicDistributionFlag
from emod_api.utils.distributions.distribution_type import DistributionType


class ConstantDistribution(BaseDistribution):
    """
    This class represents a constant distribution, a type of statistical distribution where all outcomes are equally
    likely. A constant distribution is defined by a single value that is returned for all inputs.

    Args:
        value (float):
            - The constant value that this distribution returns.
            - The value should not be negative.

    Raises:
        ValueError: If the 'value' argument is negative.

    Example:
        >>> # Create a ConstantDistribution object.
        >>> cd = ConstantDistribution(5)
        >>> # The value attribute can be accessed and updated.
        >>> cd.value
        5
        >>> cd.value = 10
        >>> cd.value
        10
    """
    DEMOGRAPHIC_DISTRIBUTION_FLAG = DemographicDistributionFlag.CONSTANT.value

    def __init__(self, value: float):
        super().__init__()
        if value < 0:
            raise ValueError("The 'value' argument should not be negative.")
        self.value = value

    def set_intervention_distribution(self, intervention_object: s2c.ReadOnlyDict, prefix: str):
        """
        Set the distribution parameters to the object.

        Args:
            intervention_object (s2c.ReadOnlyDict):
                - The object to set.
            prefix (str):
                - The prefix of the parameters.
        """
        self._set_parameters(intervention_object, f"{prefix}_Distribution", DistributionType.CONSTANT_DISTRIBUTION.value)
        self._set_parameters(intervention_object, f"{prefix}_Constant", self.value)

    def get_demographic_distribution_parameters(self) -> dict:
        """
        Yield the flag and relevant values necessary for setting a demographics constant distribution

        Returns:
            a dict of the form: {'flag': X, 'value1': Y, 'value2': Z}
        """
        return {"flag": self.DEMOGRAPHIC_DISTRIBUTION_FLAG, "value1": self.value, "value2": None}  # value 2 not used
