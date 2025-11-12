from typing import Dict


class Updateable:
    """
    (Base) class that provides update() method for each class that inherits from this class.
    """
    def __init__(self):
        self.parameter_dict = {}

    def to_dict(self) -> dict:
        raise NotImplementedError

    def update(self, overlay_object: ["Updateable", Dict], allow_nones: bool = False) -> None:
        """
        Updates an object with the values from overlay_object.

        Args:
            overlay_object: object with overriding attributes/values to apply to THIS object
            allow_nones: whether or not to apply/use attributes in overlay_object with value = None

        Returns:
            Nothing
        """
        try:
            # overlaying a provided Updateable object
            overlay_dict = vars(overlay_object)
        except TypeError:
            # overlaying a provided dict
            overlay_dict = overlay_object

        for attribute_name, new_attribute_value in overlay_dict.items():
            if not hasattr(self, attribute_name):
                raise AttributeError(f"Object of type: {type(self)} does not have an attribute named {attribute_name} "
                                     f"to override)")
            # only overlay non-None value UNLESS explicitly allowing it
            if new_attribute_value is not None or allow_nones is True:
                try:
                    # Calling update method in case we have an Updateable being overridden
                    getattr(self, attribute_name).update(new_attribute_value)
                except AttributeError:
                    # not an Updateable being overridden, do direct assignment
                    setattr(self, attribute_name, new_attribute_value)

    def add_parameter(self, key, value):
        """
        Adds a user defined key-value pair to demographics.
        :param key: Key
        :param value: Value
        :return: None
        """
        self.parameter_dict[key] = value
