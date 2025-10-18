from typing import List, Dict

from emod_api.demographics.Updateable import Updateable


class SusceptibilityDistributionOld(Updateable):
    def __init__(self,
                 distribution_values: List[float] = None,
                 result_scale_factor: float = None,
                 result_values: List[float] = None):
        """
        https://docs.idmod.org/projects/emod-generic/en/latest/parameter-demographics.html#complex-distributions

        Args:
            distribution_values:
            result_scale_factor:
            result_values:
        """
        super().__init__()
        self.distribution_values = distribution_values
        self.result_scale_factor = result_scale_factor
        self.result_values = result_values

    def to_dict(self) -> dict:
        susceptibility_distribution = self.parameter_dict

        if self.distribution_values is not None:
            susceptibility_distribution.update({"DistributionValues": self.distribution_values})

        if self.result_scale_factor is not None:
            susceptibility_distribution.update({"ResultScaleFactor": self.result_scale_factor})

        if self.result_values is not None:
            susceptibility_distribution.update({"ResultValues": self.result_values})

        return susceptibility_distribution

    def from_dict(self, age_distribution: Dict):
        raise NotImplementedError('Reading of a complex SusceptibilityDistribution json is not currently supported')
