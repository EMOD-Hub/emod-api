import json

from emod_api.demographics.demographics_base import DemographicsBase
from emod_api.demographics.node import Node


class DemographicsOverlay(DemographicsBase):
    """
    In contrast to class :py:obj:`emod_api:emod_api.demographics.Demographics` this class does not set any defaults.
    It inherits from :py:obj:`emod_api:emod_api.demographics.DemographicsBase` so all functions that can be used to
    create demographics can also be used to create an overlay file. Parameters can be changed/set specifically by
    passing node_id, individual attributes, and individual attributes to the constructor.
    """

    def __init__(self,
                 nodes: list = None,
                 idref: str = None,
                 default_node: Node = None):
        """
        A class to create demographic overlays.
        Args:
            nodes: Overlay is applied to these nodes.
            idref: a name used to indicate files (demographics, climate, and migration) are used together
            individual_attributes: Object of type
                :py:obj:`emod_api:emod_api.demographics.PropertiesAndAttributes.IndividualAttributes
                to overwrite individual attributes
            node_attributes:  Object of type
                :py:obj:`emod_api:emod_api.demographics.PropertiesAndAttributes.NodeAttributes
                to overwrite individual attributes
            default_node: (Node) An optional node to use for default settings.

        """
        super(DemographicsOverlay, self).__init__(nodes=nodes, idref=idref, default_node=default_node)

    def to_file(self, file_name="demographics_overlay.json"):
        """
        Write the contents of the instance to an EMOD-compatible (JSON) file.
        """
        with open(file_name, "w") as demo_override_f:
            json.dump(self.to_dict(), demo_override_f)
