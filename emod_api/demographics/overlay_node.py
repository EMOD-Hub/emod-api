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
