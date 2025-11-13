from emod_api import schema_to_class as s2c
from emod_api.utils.distributions.base_distribution import BaseDistribution
from emod_api.utils.distributions.distribution_type import DistributionType


class DualConstantDistribution(BaseDistribution):
    """
    This class represents a dual constant distribution, a type of statistical distribution where the outcomes are
    distributed between a constant value and zero based on a proportion. A dual constant
    distribution is defined by two parameters: the proportion and the constant value.

    This distribution is not supported in EMOD demographics.

    Args:
        proportion (float):
            - The proportion of value of zero.
            - This value should be between 0 and 1.

        constant (float):
            - The second constant value that this distribution returns other than zero.
            - The value should not be negative.

    Raises:
        ValueError: If 'proportion' argument is not between 0 and 1 or 'constant' argument is negative.

    Example:
        >>> # Create a DualConstantDistribution object.
        >>> # In the follow example, there will be 20% of zeros and 80% of 5s.
        >>> dcd = DualConstantDistribution(0.2, 5)
        >>> # The proportion and constant attributes can be accessed and updated.
        >>> dcd.proportion
        0.2
        >>> dcd.constant
        5
        >>> dcd.proportion = 0.6
        >>> dcd.proportion
        0.6
    """
    def __init__(self, proportion: float, constant: float):
        if proportion < 0 or proportion > 1:
            raise ValueError("The 'proportion' argument should be between 0 and 1.")
        if constant < 0:
            raise ValueError("The 'constant' argument should not be negative.")
        super().__init__()
        self.proportion = proportion
        self.constant = constant

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
                             DistributionType.DUAL_CONSTANT_DISTRIBUTION.value)
        self._set_parameters(intervention_object, f"{prefix}_Proportion_0", self.proportion)
        self._set_parameters(intervention_object, f"{prefix}_Peak_2_Value", self.constant)

    def get_demographic_distribution_parameters(self) -> dict:
        """
        This function is not supported in the demographic object. Raise NotImplementedError if called.
        """
        raise NotImplementedError("DualConstantDistribution does not support demographic distribution. Please use "
                                  "other distributions.")