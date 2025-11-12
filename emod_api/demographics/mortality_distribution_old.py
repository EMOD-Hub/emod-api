from typing import List, Any

from emod_api.demographics.updateable import Updateable


class MortalityDistributionOld(Updateable):
    def __init__(self,
                 axis_names: List[str] = None,
                 axis_scale_factors: List[float] = None,
                 axis_units: Any = None,
                 num_distribution_axes: Any = None,
                 num_population_axes: Any = None,
                 num_population_groups: Any = None,
                 population_groups: List[List[float]] = None,
                 result_scale_factor: int = None,
                 result_units: Any = None,
                 result_values: List = None):
        """
        https://docs.idmod.org/projects/emod-generic/en/latest/parameter-demographics.html#complex-distributions

        Args:
            axis_names:
            axis_scale_factors:
            axis_units:
            population_groups:
            result_scale_factor:
            result_units:
            result_values:
        """
        super().__init__()
        self.axis_names = axis_names
        self.axis_scale_factors = axis_scale_factors
        self.axis_units = axis_units
        self._num_distribution_axes = num_distribution_axes
        self._num_population_axes = num_population_axes
        self._num_population_groups = num_population_groups
        self.population_groups = population_groups
        self.result_scale_factor = result_scale_factor
        self.result_units = result_units
        self.result_values = result_values

    @property
    def num_distribution_axes(self):
        import warnings
        warnings.warn(
            f"{__class__}: num_distribution_axes (NumDistributionAxes) is not interpreted by EMOD and may be removed",
            DeprecationWarning, stacklevel=2)
        return self._num_distribution_axes

    @num_distribution_axes.setter
    def num_distribution_axes(self, value):
        import warnings
        warnings.warn(
            f"{__class__}: num_distribution_axes (NumDistributionAxes) is not interpreted by EMOD and may be removed",
            DeprecationWarning, stacklevel=2)
        self._num_distribution_axes = value

    @property
    def num_population_axes(self):
        import warnings
        warnings.warn(
            f"{__class__}: num_population_axes (NumPopulationAxes) is not interpreted by EMOD and may be removed",
            DeprecationWarning, stacklevel=2)
        return self._num_population_axes

    @num_population_axes.setter
    def num_population_axes(self, value):
        import warnings
        warnings.warn(
            f"{__class__}: num_population_axes (NumPopulationAxes) is not interpreted by EMOD and may be removed",
            DeprecationWarning, stacklevel=2)
        self._num_population_axes = value

    @property
    def num_population_groups(self):
        import warnings
        warnings.warn(
            f"{__class__}: num_population_groups (NumPopulationGroups) is not interpreted by EMOD and may be removed",
            DeprecationWarning, stacklevel=2)
        return self._num_population_groups

    @num_population_groups.setter
    def num_population_groups(self, value):
        import warnings
        warnings.warn(
            f"{__class__}: num_population_groups (NumPopulationGroups) is not interpreted by EMOD and may be removed",
            DeprecationWarning, stacklevel=2)
        self._num_population_groups = value

    def to_dict(self) -> dict:
        mortality_distribution = self.parameter_dict

        if self.axis_names is not None:
            mortality_distribution.update({"AxisNames": self.axis_names})

        if self.axis_scale_factors is not None:
            mortality_distribution.update({"AxisScaleFactors": self.axis_scale_factors})

        if self.axis_units is not None:
            mortality_distribution.update({"AxisUnits": self.axis_units})

        if self._num_distribution_axes is not None:
            mortality_distribution.update({"NumDistributionAxes": self._num_distribution_axes})

        if self._num_population_groups is not None:
            mortality_distribution.update({"NumPopulationGroups": self._num_population_groups})

        if self.population_groups is not None:
            mortality_distribution.update({"PopulationGroups": self.population_groups})

        if self.result_scale_factor is not None:
            mortality_distribution.update({"ResultScaleFactor": self.result_scale_factor})

        if self.result_units is not None:
            mortality_distribution.update({"ResultUnits": self.result_units})

        if self.result_values is not None:
            mortality_distribution.update({"ResultValues": self.result_values})

        return mortality_distribution

    def from_dict(self, mortality_distribution: dict):
        if mortality_distribution is None:
            return None

        self.axis_names = mortality_distribution.get("AxisNames")
        self.axis_scale_factors = mortality_distribution.get("AxisScaleFactors")
        self.axis_units = mortality_distribution.get("AxisUnits")
        self._num_distribution_axes = mortality_distribution.get("NumDistributionAxes")
        self._num_population_groups = mortality_distribution.get("NumPopulationGroups")
        self.population_groups = mortality_distribution.get("PopulationGroups")
        self.result_scale_factor = mortality_distribution.get("ResultScaleFactor")
        self.result_units = mortality_distribution.get("ResultUnits")
        self.result_values = mortality_distribution.get("ResultValues")
        return self
