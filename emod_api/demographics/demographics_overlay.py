import json

from emod_api.demographics.demographics_base import DemographicsBase


class DemographicsOverlay(DemographicsBase):
    """
    In contrast to class :py:obj:`emod_api:emod_api.demographics.Demographics` this class does not set any defaults.
    It inherits from :py:obj:`emod_api:emod_api.demographics.DemographicsBase` so all functions that can be used to
    create demographics can also be used to create an overlay file. Parameters can be changed/set specifically by
    passing node_id, individual attributes, and individual attributes to the constructor.
    """

    def __init__(self, nodes: list = None,
                 idref: str = None,
                 individual_attributes=None,
                 node_attributes=None):
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
        """
        super(DemographicsOverlay, self).__init__(nodes=nodes, idref=idref)

        self.individual_attributes = individual_attributes
        self.node_attributes = node_attributes

        if self.individual_attributes is not None:
            self.raw["Defaults"]["IndividualAttributes"] = self.individual_attributes.to_dict()

        if self.node_attributes is not None:
            self.raw["Defaults"]["NodeAttributes"] = self.node_attributes.to_dict()

    def to_dict(self):
        self.verify_demographics_integrity()
        d = {"Defaults": dict()}
        if self.raw["Defaults"]["IndividualAttributes"]:
            d["Defaults"]["IndividualAttributes"] = self.raw["Defaults"]["IndividualAttributes"]

        if self.raw["Defaults"]["NodeAttributes"]:
            d["Defaults"]["NodeAttributes"] = self.raw["Defaults"]["NodeAttributes"]

        if self.raw["Metadata"]:
            d["Metadata"] = self.raw["Metadata"]  # there is no metadata class
            d["Metadata"]["NodeCount"] = len(self.nodes)
        if self.raw["Defaults"]["IndividualProperties"]:
            d["Defaults"]["IndividualProperties"] = self.raw["Defaults"]["IndividualProperties"]

        d["Nodes"] = [{"NodeID": n.forced_id} for n in self.nodes]

        return d

    def to_file(self, file_name="demographics_overlay.json"):
        """
        Write the contents of the instance to an EMOD-compatible (JSON) file.
        """
        with open(file_name, "w") as demo_override_f:
            json.dump(self.to_dict(), demo_override_f)
