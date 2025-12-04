import warnings
from collections import Counter
from functools import partial
from typing import List, Iterable, Any, Dict, Union, Callable

import numpy as np
import pandas as pd
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from emod_api.demographics.age_distribution import AgeDistribution
from emod_api.demographics.base_input_file import BaseInputFile
from emod_api.demographics.fertility_distribution import FertilityDistribution
from emod_api.demographics.mortality_distribution import MortalityDistribution
from emod_api.demographics.node import Node
from emod_api.demographics.demographic_exceptions import InvalidNodeIdException
from emod_api.demographics.properties_and_attributes import IndividualProperty
from emod_api.demographics.susceptibility_distribution import SusceptibilityDistribution
from emod_api.utils.distributions.base_distribution import BaseDistribution


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

    def __init__(self, nodes: List[Node], idref: str = None, default_node: Node = None):
        """
        Passed-in default nodes are optional. If one is not passed in, one will be created.
        """
        super().__init__(idref=idref)
        self.nodes = nodes
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

    def apply_overlay(self, overlay_nodes: List[Node]) -> None:
        """
        Overlays a set of nodes onto the demographics object. Only overlay nodes with ids matching current demographic
        node_ids will be overlayed (extending/overriding exisiting node data).

        Args:
            overlay_nodes (List[Node]): a list of Node objects that will overlay/override data in the demographics
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
    def _duplicates_check(items: Iterable[Any]) -> List[Any]:
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
        node_names = [node.name for node in nodes]
        duplicate_items = self._duplicates_check(items=node_names)
        if len(duplicate_items) > 0:
            duplicate_items_str = [str(item) for item in duplicate_items]
            duplicates_str = ", ".join(duplicate_items_str)
            raise self.DuplicateNodeNameException(f"Duplicate node names detected: {duplicates_str}")

    @property
    def _all_nodes(self) -> List[Node]:
        all_nodes = self.nodes + [self.default_node]
        return all_nodes

    @property
    def _all_node_names(self) -> List[int]:
        return [node.name for node in self._all_nodes]

    @property
    def _all_nodes_by_name(self) -> Dict[str, Node]:
        return {node.name: node for node in self._all_nodes}

    @property
    def _all_node_ids(self) -> List[int]:
        return [node.id for node in self._all_nodes]

    @property
    def _all_nodes_by_id(self) -> Dict[int, Node]:
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

    def get_nodes_by_id(self, node_ids: List[int]) -> Dict[int, Node]:
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

    def get_nodes_by_name(self, node_names: List[str]) -> Dict[str, Node]:
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

    def set_demographics_filenames(self, filenames: List[str]):
        """
        Set paths to demographic file.

        Args:
            filenames: Paths to demographic files.
        """
        from emod_api.demographics.implicit_functions import _set_demographic_filenames

        self.implicits.append(partial(_set_demographic_filenames, filenames=filenames))

    def infer_natural_mortality(self,
                                file_male,
                                file_female,
                                interval_fit: List[Union[int, float]] = None,
                                which_point='mid',
                                predict_horizon=2050,
                                csv_out=False,
                                n=0,  # I don't know what this means
                                results_scale_factor=1.0 / 365.0) -> [Dict, Dict]:
        """
        Calculate and set the expected natural mortality by age, sex, and year from data, predicting what it would
        have been without disease (HIV-only).
        """
        from collections import OrderedDict
        from sklearn.linear_model import LinearRegression
        from functools import reduce
        from emod_api.demographics.implicit_functions import _set_mortality_age_gender_year
        warnings.warn('infer_natural_mortality() is deprecated. Please use modern country model loading.',
                      DeprecationWarning, stacklevel=2)

        if interval_fit is None:
            interval_fit = [1970, 1980]

        name_conversion_dict = {'Age (x)': 'Age',
                                'Central death rate m(x,n)': 'Mortality_mid',
                                'Age interval (n)': 'Interval',
                                'Period': 'Years'
                                }
        sex_dict = {'Male': 0, 'Female': 1}

        def construct_interval(x, y):
            return x, x + y

        def midpoint(x, y):
            return (x + y) / 2.0

        def generate_dict_order(tuple_list, which_entry=1):
            my_unordered_list = tuple_list.apply(lambda x: x[which_entry])
            dict_to_order = OrderedDict(zip(tuple_list, my_unordered_list))
            return dict_to_order

        def map_year(x_tuple, flag='mid'):
            valid_entries_loc = ['mid', 'end', 'start']

            if flag not in valid_entries_loc:
                raise ValueError('invalid endpoint specified')

            if flag == 'mid':
                return (x_tuple[0] + x_tuple[1]) / 2.0
            elif flag == 'start':
                return x_tuple[0]
            else:
                return x_tuple[1]

        df_mort_male = pd.read_csv(file_male, usecols=name_conversion_dict)
        df_mort_male['Sex'] = 'Male'
        df_mort_female = pd.read_csv(file_female, usecols=name_conversion_dict)
        df_mort_female['Sex'] = 'Female'
        df_mort = pd.concat([df_mort_male, df_mort_female], axis=0)
        df_mort.rename(columns=name_conversion_dict, inplace=True)
        df_mort['Years'] = df_mort['Years'].apply(lambda x: tuple(
            [float(zz) for zz in x.split('-')]))  # this might be a bit too format specific (ie dashes in input)

        # log transform the data and drop unneeded columns
        df_mort['log_Mortality_mid'] = df_mort['Mortality_mid'].apply(lambda x: np.log(x))
        df_mort['Age'] = df_mort[['Age', 'Interval']].apply(lambda zz: construct_interval(*zz), axis=1)

        year_order_dict = generate_dict_order(df_mort['Years'])
        age_order_dict = generate_dict_order(df_mort['Age'])
        df_mort['sortby2'] = df_mort['Age'].map(age_order_dict)
        df_mort['sortby1'] = df_mort['Sex'].map(sex_dict)
        df_mort['sortby3'] = df_mort['Years'].map(year_order_dict)
        df_mort.sort_values(['sortby1', 'sortby2', 'sortby3'], inplace=True)
        df_mort.drop(columns=['Mortality_mid', 'Interval', 'sortby1', 'sortby2', 'sortby3'], inplace=True)

        # convert to years (and to string for age_list due to really annoying practical slicing reasons
        df_mort['Years'] = df_mort['Years'].apply(lambda x: map_year(x, which_point))
        df_mort['Age'] = df_mort['Age'].apply(lambda x: str(x))
        df_before_time = df_mort[df_mort['Years'].between(0, interval_fit[0])].copy()

        df_mort.set_index(['Sex', 'Age'], inplace=True)
        sex_list = list(set(df_mort.index.get_level_values('Sex')))
        age_list = list(set(df_mort.index.get_level_values('Age')))

        df_list = []
        for sex in sex_list:
            for age in age_list:
                tmp_data = df_mort.loc[(sex, age, slice(None)), :]
                extrap_model = make_pipeline(StandardScaler(with_mean=False), LinearRegression())

                first_extrap_df = tmp_data[tmp_data['Years'].between(interval_fit[0], interval_fit[1])]
                xx = tmp_data[tmp_data['Years'].between(interval_fit[0], predict_horizon)].values[:, 0]

                values = first_extrap_df.values
                extrap_model.fit(values[:, 0].reshape(-1, 1), values[:, 1])

                extrap_predictions = extrap_model.predict(xx.reshape(-1, 1))

                loc_df = pd.DataFrame.from_dict({'Sex': sex, 'Age': age, 'Years': xx, 'Extrap': extrap_predictions})
                loc_df.set_index(['Sex', 'Age', 'Years'], inplace=True)

                df_list.append(loc_df.copy())

        df_e1 = pd.concat(df_list, axis=0)

        df_list_final = [df_mort, df_e1]
        df_total = reduce(lambda left, right: pd.merge(left, right, on=['Sex', 'Age', 'Years']), df_list_final)

        df_total = df_total.reset_index(inplace=False).set_index(['Sex', 'Age'], inplace=False)

        df_total['Extrap'] = df_total['Extrap'].apply(np.exp)
        df_total['Data'] = df_total['log_Mortality_mid'].apply(np.exp)
        df_before_time['Data'] = df_before_time['log_Mortality_mid'].apply(np.exp)

        df_before_time.set_index(['Sex', 'Age'], inplace=True)
        df_total = pd.concat([df_total, df_before_time], axis=0, join='outer', sort=True)

        df_total.reset_index(inplace=True)
        df_total['sortby2'] = df_total['Age'].map(age_order_dict)
        df_total['sortby1'] = df_total['Sex'].map(sex_dict)
        df_total.sort_values(by=['sortby1', 'sortby2', 'Years'], inplace=True)
        df_total.drop(columns=['sortby1', 'sortby2'], inplace=True)

        estimates_list = []
        estimates_list.append(df_total.copy())
        # estimates_list = [df_total.copy()] alternative

        def min_not_nan(x_list):
            loc_in = list(filter(lambda x: not np.isnan(x), x_list))
            return np.min(loc_in)

        # This was in another function before
        df = estimates_list[n]
        df['FE'] = df[['Data', 'Extrap']].apply(min_not_nan, axis=1)
        df['Age'] = df['Age'].apply(lambda x: int(x.split(',')[1].split(')')[0]))
        male_df = df[df['Sex'] == 'Male']
        female_df = df[df['Sex'] == 'Female']

        male_df.set_index(['Sex', 'Age', 'Years'], inplace=True)
        female_df.set_index(['Sex', 'Age', 'Years'], inplace=True)
        male_data = male_df['FE']
        female_data = female_df['FE']

        male_data = male_data.unstack(-1)
        male_data.sort_index(level='Age', inplace=True)
        female_data = female_data.unstack(-1)
        female_data.sort_index(level='Age', inplace=True)

        years_out_male = list(male_data.columns)
        years_out_female = list(female_data.columns)

        age_out_male = list(male_data.index.get_level_values('Age'))
        age_out_female = list(male_data.index.get_level_values('Age'))

        male_output = male_data.values
        female_output = female_data.values

        if csv_out:
            male_data.to_csv(f'Male{csv_out}')
            female_data.to_csv(f'Female{csv_out}')

        # TBD: This is the part that should use base file functionality

        dict_female = {'AxisNames': ['age', 'year'],
                       'AxisScaleFactors': [365.0, 1],
                       'AxisUnits': ['years', 'years'],
                       'PopulationGroups': [age_out_female, years_out_female],
                       'ResultScaleFactor': results_scale_factor,
                       'ResultUnits': 'annual deaths per capita',
                       'ResultValues': female_output.tolist()
                       }

        dict_male = {'AxisNames': ['age', 'year'],
                     'AxisScaleFactors': [365.0, 1],
                     'AxisUnits': ['years', 'years'],
                     'PopulationGroups': [age_out_male, years_out_male],
                     'ResultScaleFactor': results_scale_factor,
                     'ResultUnits': 'annual deaths per capita',
                     'ResultValues': male_output.tolist()
                     }
        self.implicits.append(_set_mortality_age_gender_year)
        return dict_female, dict_male

    def to_dict(self) -> Dict:
        self.verify_demographics_integrity()
        demographics_dict = {
            'Defaults': self.default_node.to_dict(),
            'Nodes': [node.to_dict() for node in self.nodes],
            'Metadata': self.metadata
        }
        demographics_dict["Metadata"]["NodeCount"] = len(self.nodes)
        return demographics_dict

    def set_birth_rate(self, rate: float, node_ids: List[int] = None):
        """
        Sets a specified population-dependent birth rate value on the target node(s). Automatically handles any
        necessary config updates.

        Args:
            rate: (float) The birth rate to set in units of births/year/1000-women
            node_ids: (List[int]) The node id(s) to apply changes to. None or 0 means the default node.

        Returns:

        """
        from emod_api.demographics.implicit_functions import _set_population_dependent_birth_rate

        rate = rate / 365 / 1000  # converting to births/day/woman, which is what EMOD internally uses.
        nodes = self.get_nodes_by_id(node_ids=node_ids)
        for _, node in nodes.items():
            node.birth_rate = rate
        self.implicits.append(_set_population_dependent_birth_rate)

    #
    # These distribution setters accept either a simple or complex distribution
    #

    def set_age_distribution(self,
                             distribution: Union[BaseDistribution, AgeDistribution],
                             node_ids: List[int] = None) -> None:
        """
        Set the distribution from which the initial ages of the population will be drawn. At initialization, each person
        will be randomly assigned an age from the given distribution. Automatically handles any necessary config
        updates.

        Args:
            distribution: The distribution to set. Can either be a BaseDistribution object for a simple distribution
                or AgeDistribution object for complex.
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
                                        node_ids: List[int] = None) -> None:
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
                                    node_ids: List[int] = None) -> None:
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
                                                 node_ids: List[int] = None) -> None:
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

    # TODO: This belongs in emodpy-malaria, as that is the one disease that uses this set of parameters.
    #  Should be moved into a subclass of emodpy Demographics inside emodpy-malaria during a 2.0 conversion of it.
    #  https://github.com/EMOD-Hub/emodpy-malaria/issues/126
    # def set_innate_immune_distribution(self,
    #                                    distribution: BaseDistribution,
    #                                    innate_immune_variation_type: str,
    #                                    node_ids: List[int] = None) -> None:
    #     """
    #     Sets a innate immune distribution on the demographics object. Automatically handles any necessary config
    #     updates.
    #
    #     Args:
    #         distribution: The distribution to set. Must be a BaseDistribution object for a simple distribution.
    #         innate_immune_variation_type: the variation type to configure in EMOD. Must be either CYTOKINE_KILLING
    #             or PYROGENIC_THRESHOLD to be compatible with setting a innate immune distribution.
    #         node_ids: The node id(s) to apply changes to. None or 0 means the default node.
    #
    #     Returns:
    #         Nothing
    #     """
    #     from emod_api.demographics.implicit_functions import _set_immune_variation_type_cytokine_killing, \
    #         _set_immune_variation_type_pyrogenic_threshold
    #
    #     valid_types = [self.CYTOKINE_KILLING, self.PYROGENIC_THRESHOLD]
    #     if innate_immune_variation_type == self.CYTOKINE_KILLING:
    #         implicits = [_set_immune_variation_type_cytokine_killing]
    #     elif innate_immune_variation_type == self.PYROGENIC_THRESHOLD:
    #         implicits = [_set_immune_variation_type_pyrogenic_threshold]
    #     else:
    #         valid_types_str = ', '.join(valid_types)
    #         raise ValueError(f'innate_immune_variation_type must be one of: {valid_types_str} ... to allow use of a '
    #                          f'distribution.')
    #
    #     self._set_distribution(distribution=distribution,
    #                            use_case='innate_immune',
    #                            simple_distribution_implicits=implicits,
    #                            node_ids=node_ids)

    #
    # These distribution setters only accept complex distributions
    #

    def set_mortality_distribution(self,
                                   distribution_male: MortalityDistribution,
                                   distribution_female: MortalityDistribution,
                                   node_ids: List[int] = None) -> None:
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
                          simple_distribution_implicits: List[Callable] = None,
                          complex_distribution_implicits: List[Callable] = None,
                          node_ids: List[int] = None) -> None:
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
                                values: Union[List[str], List[float]] = None,
                                initial_distribution: List[float] = None,
                                node_ids: List[int] = None,
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
