import json

from emod_api.demographics.demographics_base import DemographicsBase
from emod_api.demographics.node import OverlayNode


class DemographicsOverlay(DemographicsBase):
    """
    This class inherits from :py:obj:`emod_api:emod_api.demographics.DemographicsBase` so all functions that can be used
    to create demographics can also be used to create an overlay file. The intended use is for a user to pass a
    self-built default OverlayNode object in to represent the Defaults section in the demographics overlay.
    """

    def __init__(self,
                 nodes: list[OverlayNode] = None,
                 idref: str = None,
                 default_node: OverlayNode = None):
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
            default_node: (OverlayNode) An optional node to use for default settings.

        """
        super(DemographicsOverlay, self).__init__(nodes=nodes, idref=idref, default_node=default_node)

    def to_file(self, file_name="demographics_overlay.json"):
        """
        Write the contents of the instance to an EMOD-compatible (JSON) file.
        """
        with open(file_name, "w") as demo_override_f:
            json.dump(self.to_dict(), demo_override_f)
