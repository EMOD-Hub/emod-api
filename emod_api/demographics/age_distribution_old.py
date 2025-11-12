from typing import List

from emod_api.demographics.updateable import Updateable


class AgeDistributionOld(Updateable):
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

    @property
    def num_dist_axes(self):
        import warnings
        warnings.warn(f"{__class__}: num_dist_axes (NumDistributionAxes) is not interpreted by EMOD and may be removed",
                      DeprecationWarning, stacklevel=2)
        return self._num_dist_axes

    @num_dist_axes.setter
    def num_dist_axes(self, value):
        import warnings
        warnings.warn(f"{__class__}: num_dist_axes (NumDistributionAxes) is not interpreted by EMOD and may be removed",
                      DeprecationWarning, stacklevel=2)
        self._num_dist_axes = value

    def to_dict(self) -> dict:
        age_distribution = {}

        if self.distribution_values is not None:
            age_distribution.update({"DistributionValues": self.distribution_values})

        if self.result_scale_factor is not None:
            age_distribution.update({"ResultScaleFactor": self.result_scale_factor})

        if self.result_values is not None:
            age_distribution.update({"ResultValues": self.result_values})

        return age_distribution

    def from_dict(self, age_distribution: dict):
        if age_distribution is not None:
            self.distribution_values = age_distribution.get("DistributionValues")
            self.result_scale_factor = age_distribution.get("ResultScaleFactor")
            self.result_values = age_distribution.get("ResultValues")
            self._num_dist_axes = age_distribution.get("NumDistributionAxes")
            self.results_units = age_distribution.get("ResultUnits")
        return self
