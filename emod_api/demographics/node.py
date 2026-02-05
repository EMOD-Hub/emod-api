import math
from typing import Callable, List, Tuple

from emod_api.demographics.age_distribution import AgeDistribution
from emod_api.demographics.fertility_distribution import FertilityDistribution
from emod_api.demographics.mortality_distribution import MortalityDistribution
from emod_api.demographics.susceptibility_distribution import SusceptibilityDistribution
from emod_api.demographics.updateable import Updateable
from emod_api.demographics.properties_and_attributes import IndividualAttributes, IndividualProperty, IndividualProperties, NodeAttributes


class Node(Updateable):
    # ability to resolve between Nodes
    res_in_degrees = 2.5 / 60

    def __init__(self,
                 lat: float,
                 lon: float,
                 pop: float,
                 name: str = None,
                 area: float = None,
                 # TODO: consider deprecating 'forced_id' as an argument and renaming it to simply 'id' for clarity and
                 #  brevity.
                 forced_id: int = None,
                 individual_attributes: IndividualAttributes = None,
                 individual_properties: IndividualProperties = None,
                 node_attributes: NodeAttributes = None,
                 meta: dict = None):
        """
        A Node in EMOD is synonymous with a group of people (model agents). A node typically represents a spatial
        geography (for example, a city, province, or country), but does not have to. Arguments to Node construction
        define states of the agents (individual_properties), their initial attributes and distributions
        (initial_attributes), and attributes of the node (group) as a whole (node_attributes).

        Args:
            lat (float): Latitude of the node in degrees.
            lon (float): Longitude of the node in degrees.
            pop (int): Initial population of the node.
            name (str): Name of the node.
            area (float): Area of the node. # TODO: units unknown
            forced_id (int): ID of the node
            individual_attributes (IndividualAttributes): Specifies initial distributions of various agent attributes,
                such as age, fertility, and mortality.
            individual_properties (IndividualProperties): Specifies the utilized IndividualProperty objects for the
                node, which define properties of individual model agents.
            node_attributes (NodeAttributes): Specifies node-specific attributes.
            meta (dict): A metadata dictionary for a Node. Entries in here are effectively comments as EMOD
                  binaries do not recognize node-level metadata.
        """
        super().__init__()
        self.forced_id = forced_id
        self.meta = meta if meta else {}
        self.individual_attributes = individual_attributes if individual_attributes else IndividualAttributes()
        self.individual_properties = individual_properties if individual_properties else IndividualProperties()

        self.node_attributes = NodeAttributes(latitude=lat, longitude=lon, initial_population=pop, area=area)
        if node_attributes is not None:
            self.node_attributes.update(node_attributes)

        if name is None:
            # if no node name was explicitly provided, we need to figure out how to name the node
            if node_attributes is None or node_attributes.name is None:
                # if no node_attributes object was provided with a name, use a standard default name
                name = f"node{str(self.id)}"
            else:
                # if a name was specified for use via the node_attributes parameter, use it
                name = node_attributes.name
        self.name = name

    @property
    def name(self):
        return self.node_attributes.name

    @name.setter
    def name(self, value):
        self.node_attributes.name = value

    def __repr__(self):
        return f"{self.node_attributes.name} - ({self.node_attributes.latitude},{self.node_attributes.longitude})"

    def has_individual_property(self, property_key: str) -> bool:
        return self.individual_properties.has_individual_property(property_key=property_key)

    def get_individual_property(self, property_key: str) -> IndividualProperty:
        if not self.has_individual_property(property_key=property_key):
            raise Exception(f"No such individual property {property_key} exists in node: {self.id}")
        ip_by_name = {ip.property: ip for ip in self.individual_properties}
        return ip_by_name[property_key]

    def to_dict(self) -> dict:
        """
        Translate node structure to a dictionary for EMOD
        """
        d = {"NodeID": self.id,
             "NodeAttributes": self.node_attributes.to_dict()}

        if self.individual_attributes:
            d["IndividualAttributes"] = self.individual_attributes.to_dict()

        if self.individual_properties:
            ip_dict = {"IndividualProperties": []}
            for ip in self.individual_properties:
                ip_dict["IndividualProperties"].append(ip.to_dict())
            d.update(ip_dict)

        d.update(self.meta)
        return d

    def to_tuple(self):
        """
        Returns a tuple of (latitude, longitude, and initial population)
        """
        return self.node_attributes.latitude, self.node_attributes.longitude, self.node_attributes.initial_population

    @property
    def id(self):
        """ Returns the node ID"""
        return (
            self.forced_id
            if self.forced_id is not None
            else nodeid_from_lat_lon(self.node_attributes.latitude, self.node_attributes.longitude, self.res_in_degrees)
        )

    @classmethod
    def init_resolution_from_file(cls, fn):
        if "30arcsec" in fn:
            cls.res_in_degrees = 30 / 3600.0
        elif "2_5arcmin" in fn:
            cls.res_in_degrees = 2.5 / 30
        else:
            raise Exception("Don't recognize resolution from demographics filename")

    @classmethod
    def from_data(cls,
                  data: dict) -> Tuple["Node", List[Callable]]:
        """
        Function used to create the node object from data (most likely coming from a demographics file)

        Args:
            data (dict): Contains the node definitions

        Returns:
            A New Node object and a list of known implicit functions needed for config compatibility.
        """
        implicit_functions = []

        nodeid = data["NodeID"]
        node_attributes_dict = dict(data.get("NodeAttributes"))
        attributes = data["NodeAttributes"]
        name = attributes.pop("FacilityName", nodeid)
        individual_attributes_dict = data.get("IndividualAttributes")
        individual_properties_dict = data.get("IndividualProperties")

        individual_properties = IndividualProperties()
        if individual_properties_dict:
            for ip in individual_properties_dict:
                individual_properties.add(IndividualProperty(property=ip["Property"],
                                                             values=ip["Values"],
                                                             transitions=ip["Transitions"],
                                                             initial_distribution=ip["Initial_Distribution"]))
        individual_attributes = None
        if individual_attributes_dict:
            individual_attributes, implicit_functions = IndividualAttributes().from_dict(individual_attributes_dict)

        node_attributes = None
        if node_attributes_dict:
            node_attributes = NodeAttributes().from_dict(node_attributes_dict)

        # Create the node and return plus any known necessary implicit functions
        node = cls(node_attributes.latitude, node_attributes.longitude, node_attributes.initial_population,
                   name=name, forced_id=nodeid, individual_attributes=individual_attributes,
                   individual_properties=individual_properties, node_attributes=node_attributes)
        return node, implicit_functions

    @property
    def pop(self):
        """ initial population """
        return self.node_attributes.initial_population

    @pop.setter
    def pop(self, value):
        self.node_attributes.initial_population = value

    @property
    def lon(self):
        """ longitude """
        return self.node_attributes.longitude

    @lon.setter
    def lon(self, value):
        self.node_attributes.longitude = value

    @property
    def lat(self):
        """ latitude """
        return self.node_attributes.latitude

    @lat.setter
    def lat(self, value):
        self.node_attributes.latitude = value

    @property
    def birth_rate(self):
        """ birth rate in births per person per day"""
        return self.node_attributes.birth_rate

    @birth_rate.setter
    def birth_rate(self, value):
        self.node_attributes.birth_rate = value

    def _set_individual_attributes(self, ind_attribute: IndividualAttributes):
        self.individual_attributes = ind_attribute

    def _set_individual_properties(self, ind_properties: IndividualProperties):
        self.individual_properties = ind_properties

    def _add_individual_property(self, ind_property: IndividualProperty):
        self.individual_properties.add(ind_property)

    def _set_node_attributes(self, node_attributes: NodeAttributes):
        self.node_attributes = node_attributes

    #
    # Any of the following _set_*() functions that appear to be missing are not valid (e.g. prevalence complex dist)
    #

    def _set_age_complex_distribution(self, distribution: AgeDistribution):
        """
        Properly sets a complex age distribution and unsets a simple one for consistency (just in case one was set).
        For details on complex distributions, see:
        https://docs.idmod.org/projects/emod-generic/en/latest/parameter-demographics.html#complex-distributions

        Args:
            distribution: The complex age distribution to set

        Returns:
            Nothing
        """
        self.individual_attributes.age_distribution_flag = None
        self.individual_attributes.age_distribution1 = None
        self.individual_attributes.age_distribution2 = None
        self.individual_attributes.age_distribution = distribution

    def _set_age_simple_distribution(self, flag: int, value1: float, value2: float):
        """
        Properly sets a simple age distribution and unsets a complex one for consistency (just in case one was set).
        For details on the simple distribution flag and value meanings, see:
        https://docs.idmod.org/projects/emod-generic/en/latest/parameter-demographics.html#simple-distributions

        Args:
            flag: simple distribution flag determines the type of simple distribution to use
            value1: simple distribution type-dependent parameter number 1
            value2: simple distribution type-dependent parameter number 2

        Returns:
            Nothing
        """
        self.individual_attributes.age_distribution_flag = flag
        self.individual_attributes.age_distribution1 = value1
        self.individual_attributes.age_distribution2 = value2
        self.individual_attributes.age_distribution = None

    def _set_susceptibility_complex_distribution(self, distribution: SusceptibilityDistribution):
        """
        Properly sets a complex susceptibility distribution and unsets a simple one for consistency (just in case one
        was set). For details on complex distributions, see:
        https://docs.idmod.org/projects/emod-generic/en/latest/parameter-demographics.html#complex-distributions

        Args:
            distribution: The complex susceptibility distribution to set

        Returns:
            Nothing
        """
        self.individual_attributes.susceptibility_distribution_flag = None
        self.individual_attributes.susceptibility_distribution1 = None
        self.individual_attributes.susceptibility_distribution2 = None
        self.individual_attributes.susceptibility_distribution = distribution

    def _set_susceptibility_simple_distribution(self, flag: int, value1: float, value2: float):
        """
        Properly sets a simple susceptibility distribution and unsets a complex one for consistency (just in case one
        was set). For details on the simple distribution flag and value meanings, see:
        https://docs.idmod.org/projects/emod-generic/en/latest/parameter-demographics.html#simple-distributions

        Args:
            flag: simple distribution flag determines the type of simple distribution to use
            value1: simple distribution type-dependent parameter number 1
            value2: simple distribution type-dependent parameter number 2

        Returns:
            Nothing
        """
        self.individual_attributes.susceptibility_distribution_flag = flag
        self.individual_attributes.susceptibility_distribution1 = value1
        self.individual_attributes.susceptibility_distribution2 = value2
        self.individual_attributes.susceptibility_distribution = None

    def _set_prevalence_simple_distribution(self, flag: int, value1: float, value2: float):
        """
        Properly sets a simple prevalence distribution. For details on the simple distribution flag and value meanings,
        see:
        https://docs.idmod.org/projects/emod-generic/en/latest/parameter-demographics.html#simple-distributions

        Args:
            flag: simple distribution flag determines the type of simple distribution to use
            value1: simple distribution type-dependent parameter number 1
            value2: simple distribution type-dependent parameter number 2

        Returns:
            Nothing
        """
        self.individual_attributes.prevalence_distribution_flag = flag
        self.individual_attributes.prevalence_distribution1 = value1
        self.individual_attributes.prevalence_distribution2 = value2

    def _set_migration_heterogeneity_simple_distribution(self, flag: int, value1: float, value2: float):
        """
        Properly sets a simple migration heterogeneity distribution. For details on the simple distribution flag and
        value meanings, see:
        https://docs.idmod.org/projects/emod-generic/en/latest/parameter-demographics.html#simple-distributions

        Args:
            flag: simple distribution flag determines the type of simple distribution to use
            value1: simple distribution type-dependent parameter number 1
            value2: simple distribution type-dependent parameter number 2

        Returns:
            Nothing
        """
        self.individual_attributes.migration_heterogeneity_distribution_flag = flag
        self.individual_attributes.migration_heterogeneity_distribution1 = value1
        self.individual_attributes.migration_heterogeneity_distribution2 = value2

    def _set_mortality_complex_distribution(self, distribution: MortalityDistribution):
        """
        Properly sets a complex mortality distribution. For details on complex distributions, see:
        https://docs.idmod.org/projects/emod-generic/en/latest/parameter-demographics.html#complex-distributions

        Args:
            distribution: The complex mortality distribution to set

        Returns:
            Nothing
        """
        self.individual_attributes.mortality_distribution = distribution

    def _set_mortality_female_complex_distribution(self, distribution: MortalityDistribution):
        """
        Properly sets a complex female mortality distribution. For details on complex distributions, see:
        https://docs.idmod.org/projects/emod-generic/en/latest/parameter-demographics.html#complex-distributions

        Args:
            distribution: The complex female mortality distribution to set

        Returns:
            Nothing
        """
        self.individual_attributes.mortality_distribution_female = distribution

    def _set_mortality_male_complex_distribution(self, distribution: MortalityDistribution):
        """
        Properly sets a complex male mortality distribution. For details on complex distributions, see:
        https://docs.idmod.org/projects/emod-generic/en/latest/parameter-demographics.html#complex-distributions

        Args:
            distribution: The complex male mortality distribution to set

        Returns:
            Nothing
        """
        self.individual_attributes.mortality_distribution_male = distribution

    # malaria only
    # TODO: Move to emodpy-malaria?
    #  https://github.com/InstituteforDiseaseModeling/emodpy-malaria-old/issues/707
    def _set_innate_immune_simple_distribution(self, flag: int, value1: float, value2: float):
        """
        Properly sets a simple innate immune distribution. For details on the simple distribution flag and value
        meanings, see:
        https://docs.idmod.org/projects/emod-generic/en/latest/parameter-demographics.html#simple-distributions

        Args:
            flag: simple distribution flag determines the type of simple distribution to use
            value1: simple distribution type-dependent parameter number 1
            value2: simple distribution type-dependent parameter number 2

        Returns:
            Nothing
        """
        self.individual_attributes.innate_immune_distribution_flag = flag
        self.individual_attributes.innate_immune_distribution1 = value1
        self.individual_attributes.innate_immune_distribution2 = value2

    # malaria only
    # TODO: Move to emodpy-malaria?
    #  https://github.com/InstituteforDiseaseModeling/emodpy-malaria-old/issues/707
    def _set_risk_simple_distribution(self, flag: int, value1: float, value2: float):
        """
        Properly sets a simple risk distribution. For details on the simple distribution flag and value meanings, see:
        https://docs.idmod.org/projects/emod-generic/en/latest/parameter-demographics.html#simple-distributions

        Args:
            flag: simple distribution flag determines the type of simple distribution to use
            value1: simple distribution type-dependent parameter number 1
            value2: simple distribution type-dependent parameter number 2

        Returns:
            Nothing
        """
        self.individual_attributes.risk_distribution_flag = flag
        self.individual_attributes.risk_distribution1 = value1
        self.individual_attributes.risk_distribution2 = value2

    # HIV only
    def _set_fertility_complex_distribution(self, distribution: FertilityDistribution):
        """
        Properly sets a complex fertility distribution. For details on complex distributions, see:
        https://docs.idmod.org/projects/emod-generic/en/latest/parameter-demographics.html#complex-distributions

        Args:
            distribution: The complex fertility distribution to set

        Returns:
            Nothing
        """
        self.individual_attributes.fertility_distribution = distribution


