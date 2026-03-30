from emod_api.demographics.node import Node


class OverlayNode(Node):
    """
    Node that only requires an ID. Use to overlay a Node.
    """

    def __init__(self,
                 node_id: int,
                 latitude: float = None,
                 longitude: float = None,
                 initial_population: int = None,
                 **kwargs
                 ):
        super().__init__(lat=latitude, lon=longitude, pop=initial_population, forced_id=node_id, **kwargs)

    def to_dict(self) -> dict:
        """
        Translate node structure to a dictionary for EMOD
        """
        d = {"NodeID": self.id}

        if self.node_attributes:
            na_dict = self.node_attributes.to_dict()
            if na_dict:
                d["NodeAttributes"] = na_dict

        if self.individual_attributes:
            ia_dict = self.individual_attributes.to_dict()
            if ia_dict:
                d["IndividualAttributes"] = ia_dict

        if self.individual_properties:
            ip_dict = {"IndividualProperties": []}
            for ip in self.individual_properties:
                ip_dict["IndividualProperties"].append(ip.to_dict())
            d.update(ip_dict)

        d.update(self.meta)
        return d
