from emod_api import schema_to_class as s2c
from emod_api.utils.distributions.base_distribution import BaseDistribution
from emod_api.utils.distributions.demographic_distribution_flag import DemographicDistributionFlag


class BimodalDistribution(BaseDistribution):
    """
    This class represents a bimodal distribution, a type of statistical distribution with two different modes (peaks).
    A bimodal distribution is defined by two parameters: the proportion of the second bin, user defined bin, and the
    constant value of the second bin. The 1-proportion will be the first bin and constant value in the first bin is 1.

    This distribution is not supported in EMOD interventions.

    Args:
        proportion (float):
            - The proportion of the second bin.
            - This value should be between 0 and 1.

        constant (float):
            - The constant value of the second bin.
            - The value should not be negative.

    Examples:
        >>> # Create a BimodalDistribution object.
        >>> # In the follow example, there will be 20% of the second bin(5) and 80% of the first bin(1).
        >>> bd = BimodalDistribution(0.2, 5)
        >>> # The proportion and constant attributes can be accessed and updated.
        >>> bd.proportion
        0.2
        >>> bd.constant
        5
        >>> bd.proportion = 0.6
        >>> bd.proportion
        0.6

    """
    DEMOGRAPHIC_DISTRIBUTION_FLAG = DemographicDistributionFlag.BIMODAL.value

    def __init__(self, proportion: float, constant: float):
        super().__init__()
        if proportion < 0 or proportion > 1:
            raise ValueError("The 'proportion' argument should be between 0 and 1.")
        if constant < 0:
            raise ValueError("The 'constant' argument should not be negative.")
        self.proportion = proportion
        self.constant = constant

    def set_intervention_distribution(self, intervention_object: s2c.ReadOnlyDict, prefix: str):
        """
        This function is not supported in the intervention object. Raise NotImplementedError if called.
        """
        raise NotImplementedError("BimodalDistribution does not support intervention distribution. Please use "
                                  "other distributions.")

    def get_demographic_distribution_parameters(self) -> dict:
        """
        Yield the flag and relevant values necessary for setting a demographics bimodal distribution

        Returns:
            a dict of the form: {'flag': X, 'value1': Y, 'value2': Z}
        """
        return {"flag": self.DEMOGRAPHIC_DISTRIBUTION_FLAG,
                "value1": self.proportion,
                "value2": self.constant}
