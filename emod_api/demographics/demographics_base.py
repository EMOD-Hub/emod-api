import warnings
from collections import Counter
from functools import partial
from collections.abc import Iterable
from typing import Union, Callable

from emod_api.demographics.age_distribution import AgeDistribution
from emod_api.demographics.base_input_file import BaseInputFile
from emod_api.demographics.fertility_distribution import FertilityDistribution
from emod_api.demographics.mortality_distribution import MortalityDistribution
from emod_api.demographics.node import Node
from emod_api.demographics.demographic_exceptions import InvalidNodeIdException
from emod_api.demographics.properties_and_attributes import IndividualProperty, NodeProperty, NodeProperties
from emod_api.demographics.susceptibility_distribution import SusceptibilityDistribution
from emod_api.utils.distributions.base_distribution import BaseDistribution
from emod_api.utils.emod_enum import BirthRateDependence


class DemographicsBase(BaseInputFile):
    """
    Base class for :py:obj:`emod_api:emod_api.demographics.Demographics` and
        :py:obj:`emod_api:emod_api.demographics.DemographicsOverlay`.
    """

    DEFAULT_NODE_NAME = 'default_node'

    class UnknownNodeException(ValueError):
        pass

    class DuplicateNodeIdException(Exception):
        pass

    class DuplicateNodeNameException(Exception):
        pass

    def __init__(self, nodes: list[Node], idref: str = None, default_node: Node = None):
        """
        Passed-in default nodes are optional. If one is not passed in, one will be created.
        """
        super().__init__(idref=idref)
        self.nodes = nodes
        self.node_properties = NodeProperties()
        self.implicits = list()
        self.migration_files = list()

        # verify that the provided non-default nodes have ids > 0
        for node in self.nodes:
            if node.id <= 0:
                raise InvalidNodeIdException(f"Non-default nodes must have integer ids > 0 . Found id: {node.id}")

        # Build the default node if not provided and then perform some setup/verification
        default_node = self._generate_default_node() if default_node is None else default_node
        self.default_node = default_node
        self.default_node.name = self.DEFAULT_NODE_NAME
        if self.default_node.id != 0:
            raise InvalidNodeIdException(f"Default nodes must have an id of 0. It is {self.default_node.id} .")
        self.metadata = self.generate_headers()
        # TODO: remove the following setting of birth_rate on the default node once this EMOD binary issue is fixed
        #  https://github.com/InstituteforDiseaseModeling/DtkTrunk/issues/4009
        if self.default_node.birth_rate is None:
            self.default_node.birth_rate = 0

        # enforce unique node ids and names
        self.verify_demographics_integrity()

    def _generate_default_node(self) -> Node:
        default_node = Node(lat=0, lon=0, pop=0, name=self.DEFAULT_NODE_NAME, forced_id=0)
        # TODO: remove the following setting of birth_rate on the default node once this EMOD binary issue is fixed
        #  https://github.com/InstituteforDiseaseModeling/DtkTrunk/issues/4009
        default_node.birth_rate = 0
        return default_node

    def apply_overlay(self, overlay_nodes: list[Node]) -> None:
        """
        Overlays a set of nodes onto the demographics object. Only overlay nodes with ids matching current demographic
        node_ids will be overlayed (extending/overriding exisiting node data).

        Args:
            overlay_nodes (list[Node]): a list of Node objects that will overlay/override data in the demographics
                object.

        Returns:
            Nothing
        """
        existing_nodes_by_id = self._all_nodes_by_id
        for overlay_node in overlay_nodes:
            if overlay_node.id in existing_nodes_by_id:
                self.get_node_by_id(node_id=overlay_node.id).update(overlay_node)

    @property
    def node_ids(self):
        """
        Return the list of (geographic) node ids.
        """
        return [node.id for node in self.nodes]

    @property
    def node_count(self):
        """
        Return the number of (geographic) nodes.
        """
        message = "node_count is a deprecated property of Node objects, use len(demog.nodes) instead."
        warnings.warn(message=message, category=DeprecationWarning, stacklevel=2)
        return len(self.nodes)

    def get_node(self, nodeid: int) -> Node:
        """
        Return the node with node.id equal to nodeid.

        Args:
            nodeid: an id to use in retrieving the requested Node object. None or 0 for 'the default node'.

        Returns:
            a Node object
        """
        message = "get_node() is a deprecated function of Node objects, use get_node_by_id() instead. " \
                  "(For example, demographics.get_node_by_id(node_id=4))"
        warnings.warn(message=message, category=DeprecationWarning, stacklevel=2)
        return self.get_node_by_id(node_id=nodeid)

    def verify_demographics_integrity(self):
        """
        One stop shopping for making sure a demographics object doesn't have known invalid settings.
        """
        self._verify_node_id_uniqueness()
        self._verify_node_name_uniqueness()

    @staticmethod
    def _duplicates_check(items: Iterable) -> list:
        """
        Simple function that detects and returns the duplicates in an provide iterable.
        Args:
            items: a collection of items to search for duplicates

        Returns: a list of duplicated items from the provided list
        """
        usage_count = Counter(items)
        return [item for item in usage_count.keys() if usage_count[item] > 1]

    def _verify_node_id_uniqueness(self):
        nodes = self._all_nodes
        node_ids = [node.id for node in nodes]
        duplicate_items = self._duplicates_check(items=node_ids)
        if len(duplicate_items) > 0:
            duplicate_items_str = [str(item) for item in duplicate_items]
            duplicates_str = ", ".join(duplicate_items_str)
            raise self.DuplicateNodeIdException(f"Duplicate node ids detected: {duplicates_str}")

    def _verify_node_name_uniqueness(self):
        nodes = self._all_nodes
        node_names = [node.name for node in nodes if node.name is not None]
        duplicate_items = self._duplicates_check(items=node_names)
        if len(duplicate_items) > 0:
            duplicate_items_str = [str(item) for item in duplicate_items]
            duplicates_str = ", ".join(duplicate_items_str)
            raise self.DuplicateNodeNameException(f"Duplicate node names detected: {duplicates_str}")

    @property
    def _all_nodes(self) -> list[Node]:
        all_nodes = self.nodes + [self.default_node]
        return all_nodes

    @property
    def _all_node_names(self) -> list[int]:
        return [node.name for node in self._all_nodes]

    @property
    def _all_nodes_by_name(self) -> dict[int, Node]:
        return {node.name: node for node in self._all_nodes}

    @property
    def _all_node_ids(self) -> list[int]:
        return [node.id for node in self._all_nodes]

    @property
    def _all_nodes_by_id(self) -> dict[int, Node]:
        return {node.id: node for node in self._all_nodes}

    def get_node_by_id(self, node_id: int) -> Node:
        """
        Returns the Node object requested by its node id.

        Args:
            node_id: a node_id to use in retrieving the requested Node object. None or 0 for 'the default node'.

        Returns:
            a Node object
        """
        return list(self.get_nodes_by_id(node_ids=[node_id]).values())[0]

    def get_nodes_by_id(self, node_ids: list[int]) -> dict[int, Node]:
        """
        Returns the Node objects requested by their node id.

        Args:
            node_ids: a list of node ids to use in retrieving Node objects. None or 0 for 'the default node'.

        Returns:
            a dict with id: node entries
        """
        # replace a None id (default node) request with 0
        if node_ids is None:
            node_ids = [0]
        if None in node_ids:
            node_ids.remove(None)
            node_ids.append(0)

        missing_node_ids = [node_id for node_id in node_ids if node_id not in self._all_node_ids]
        if len(missing_node_ids) > 0:
            msg = ', '.join([str(node_id) for node_id in missing_node_ids])
            raise self.UnknownNodeException(f"The following node id(s) were requested but do not exist in this demographics "
                                            f"object:\n{msg}")
        requested_nodes = {node_id: node for node_id, node in self._all_nodes_by_id.items() if node_id in node_ids}
        return requested_nodes

    def get_node_by_name(self, node_name: str) -> Node:
        """
        Returns the Node object requested by its node name.

        Args:
            node_name: a node_name to use in retrieving the requested Node object. None for 'the default node'.

        Returns:
            a Node object
        """
        return list(self.get_nodes_by_name(node_names=[node_name]).values())[0]

    def get_nodes_by_name(self, node_names: list[str]) -> dict[str, Node]:
        """
        Returns the Node objects requested by their node name.

        Args:
            node_names: a list of node names to use in retrieving Node objects. None for 'the default node'.

        Returns:
            a dict with name: node entries
        """
        # replace a None name (default node) request with the default node's name
        if node_names is None:
            node_names = [self.default_node.name]
        if None in node_names:
            node_names.remove(None)
            node_names.append(self.default_node.name)

        missing_node_names = [node_name for node_name in node_names if node_name not in self._all_node_names]
        if len(missing_node_names) > 0:
            msg = ', '.join([str(node_name) for node_name in missing_node_names])
            raise self.UnknownNodeException(f"The following node name(s) were requested but do not exist in this demographics "
                                            f"object:\n{msg}")
        requested_nodes = {node_name: node for node_name, node in self._all_nodes_by_name.items()
                           if node_name in node_names}
        return requested_nodes

    def set_demographics_filenames(self, filenames: list[str]):
        """
        Set paths to demographic file.

        Args:
            filenames: Paths to demographic files.
        """
        from emod_api.demographics.implicit_functions import _set_demographic_filenames

        self.implicits.append(partial(_set_demographic_filenames, filenames=filenames))

    def to_dict(self) -> dict:
        self.verify_demographics_integrity()
        demographics_dict = {
            'Defaults': self.default_node.to_dict(),
            'Nodes': [node.to_dict() for node in self.nodes],
            'Metadata': self.metadata
        }
        demographics_dict["Metadata"]["NodeCount"] = len(self.nodes)
        if self.node_properties:
            demographics_dict["NodeProperties"] = self.node_properties.to_dict()
        return demographics_dict

    def set_birth_rate(self, rate: float, node_ids: list[int] = None, birth_rate_dependence: Union[str, BirthRateDependence] = "POPULATION_DEP_RATE"):
        """
        Sets the BirthRate on the target node(s) and configures how EMOD interprets it via
        Birth_Rate_Dependence. Automatically registers the corresponding config implicit.

        Args:
            rate: The birth rate to set on the target node(s). The units of this value depend on the
                birth_rate_dependence setting, see below.
            node_ids: Node id(s) to apply rate to. ``None`` or ``0`` targets the default node. Please note that the
                birth rate dependence setting will be applied to all nodes, regardless of which node(s) the birth
                rate is applied to.
            birth_rate_dependence: How EMOD uses the BirthRate value.
                Accepts a :class:`~emod_api.demographics.implicit_functions.BirthRateDependence`
                member or its string value. Defaults to ``POPULATION_DEP_RATE``.
                - ``FIXED_BIRTH_RATE`` — 'rate' is used as an absolute daily birth rate with which new individuals are born.
                    units: number of births per year
                - ``POPULATION_DEP_RATE`` — 'rate' is scaled by node population to determine the daily birth rate.
                    units: number of births per 1000 people per year
                    max: 1000 (equivalent to 1 birth per year for every person in the population)
                - ``DEMOGRAPHIC_DEP_RATE`` — 'rate' is scaled by number of possible mothers (female population in
                    fertility age range of 15–44 years).
                    units: number of births per 8 fertile women per year
                    max: 8 (equivalent to 1 birth per year for every possible mother in the population)
                - ``INDIVIDUAL_PREGNANCIES`` — like DEMOGRAPHIC_DEP_RATE, but pregnancies are
                    assigned individually with a 40-week gestation period. An individual fertile female person becomes
                    pregnant based on the birth rate and then gives birth 40 weeks later. This setup is required for
                    using IsPregnant targeting in campaigns.
                    units: number of pregnancies per 8 fertile women per year
                    max: 8 (equivalent to 1 pregnancy per year for every possible mother in the population)

        """
        from emod_api.demographics.implicit_functions import _set_birth_rate_dependence

        if not isinstance(birth_rate_dependence, BirthRateDependence):
            try:
                birth_rate_dependence = BirthRateDependence(birth_rate_dependence)
            except ValueError:
                raise ValueError(
                    f"Invalid birth_rate_dependence {birth_rate_dependence!r}. "
                    f"Valid options: {[e.value for e in BirthRateDependence]}")

        if birth_rate_dependence == BirthRateDependence.POPULATION_DEP_RATE:
            if rate > 1000:
                raise ValueError(f"Births per 1000 people per year cannot exceed 1000. Provided rate: {rate}")
            rate = rate / 365 / 1000  # converting to per day per 1000 people
        elif birth_rate_dependence in (BirthRateDependence.DEMOGRAPHIC_DEP_RATE,
                                       BirthRateDependence.INDIVIDUAL_PREGNANCIES):
            if rate > 8:
                raise ValueError(f"Births per 8 fertile women per year cannot exceed 8. Provided rate: {rate}")
            rate = rate / 365 / 8  # converting to per day per 8 fertile women

        nodes = self.get_nodes_by_id(node_ids=node_ids)
        for _, node in nodes.items():
            node.birth_rate = rate
        self.implicits.append(partial(_set_birth_rate_dependence,
                                      birth_rate_dependence=birth_rate_dependence))

    #
    # These distribution setters accept either a simple or complex distribution
    #
    def set_age_distribution(self,
                             distribution: Union[BaseDistribution, AgeDistribution],
                             node_ids: list[int] = None) -> None:
        """
        Set the distribution from which the initial ages of the population will be drawn. At initialization, each person
        will be randomly assigned an age from the given distribution. Automatically handles any necessary config
        updates.

        Args:
            distribution: The distribution to set. Can either be a BaseDistribution object for a simple distribution
                or AgeDistribution object for complex.
                Note: When using BaseDistribution, the parameter ages are in days. Ex: UniformDistribution(0, 365*50) for
                    a uniform distribution of ages between 0 and 50 years. When using AgeDistribution, the parameter
                    ages are in years.
            node_ids: The node id(s) to apply changes to. None or 0 means the default node.

        Returns:
            Nothing
        """
        from emod_api.demographics.implicit_functions import _set_age_simple, _set_age_complex

        self._set_distribution(distribution=distribution,
                               use_case='age',
                               simple_distribution_implicits=[_set_age_simple],
                               complex_distribution_implicits=[_set_age_complex],
                               node_ids=node_ids)

    def set_susceptibility_distribution(self,
                                        distribution: Union[BaseDistribution, SusceptibilityDistribution],
                                        node_ids: list[int] = None) -> None:
        """
        Set a distribution that will impact the probability that a person will acquire an infection based on immunity.
        The SusceptibilityDistribution is used to define an age-based distribution from which a probability is selected
        to determine if a person is susceptible or not. The older ages of the distribution are only used during
        initialization. Automatically handles any necessary config updates. Susceptibility distributions are NOT
        compatible or supported for Malaria or HIV simulations.


        Args:
            distribution: The distribution to set. Can either be a BaseDistribution object for a simple distribution
                or SusceptibilityDistribution object for complex.
            node_ids: The node id(s) to apply changes to. None or 0 means the default node.

        Returns:
            Nothing
        """
        from emod_api.demographics.implicit_functions import _set_suscept_simple, _set_suscept_complex

        self._set_distribution(distribution=distribution,
                               use_case='susceptibility',
                               simple_distribution_implicits=[_set_suscept_simple],
                               complex_distribution_implicits=[_set_suscept_complex],
                               node_ids=node_ids)

    #
    # These distribution setters only accept simple distributions
    #

    def set_prevalence_distribution(self,
                                    distribution: BaseDistribution,
                                    node_ids: list[int] = None) -> None:
        """
        Sets a prevalence distribution on the demographics object. Automatically handles any necessary config updates.
        Initial prevalence distributions are not compatible with HIV EMOD simulations.

        Args:
            distribution: The distribution to set. Must be a BaseDistribution object for a simple distribution.
            node_ids: The node id(s) to apply changes to. None or 0 means the default node.

        Returns:
            Nothing
        """
        from emod_api.demographics.implicit_functions import _set_init_prev

        self._set_distribution(distribution=distribution,
                               use_case='prevalence',
                               simple_distribution_implicits=[_set_init_prev],
                               node_ids=node_ids)

    def set_migration_heterogeneity_distribution(self,
                                                 distribution: BaseDistribution,
                                                 node_ids: list[int] = None) -> None:
        """
        Sets a migration heterogeneity distribution on the demographics object. Automatically handles any necessary
        config updates.

        Args:
            distribution: The distribution to set. Must be a BaseDistribution object for a simple distribution.
            node_ids: The node id(s) to apply changes to. None or 0 means the default node.

        Returns:
            Nothing
        """

        from emod_api.demographics.implicit_functions import _set_migration_model_fixed_rate
        from emod_api.demographics.implicit_functions import _set_enable_migration_model_heterogeneity

        implicits = [_set_migration_model_fixed_rate, _set_enable_migration_model_heterogeneity]
        self._set_distribution(distribution=distribution,
                               use_case='migration_heterogeneity',
                               simple_distribution_implicits=implicits,
                               node_ids=node_ids)

    #
    # These distribution setters only accept complex distributions
    #

    def set_mortality_distribution(self,
                                   distribution_male: MortalityDistribution,
                                   distribution_female: MortalityDistribution,
                                   node_ids: list[int] = None) -> None:
        """
        Sets the gendered mortality distributions on the demographics object. Automatically handles any necessary
        config updates.

        Args:
            distribution_male: The male MortalityDistribution to set. Must be a MortalityDistribution object for a
                complex distribution.
            distribution_female: The female MortalityDistribution to set. Must be a MortalityDistribution object for a
                complex distribution.
            node_ids: The node id(s) to apply changes to. None or 0 means the default node.

        Returns:
            Nothing
        """

        # Note that we only need to set the implicit function once, even though we set two distributions.
        from emod_api.demographics.implicit_functions import _set_enable_natural_mortality
        from emod_api.demographics.implicit_functions import _set_mortality_age_gender_year

        implicits = [_set_enable_natural_mortality, _set_mortality_age_gender_year]
        self._set_distribution(distribution=distribution_male,
                               use_case='mortality_male',
                               complex_distribution_implicits=implicits,
                               node_ids=node_ids)
        self._set_distribution(distribution=distribution_female,
                               use_case='mortality_female',
                               node_ids=node_ids)

    def _set_distribution(self,
                          distribution: Union[
                              BaseDistribution,
                              AgeDistribution,
                              SusceptibilityDistribution,
                              FertilityDistribution,
                              MortalityDistribution],
                          use_case: str,
                          simple_distribution_implicits: list[Callable] = None,
                          complex_distribution_implicits: list[Callable] = None,
                          node_ids: list[int] = None) -> None:
        """
        A common core function for setting simple and complex distributions for all uses in EMOD demographics. This
        should not be called directly by users.

        Args:
            distribution: The distribution object to set. If it is a BaseDistribution object, a simple distribution
                will be set on the demographics object. If it is of any other allowed type, a complex distribution is
                set.
            use_case: A string used to identify which function to call on specified nodes to properly configure the
                specified distribution.
            simple_distribution_implicits: for simple distributions, a list of functions to call at config build-time to
                ensure the specified distribution is utilized properly.
            complex_distribution_implicits: for complex distributions, a list of functions to call at config build-time
                to ensure the specified distribution is utilized properly.
            node_ids: The node id(s) to apply changes to. None or 0 means the default node.

        Returns:
            Nothing
        """
        if isinstance(distribution, BaseDistribution):
            distribution_values = distribution.get_demographic_distribution_parameters()
            function_name = f"_set_{use_case}_simple_distribution"
            implicit_calls = simple_distribution_implicits
        else:
            function_name = f"_set_{use_case}_complex_distribution"
            distribution_values = {'distribution': distribution}
            implicit_calls = complex_distribution_implicits

        nodes = self.get_nodes_by_id(node_ids=node_ids)
        for _, node in nodes.items():
            getattr(node, function_name)(**distribution_values)

        # ensure the config is properly set up to know about this distribution
        if implicit_calls is not None:
            self.implicits.extend(implicit_calls)

    def add_individual_property(self,
                                property: str,
                                values: Union[list[str], list[float]] = None,
                                initial_distribution: list[float] = None,
                                node_ids: list[int] = None,
                                overwrite_existing: bool = False) -> None:
        """
        Adds a new individual property or replace values on an already-existing property in a demographics object.

        Individual properties act as 'labels' on model agents that can be used for identifying and targeting
        subpopulations in campaign elements and reports. For example, model agents may be given a property
        ('Accessibility') that labels them as either having access to health care (value: 'Yes') or not (value: 'No').

        Another example: a property ('Risk') could label model agents as belonging to a spectrum of value categories
        (values: 'HIGH', 'MEDIUM', 'LOW') that govern disease-related behavior.

        Note: EMOD requires individual property key and values (property and values arguments) to be the same across all
            nodes. The initial distributions of individual properties (initial_distribution) can vary across nodes.

        Documentation of individual properties and HINT:
            For malaria, see :doc:`emod-malaria:emod/model-properties`
                    and for HIV, see :doc:`emod-hiv:emod/model-properties`.

        Args:
            property: a new individual property key to add. If property already exists an exception is raised
                unless overwrite_existing is True. 'property' must be the same across all nodes, note above.
            values: A list of valid values for the property key. For example,  ['Yes', 'No'] for an 'Accessibility'
                property key. 'values' must be the same across all nodes, note above.
            initial_distribution: The fractional, between 0 and 1, initial distribution of each valid values entry.
                Order must match values argument. The values must add up to 1.
            node_ids: The node ids to apply changes to. None or 0 means the 'Defaults' node, which will apply to all
                the nodes unless a node has its own individual properties re-definition.
            overwrite_existing: When True, overwrites existing individual properties with the same key. If False,
                raises an exception if the property already exists in the node(s).

        Returns:
            None
        """
        nodes = self.get_nodes_by_id(node_ids=node_ids).values()
        individual_property = IndividualProperty(property=property,
                                                 values=values,
                                                 initial_distribution=initial_distribution)
        for node in nodes:
            if not overwrite_existing and node.has_individual_property(property_key=property):
                raise ValueError(f"Property key '{property}' already present in IndividualProperties list")

            node.individual_properties.add(individual_property=individual_property, overwrite=overwrite_existing)

    def add_node_property(self,
                          property: str,
                          values: list[str],
                          initial_distribution: list[float] = None,
                          overwrite_existing: bool = False) -> None:
        """
        Adds a new node property to the demographics object.

        Node properties are top-level in the demographics file and define property labels
        on nodes that can be used for identifying and targeting subsets of nodes in campaign
        elements and reports. For example, nodes may be given a property ('Place') with
        values like 'URBAN' or 'RURAL'.

        Each node is randomly assigned a value from the ``initial_distribution`` at
        initialization. To override the drawn value for specific nodes, use
        ``set_node_property_values``.

        Args:
            property: A node property key to add (e.g. ``'Place'``).
            values: A list of valid string values for the property (e.g. ``['URBAN', 'RURAL']``).
            initial_distribution: The fractional (0 to 1) initial distribution of each value.
                Order must match the values argument. Must sum to 1.
            overwrite_existing: When True, overwrites an existing node property with the same
                key. If False, raises an exception if the property already exists.

        Returns:
            None
        """
        node_property = NodeProperty(property=property,
                                     values=values,
                                     initial_distribution=initial_distribution)
        self.node_properties.add(node_property=node_property, overwrite=overwrite_existing)

    def set_node_property_values(self,
                                 node_ids: list[int],
                                 values: list[str]) -> None:
        """
        Set per-node ``NodePropertyValues`` overrides inside ``NodeAttributes``.

        When a node has ``NodePropertyValues`` set, those values override whatever was
        drawn from the ``Initial_Distribution`` of the top-level ``NodeProperties``.

        Args:
            node_ids: The node ids to apply the overrides to. Must be specific node ids
                (not None/0 default node).
            values: A list of ``"Property:Value"`` strings (e.g.
                ``["Place:RURAL", "InterventionStatus:SPRAYED_B"]``).

        Returns:
            None
        """
        nodes = self.get_nodes_by_id(node_ids=node_ids)
        for _, node in nodes.items():
            node.node_attributes.node_property_values = values
