from abc import ABC, abstractmethod
from emod_api import schema_to_class as s2c


class BaseDistribution(ABC):
    """
    Abstract base class for distribution classes. This class should not be instantiated directly.
    """

    @abstractmethod
    def set_intervention_distribution(self, intervention_object: s2c.ReadOnlyDict, prefix: str):
        """
        Set the distribution parameters to the intervention object.

        Args:
            intervention_object (s2c.ReadOnlyDict):
                - The object to set.
            prefix (str):
                - The prefix of the parameters.
        """
        pass

    @abstractmethod
    def get_demographic_distribution_parameters(self) -> dict:
        """
        Yield the flag and relevant values necessary for setting a demographics distribution of the class type

        Returns:
            a dict of the form: {'flag': X, 'value1': Y, 'value2': Z}
        """
        pass

    def _set_parameters(self, emod_object, key, value):
        if hasattr(emod_object, key):
            setattr(emod_object, key, value)
        else:
            raise AttributeError(f"Attribute {key} does not exist in {emod_object.__class__.__name__}")
