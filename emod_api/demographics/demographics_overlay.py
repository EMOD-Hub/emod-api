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
                 default_node: OverlayNode,
                 nodes: list[OverlayNode] = None,
                 idref: str = None):
        """
        An object representation of an EMOD demographics overlay input (file). The contents are interpreted by EMOD
        at runtime as overrides to the canonical/primary demographics input file.

        Args:
            default_node: (OverlayNode) Contains default settings for nodes in the overlay.
            nodes (List[OverlayNode]): Overlay is applied to these nodes. Default is no nodes.
            idref (str): a name used to indicate files (demographics, climate, and migration) are used together
        """
        nodes = [] if nodes is None else nodes
        super().__init__(nodes=nodes, idref=idref, default_node=default_node)

    def to_file(self, file_name: str = "demographics_overlay.json"):
        """
        Writes the DemographicsOverlay to an EMOD-compatible json file.

        Args:
            file_name (str): The filepath to write to.

        Returns:
            Nothing
        """
        with open(file_name, "w") as demo_override_f:
            json.dump(self.to_dict(), demo_override_f)