def get_xpix_ypix(nodeid):
    """ Get pixel position from nodid. Inverse of :py:func:`nodeid_from_lat_lon` """
    ypix = (nodeid - 1) & 2 ** 16 - 1
    xpix = (nodeid - 1) >> 16 # shift bits to the right
    return (xpix, ypix)


def lat_lon_from_nodeid(nodeid, res_in_deg=Node.res_in_degrees):
    """ Inverse of :py:func:`nodeid_from_lat_lon` """
    xpix, ypix = get_xpix_ypix(nodeid)
    lat = (0.5 + ypix) * res_in_deg - 90.0
    lon = (0.5 + xpix) * res_in_deg - 180.0
    return (lat, lon)


def xpix_ypix_from_lat_lon(lat, lon, res_in_deg=Node.res_in_degrees):
    """ Pixel position (origin is -90°N and -180°E). No modular arithmentic is done."""
    xpix = int(math.floor((lon + 180.0) / res_in_deg))
    ypix = int(math.floor((lat + 90.0) / res_in_deg))
    return xpix, ypix


def nodeid_from_lat_lon(lat, lon, res_in_deg=Node.res_in_degrees):
    """ Generate unique identifier from lat, lon. Inverse of  :py:func:`lat_lon_from_nodeid` """
    xpix, ypix = xpix_ypix_from_lat_lon(lat, lon, res_in_deg)
    nodeid = (xpix << 16) + ypix + 1
    return nodeid
