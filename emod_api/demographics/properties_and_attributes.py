from typing import Union, Optional, Callable, Tuple

from emod_api.demographics.age_distribution import AgeDistribution
from emod_api.demographics.demographic_exceptions import ConflictingDistributionsException
from emod_api.demographics.fertility_distribution import FertilityDistribution
from emod_api.demographics.implicit_functions import _set_age_simple, _set_age_complex, _set_suscept_simple, \
    _set_suscept_complex, _set_init_prev, _set_migration_model_fixed_rate, _set_enable_migration_model_heterogeneity, \
    _set_enable_natural_mortality, _set_mortality_age_gender_year, _set_mortality_age_gender, _set_enable_demog_risk, \
    _set_fertility_age_year
from emod_api.demographics.mortality_distribution import MortalityDistribution
from emod_api.demographics.susceptibility_distribution import SusceptibilityDistribution
from emod_api.demographics.updateable import Updateable


# TODO: most of the documentation in this file consists of stand-in stubs. Needs to be filled in.
#  https://github.com/InstituteforDiseaseModeling/emod-api/issues/695


class IndividualProperty(Updateable):
    def __init__(self,
                 property: str,
                 values: Union[list[float], list[str]],
                 initial_distribution: list[float] = None,
                 transitions: list[dict] = None,
                 transmission_matrix: list[list[float]] = None,
                 transmission_route: str = "Contact"):
        """
        Add Individual Properties, including an optional HINT configuration matrix.

        Individual properties act as 'labels' on model agents that can be used for identifying and targeting
        subpopulations in campaign elements and reports. E.g. model agents may be given a property ('Accessibility')
        that labels them as either having access to health care (value: 'Yes') or not (value: 'No').

        Property-based heterogeneous disease transmission (HINT) is available for generic, environmental, typhoid,
        airborne, or TBHIV simulations as other simulation types have parameters for modeling the heterogeneity of
        transmission. By default, transmission is assumed to occur homogeneously among the population within a node.

        Note: EMOD requires individual property key and values (property and values args) to be the same across all
            nodes. The individual distributions of individual properties (initial_distribution) can vary acros nodes.

        Note: For HINT, you will also need to set config parameter `Enable_Heterogeneous_Intranode_Transmission` to 1
        likely with config.parameters.Enable_Heterogeneous_Intranode_Transmission = 1

        Documentation of individual properties and HINT:
            For malaria, see :doc:`emod-malaria:emod/model-properties`
                    and for HIV, see :doc:`emod-hiv:emod/model-properties`.
            For malaria, see :doc:`emod-malaria:emod/model-hint`
                    and for HIV, see :doc:`emod-hiv:emod/model-hint`.

        Args:
            property: a new individual property key to add. If property already exists an exception is raised
                unless overwrite_existing is True.
            values: A list of valid values for the property, or, if creating age-based transmission, age edges for
                the 'Age_Bin' property. E.g. ['Yes', 'No'] for an 'Accessibility' property.
            initial_distribution: The fractional, between 0 and 1, initial distribution of each valid values entry.
                Order must match values argument. The values must add up to 1.
            transmission_matrix: HINT transmission matrix. For malaria, see :doc:`emod-malaria:emod/model-hint`
                and for HIV, see :doc:`emod-hiv:emod/model-hint`.
            transmission_route: The route of transmission. Default is 'Contact'. Available routes are 'Contact' and
                'Environmental'.
            transitions: A list of dictionaries that each define how an individual transitions
                from one property value to another.  For malaria, see :doc:`emod-malaria:emod/parameter-demographics`
                and for HIV, see :doc:`emod-hiv:emod/parameter-demographics`.
        """
        super().__init__()
        if property == "Age_Bin":
            if not isinstance(values, list) or not all(isinstance(i, float) or isinstance(i, int) for i in values):
                raise ValueError("For property 'Age_Bin' values must be a list of floats representing "
                                 "age bin edges in years.")
            if values[0] != 0 or values[-1] != -1:
                raise ValueError("For property 'Age_Bin', first value must be 0 and last value must be -1.")
            if not transmission_matrix:
                raise ValueError("For property 'Age_Bin', transmission_matrix and transmission_routes must be defined.")
            num_age_buckets = len(values) - 1
            if len(transmission_matrix) != num_age_buckets:
                raise ValueError("For property 'Age_Bin', transmission_matrix must match number of age buckets, which "
                                 " is number of edges in 'values' - 1.")
            for mtx_row in transmission_matrix:
                if len(mtx_row) != num_age_buckets:
                    raise ValueError("For property 'Age_Bin', each row of transmission_matrix must match number of age "
                                     "buckets, which is number of edges in 'values' - 1.")
        if initial_distribution:
            for i in initial_distribution:
                if i < 0 or i > 1:
                    raise ValueError("initial_distribution values must be between 0 and 1.")
            if sum(initial_distribution) != 1:
                raise ValueError("initial_distribution values must sum to 1.")
            if len(initial_distribution) != len(values):
                raise ValueError("initial_distribution must have the same number of entries as values.")

        if transmission_matrix and transmission_route not in ["Contact", "Environmental"]:
            raise ValueError(f"Invalid transmission route: {transmission_route}. "
                             f"Valid routes are 'Contact' and 'Environmental'.")
        if transmission_matrix and property != "Age_Bin":
            if len(transmission_matrix) != len(values):
                raise ValueError("For property other than 'Age_Bin', size of transmission_matrix must match number "
                                 "of values.")
            for mtx_row in transmission_matrix:
                if len(mtx_row) != len(values):
                    raise ValueError("For property other than 'Age_Bin', each row of transmission_matrix must match "
                                     "number of values.")
        for transition in transitions or []:
            if not isinstance(transition, dict):
                raise ValueError("Transitions must be a list of dictionaries. Please see the documentation for correct "
                                 "format: ")

        self.initial_distribution = initial_distribution
        self.property = property
        self.values = values
        self.transitions = transitions
        self.transmission_matrix = transmission_matrix
        self.transmission_route = transmission_route

    def to_dict(self) -> dict:
        individual_property = self.parameter_dict
        individual_property.update({"Property": self.property})
        if self.property == "Age_Bin":
            individual_property.update({"Age_Bin_Edges_In_Years": self.values})
        else:
            individual_property.update({"Values": self.values})

        if self.initial_distribution:
            individual_property.update({"Initial_Distribution": self.initial_distribution})

        if self.transitions is not None:
            individual_property.update({"Transitions": self.transitions})

        if self.transmission_matrix is not None:
            individual_property.update({"TransmissionMatrix": {"Route": self.transmission_route,
                                                               "Matrix": self.transmission_matrix}})
        return individual_property

    @classmethod
    def from_dict(cls, ip_dict: dict) -> '__class__':
        available_args = ['initial_distribution', 'property', 'values', 'transitions',
                          'transmission_matrix', 'transmission_route']
        args = {key: ip_dict[key] for key in available_args if key in ip_dict}
        return cls(**args)

    def __eq__(self, other) -> bool:
        return self.to_dict() == other.to_dict()


class IndividualProperties(Updateable):
    """
    A container class for holding IndividualProperty objects used by Node objects. It simply contains functionality for
    adding, removing, and retrieving contained IndividualProperty objects with some light consistency checking
    (preventing duplicate-named IndividualProperties).
    """

    class DuplicateIndividualPropertyException(Exception):
        pass

    class NoSuchIndividualPropertyException(Exception):
        pass

    def __init__(self, individual_properties: list[IndividualProperty] = None):
        """
        https://docs.idmod.org/projects/emod-generic/en/latest/model-properties.html

        Args:
            individual_properties (list[IndividualProperty]): list of individual properties to include. Default is
                no individual_properties.
        """
        super().__init__()
        self.individual_properties = [] if individual_properties is None else individual_properties

    def add(self, individual_property: IndividualProperty, overwrite=False) -> None:
        has_ip = self.has_individual_property(property_key=individual_property.property)
        if has_ip:
            if overwrite:
                # remove existing then add
                self.remove_individual_property(property_key=individual_property.property)
            else:
                msg = f"Property {individual_property.property} already present in IndividualProperties"
                raise self.DuplicateIndividualPropertyException(msg)
        self.individual_properties.append(individual_property)

    def add_parameter(self, key, value):
        raise NotImplementedError("A parameter cannot be added to IndividualProperties.")

    @property
    def ip_by_name(self):
        return {ip.property: ip for ip in self.individual_properties}

    def has_individual_property(self, property_key: str) -> bool:
        return property_key in self.ip_by_name.keys()

    def get_individual_property(self, property_key: str) -> IndividualProperty:
        ip = self.ip_by_name.get(property_key, None)
        if ip is None:
            msg = f"No IndividualProperty exists with the property key: {property_key}"
            raise self.NoSuchIndividualPropertyException(msg)
        return ip

    def remove_individual_property(self, property_key: str):
        ips_to_keep = [ip for ip in self.individual_properties if ip.property != property_key]
        self.individual_properties = ips_to_keep

    def to_dict(self) -> list[dict]:
        data = [ip.to_dict() for ip in self.individual_properties]
        return data

    def __getitem__(self, index: int):
        return self.individual_properties[index]

    def __len__(self):
        return len(self.individual_properties)


class IndividualAttributes(Updateable):
    # TODO: consider refactoring to use objects instead of a big list of potential parameters here:
    #  https://github.com/InstituteforDiseaseModeling/emod-api-old/issues/750
    def __init__(self,
                 age_distribution_flag: int = None,
                 age_distribution1: int = None,
                 age_distribution2: int = None,
                 age_distribution: AgeDistribution = None,
                 susceptibility_distribution_flag: int = None,
                 susceptibility_distribution1: int = None,
                 susceptibility_distribution2: int = None,
                 susceptibility_distribution: SusceptibilityDistribution = None,
                 prevalence_distribution_flag: int = None,
                 prevalence_distribution1: int = None,
                 prevalence_distribution2: int = None,
                 risk_distribution_flag: int = None,
                 risk_distribution1: int = None,
                 risk_distribution2: int = None,
                 migration_heterogeneity_distribution_flag: int = None,
                 migration_heterogeneity_distribution1: int = None,
                 migration_heterogeneity_distribution2: int = None,
                 fertility_distribution: FertilityDistribution = None,
                 mortality_distribution_male: MortalityDistribution = None,
                 mortality_distribution_female: MortalityDistribution = None,
                 innate_immune_distribution_flag: int = None,
                 innate_immune_distribution1: int = None,
                 innate_immune_distribution2: int = None
                 ):
        """
        Defines the initial distribution of attributes for model agents for all disease setups. These are used by Node
        objects and can be defined separately per-node. Some attributes utilize simple distributions, some utilize
        complex distributions, some can utilize either simple or complex. For those that can utilize simple or complex
        distributions, only one may be specified (it is a user choice). It is highly unlikely a user will utilize this
        class directly, as it exists primarily for ensuring proper serialization to JSON for EMOD input file
        representation. The standard, user-facing interface for updating the distributions used is in the Demographics
        class in emodpy.demographics .

        Supported simple distributions and the meaning of their parameters are defined in the
        emod_api.utils.distributions submodule.

        Further information can be found at:
        https://docs.idmod.org/projects/emod-generic/en/latest/parameter-demographics.html#individual-attributes

        Args:
            age_distribution_flag (int, optional): Toggles the type of simple distribution for representing age,
                determining the distribution-specific interpretation of age_distribution1 and age_distribution2.
                Mutually exclusive with a complex age distribution (age_distribution).
            age_distribution1 (int, optional): If age_distribution_flag is not None, the specified simple
                distribution-dependent first argument.
            age_distribution2 (int, optional): If age_distribution_flag is not None, the specified simple
                distribution-dependent second argument (if any).
            age_distribution (AgeDistribution, optional): If provided, defines a complex age distribution. Mutually
                exclusive with a simple age distribution (age_distribution_flag).

            susceptibility_distribution_flag (int, optional): Toggles the type of simple distribution for representing
                susceptibility, determining the distribution-specific interpretation of susceptibility_distribution1
                and susceptibility_distribution2. Mutually exclusive with a complex susceptibility distribution
                (susceptibility_distribution).
            susceptibility_distribution1 (int, optional): If susceptibility_distribution_flag is not None, the
                specified simple distribution-dependent first argument.
            susceptibility_distribution2 (int, optional): If susceptibility_distribution_flag is not None, the
                specified simple distribution-dependent second argument (if any).
            susceptibility_distribution (SusceptibilityDistribution, optional): If provided, defines a complex
                susceptibility distribution. Mutually exclusive with a simple susceptibility distribution
                (susceptibility_distribution_flag).

            prevalence_distribution_flag (int, optional): Toggles the type of simple distribution for representing
                prevalence, determining the distribution-specific interpretation of prevalence_distribution1 and
                prevalence_distribution2.
            prevalence_distribution1 (int, optional): If prevalence_distribution_flag is not None, the specified simple
                distribution-dependent first argument.
            prevalence_distribution2 (int, optional): If prevalence_distribution_flag is not None, the specified simple
                distribution-dependent second argument (if any).

            risk_distribution_flag (int, optional): Toggles the type of simple distribution for representing risk,
                determining the distribution-specific interpretation of risk_distribution1 and risk_distribution2.
            risk_distribution1 (int, optional): If risk_distribution_flag is not None, the specified simple
                distribution-dependent first argument.
            risk_distribution2 (int, optional): If risk_distribution_flag is not None, the specified simple
                distribution-dependent second argument (if any).

            migration_heterogeneity_distribution_flag (int, optional): Toggles the type of simple distribution for
                representing migration heterogeneity, determining the distribution-specific interpretation of
                migration_heterogeneity_distribution1 and migration_heterogeneity_distribution2.
            migration_heterogeneity_distribution1 (int, optional): If migration_heterogeneity_distribution_flag is not
                None, the specified simple distribution-dependent first argument.
            migration_heterogeneity_distribution2 (int, optional): If migration_heterogeneity_distribution_flag is not
                None, the specified simple distribution-dependent second argument (if any).

            fertility_distribution (FertilityDistribution, optional): If provided, defines a complex fertility
                distribution for females.

            mortality_distribution_male (MortalityDistribution, optional): If provided, defines a complex mortality
                distribution for males.
            mortality_distribution_female (MortalityDistribution, optional): If provided, defines a complex mortality
                distribution for females.

            innate_immune_distribution_flag (int, optional): Toggles the type of simple distribution for representing
                innate immunity, determining the distribution-specific interpretation of innate_immune_distribution1
                and innate_immune_distribution2.
            innate_immune_distribution1 (int, optional): If innate immune_distribution_flag is not None, the specified
                simple distribution-dependent first argument.
            innate_immune_distribution2 (int, optional): If innate immune_distribution_flag is not None, the specified
                simple distribution-dependent second argument (if any).
        """
        super().__init__()

        # users can either use a simple age distribution (toggled with age_distribution_flag, defined by
        # age_distribution1 and age_distribution2) OR a complex one (passed in via age_distribution)
        if (age_distribution is not None) and (age_distribution_flag is not None):
            raise ValueError("Cannot set both a simple age distribution via age_distribution_flag AND a complex "
                             "age distribution via age_distribution. Must choose one or the other. Or choose neither "
                             "to get default age distribution behavior.")
        self.age_distribution_flag = age_distribution_flag
        self.age_distribution1 = age_distribution1
        self.age_distribution2 = age_distribution2
        self.age_distribution = age_distribution

        # users can either use a simple susceptibility distribution (toggled with susceptibility_distribution_flag,
        # defined by susceptibility_distribution1 and susceptibility_distribution2) OR a complex one (passed in via
        # susceptibility_distribution)
        if (susceptibility_distribution is not None) and (susceptibility_distribution_flag is not None):
            raise ValueError("Cannot set both a simple susceptibility distribution via "
                             "susceptibility_distribution_flag AND a complex susceptibility distribution via "
                             "susceptibility_distribution. Must choose one or the other. Or choose neither to get "
                             "default susceptibility distribution behavior.")
        self.susceptibility_distribution_flag = susceptibility_distribution_flag
        self.susceptibility_distribution1 = susceptibility_distribution1
        self.susceptibility_distribution2 = susceptibility_distribution2
        self.susceptibility_distribution = susceptibility_distribution

        self.prevalence_distribution_flag = prevalence_distribution_flag
        self.prevalence_distribution1 = prevalence_distribution1
        self.prevalence_distribution2 = prevalence_distribution2

        self.migration_heterogeneity_distribution_flag = migration_heterogeneity_distribution_flag
        self.migration_heterogeneity_distribution1 = migration_heterogeneity_distribution1
        self.migration_heterogeneity_distribution2 = migration_heterogeneity_distribution2

        self.mortality_distribution_male = mortality_distribution_male
        self.mortality_distribution_female = mortality_distribution_female
        self.mortality_distribution = None # This should ONLY be set via from_dict() loading (deprecated).
        # fertility is only used by HIV

        self.fertility_distribution = fertility_distribution

        # risk and innate_immune are only used by malaria

        self.risk_distribution_flag = risk_distribution_flag
        self.risk_distribution1 = risk_distribution1
        self.risk_distribution2 = risk_distribution2

        self.innate_immune_distribution_flag = innate_immune_distribution_flag
        self.innate_immune_distribution1 = innate_immune_distribution1
        self.innate_immune_distribution2 = innate_immune_distribution2

    # New names for by-gender mortality distributions to support emodpy Demographics setting of all distributions
    # using the same code (see properties here).

    @property
    def mortality_male_distribution(self):
        return self.mortality_distribution_male

    @mortality_male_distribution.setter
    def mortality_male_distribution(self, value):
        self.mortality_distribution_male = value

    @property
    def mortality_female_distribution(self):
        return self.mortality_distribution_female

    @mortality_female_distribution.setter
    def mortality_female_distribution(self, value):
        self.mortality_distribution_female = value

    @staticmethod
    def _ensure_valid_value2_value(distribution_dict: dict, value2_key: str):
        # change any None to 0 for value2. Demographics demands it or EMOD fails.
        distribution_dict[value2_key] = 0 if distribution_dict[value2_key] is None else distribution_dict[value2_key]

    def to_dict(self) -> dict:
        # TODO: Consider updating how/where we check for consistency of attributes of IndividualProperties objects,
        #  as a user MAY alter validity after constructor call which currently enforces consistency:
        #  https://github.com/InstituteforDiseaseModeling/emod-api-old/issues/751
        individual_attributes = self.parameter_dict

        # Set age distribution as complex or simple if specified, but not both.
        both_types_selected = ((self.age_distribution is not None) and (self.age_distribution_flag is not None))
        if both_types_selected:
            raise ConflictingDistributionsException('Both a simple and complex distribution for age has been set. '
                                                    'Only type is allowed.')
        if self.age_distribution is not None:
            # complex distribution
            age_distribution_dict = {"AgeDistribution": self.age_distribution.to_dict()}
            individual_attributes.update(age_distribution_dict)
        elif self.age_distribution_flag is not None:
            # simple distribution
            age_distribution_dict = {
                "AgeDistributionFlag": self.age_distribution_flag,
                "AgeDistribution1": self.age_distribution1,
                "AgeDistribution2": self.age_distribution2
            }
            self._ensure_valid_value2_value(distribution_dict=age_distribution_dict, value2_key="AgeDistribution2")
            individual_attributes.update(age_distribution_dict)

        # Set susceptibility distribution as complex or simple if specified, but not both.
        both_types_selected = ((self.susceptibility_distribution is not None) and (self.susceptibility_distribution_flag is not None))
        if both_types_selected:
            raise ConflictingDistributionsException('Both a simple and complex distribution for susceptibility has '
                                                    'been set. Only type is allowed.')
        if self.susceptibility_distribution is not None:
            # complex distribution
            susceptibility_distribution_dict = {"SusceptibilityDistribution": self.susceptibility_distribution.to_dict()}
            individual_attributes.update(susceptibility_distribution_dict)
        elif self.susceptibility_distribution_flag is not None:
            # simple distribution
            susceptibility_distribution_dict = {
                "SusceptibilityDistributionFlag": self.susceptibility_distribution_flag,
                "SusceptibilityDistribution1": self.susceptibility_distribution1,
                "SusceptibilityDistribution2": self.susceptibility_distribution2
            }
            self._ensure_valid_value2_value(distribution_dict=susceptibility_distribution_dict,
                                            value2_key="SusceptibilityDistribution2")
            individual_attributes.update(susceptibility_distribution_dict)

        # The following distributions can only be simple, not complex

        if self.prevalence_distribution_flag is not None:
            prevalence_distribution_dict = {
                "PrevalenceDistributionFlag": self.prevalence_distribution_flag,
                "PrevalenceDistribution1": self.prevalence_distribution1,
                "PrevalenceDistribution2": self.prevalence_distribution2
            }
            self._ensure_valid_value2_value(distribution_dict=prevalence_distribution_dict,
                                            value2_key="PrevalenceDistribution2")
            individual_attributes.update(prevalence_distribution_dict)

        if self.migration_heterogeneity_distribution_flag is not None:
            migration_heterogeneity_distribution_dict = {
                "MigrationHeterogeneityDistributionFlag": self.migration_heterogeneity_distribution_flag,
                "MigrationHeterogeneityDistribution1": self.migration_heterogeneity_distribution1,
                "MigrationHeterogeneityDistribution2": self.migration_heterogeneity_distribution2
            }
            self._ensure_valid_value2_value(distribution_dict=migration_heterogeneity_distribution_dict,
                                            value2_key="MigrationHeterogeneityDistribution2")
            individual_attributes.update(migration_heterogeneity_distribution_dict)

        # malaria only - possible to move this to emodpy-malaria in the future if desired.
        if self.risk_distribution_flag is not None:
            risk_distribution_dict = {
                "RiskDistributionFlag": self.risk_distribution_flag,
                "RiskDistribution1": self.risk_distribution1,
                "RiskDistribution2": self.risk_distribution2
            }
            self._ensure_valid_value2_value(distribution_dict=risk_distribution_dict, value2_key="RiskDistribution2")
            individual_attributes.update(risk_distribution_dict)

        # malaria only - possible to move this to emodpy-malaria in the future if desired.
        if self.innate_immune_distribution_flag is not None:
            innate_immune_distribution_dict = {
                "InnateImmuneDistributionFlag": self.innate_immune_distribution_flag,
                "InnateImmuneDistribution1": self.innate_immune_distribution1,
                "InnateImmuneDistribution2": self.innate_immune_distribution2
            }
            self._ensure_valid_value2_value(distribution_dict=innate_immune_distribution_dict,
                                            value2_key="InnateImmuneDistribution2")
            individual_attributes.update(innate_immune_distribution_dict)

        # The following distributions can only be complex, not simple

        if self.fertility_distribution is not None:
            individual_attributes.update({"FertilityDistribution": self.fertility_distribution.to_dict()})

        if self.mortality_distribution_male is not None:
            individual_attributes.update({"MortalityDistributionMale": self.mortality_distribution_male.to_dict()})

        if self.mortality_distribution_female is not None:
            individual_attributes.update({"MortalityDistributionFemale": self.mortality_distribution_female.to_dict()})

        # # This should ONLY be set via from_dict() loading (deprecated).
        if self.mortality_distribution is not None:
            individual_attributes.update({"MortalityDistribution": self.mortality_distribution.to_dict()})

        return individual_attributes

    def from_dict(self, individual_attributes: dict) -> Tuple["IndividualAttributes", list[Callable]]:
        implicit_functions = []

        age_distribution_dict = individual_attributes.get("AgeDistribution", None)
        if age_distribution_dict is None:
            self.age_distribution = None
            self.age_distribution_flag = individual_attributes.get("AgeDistributionFlag", None)
            self.age_distribution1 = individual_attributes.get("AgeDistribution1", None)
            self.age_distribution2 = individual_attributes.get("AgeDistribution2", None)
            implicit_functions.append(_set_age_simple)
        else:
            self.age_distribution = AgeDistribution.from_dict(distribution_dict=age_distribution_dict)
            self.age_distribution_flag = None
            self.age_distribution1 = None
            self.age_distribution2 = None
            implicit_functions.append(_set_age_complex)

        susceptibility_distribution_dict = individual_attributes.get("SusceptibilityDistribution", None)
        if susceptibility_distribution_dict is None:
            self.susceptibility_distribution = None
            self.susceptibility_distribution_flag = individual_attributes.get("SusceptibilityDistributionFlag", None)
            self.susceptibility_distribution1 = individual_attributes.get("SusceptibilityDistribution1", None)
            self.susceptibility_distribution2 = individual_attributes.get("SusceptibilityDistribution2", None)
            implicit_functions.append(_set_suscept_simple)
        else:
            self.susceptibility_distribution = SusceptibilityDistribution.from_dict(
                distribution_dict=susceptibility_distribution_dict)
            self.susceptibility_distribution_flag = None
            self.susceptibility_distribution1 = None
            self.susceptibility_distribution2 = None
            implicit_functions.append(_set_suscept_complex)

        self.prevalence_distribution_flag = individual_attributes.get("PrevalenceDistributionFlag", None)
        self.prevalence_distribution1 = individual_attributes.get("PrevalenceDistribution1", None)
        self.prevalence_distribution2 = individual_attributes.get("PrevalenceDistribution2", None)
        if self.prevalence_distribution_flag is not None:
            implicit_functions.append(_set_init_prev)

        self.migration_heterogeneity_distribution_flag = individual_attributes.get(
            "MigrationHeterogeneityDistributionFlag", None)
        self.migration_heterogeneity_distribution1 = individual_attributes.get("MigrationHeterogeneityDistribution1",
                                                                               None)
        self.migration_heterogeneity_distribution2 = individual_attributes.get("MigrationHeterogeneityDistribution2",
                                                                               None)
        if self.migration_heterogeneity_distribution_flag is not None:
            implicit_functions.extend([_set_migration_model_fixed_rate, _set_enable_migration_model_heterogeneity])

        loaded_mortality = False
        distribution_dict = individual_attributes.get("MortalityDistributionMale", None)
        if distribution_dict is None:
            self.mortality_distribution_male = None
        else:
            self.mortality_distribution_male = MortalityDistribution.from_dict(distribution_dict=distribution_dict)
            loaded_mortality = True

        distribution_dict = individual_attributes.get("MortalityDistributionFemale", None)
        if distribution_dict is None:
            self.mortality_distribution_female = None
        else:
            self.mortality_distribution_female = MortalityDistribution.from_dict(distribution_dict=distribution_dict)
            loaded_mortality = True

        if loaded_mortality:
            implicit_functions.extend([_set_enable_natural_mortality, _set_mortality_age_gender_year])

        # Even though we do NOT support NEW CREATION of all-gender mortality distributions, they are still valid in
        # deprecated "from_dict()"(files)-type demographics loading. This is the only way self.mortality_distribution
        # can/should be set in this class.
        distribution_dict = individual_attributes.get("MortalityDistribution", None)
        if distribution_dict is None:
            self.mortality_distribution = None
        else:
            self.mortality_distribution = MortalityDistribution.from_dict(distribution_dict=distribution_dict)
            implicit_functions.extend([_set_enable_natural_mortality, _set_mortality_age_gender])

        # malaria only - possible to move this to emodpy-malaria in the future if desired.
        self.innate_immune_distribution_flag = individual_attributes.get("InnateImmuneDistributionFlag", None)
        self.innate_immune_distribution1 = individual_attributes.get("InnateImmuneDistribution1", None)
        self.innate_immune_distribution2 = individual_attributes.get("InnateImmuneDistribution2", None)
        if self.innate_immune_distribution_flag is not None:
            import warnings
            warnings.warn("InnateImmuneDistribution loaded by file. Pyrogenic vs. cytokine-killing vs NONE (ignore) is "
                          "unknown. Config may need updating to ensure parameter Innate_Immune_Variation_Type is set "
                          "properly.",
                          Warning, stacklevel=2)

        # malaria only - possible to move this to emodpy-malaria in the future if desired.
        self.risk_distribution_flag = individual_attributes.get("RiskDistributionFlag", None)
        self.risk_distribution1 = individual_attributes.get("RiskDistribution1", None)
        self.risk_distribution2 = individual_attributes.get("RiskDistribution2", None)
        if self.risk_distribution_flag is not None:
            implicit_functions.append(_set_enable_demog_risk)

        distribution_dict = individual_attributes.get("FertilityDistribution", None)
        if distribution_dict is None:
            self.fertility_distribution = None
        else:
            self.fertility_distribution = FertilityDistribution.from_dict(distribution_dict)
            implicit_functions.append(_set_fertility_age_year)

        return self, implicit_functions


class NodeAttributes(Updateable):
    def __init__(self,
                 airport: int = None,
                 altitude: float = None,
                 area: float = None,
                 birth_rate: float = None,
                 country: str = None,
                 growth_rate: float = None,
                 name: str = None,
                 latitude: float = None,
                 longitude: float = None,
                 metadata: dict = None,
                 initial_population: int = None,
                 region: int = None,
                 seaport: int = None,
                 larval_habitat_multiplier: Optional[list[float]] = None,
                 initial_vectors_per_species: Union[dict, int, None] = None,
                 infectivity_multiplier: float = None,
                 extra_attributes: dict = None):
        """
        Defines node-specific attributes for all disease setups, utilized by Node objects.

        Further information can be found at:
        https://docs.idmod.org/projects/emod-generic/en/latest/parameter-demographics.html#nodeattributes
        https://docs.idmod.org/projects/emod-malaria/en/latest/parameter-demographics.html#nodeattributes

        Args:
            airport (int, optional): Whether the node has an airport (1 for true, 0 for false).
            altitude (float, optional): Altitude of the node (in meters).
            area (float, optional): Spatial size of the node (TODO: unknown units)
            birth_rate (float, optional): The birth rate in births/day/woman .
            country (str, optional): Name of the country the node is in.
            growth_rate (float, optional): TODO: unknown
            name (str, optional): Name of the node
            latitude (float, optional): Latitude of the node in degrees.
            longitude (float, optional): Longitude of the node in degrees.
            metadata (dict, optional): An arbitrary dict of metaaata key/values to add to the node for notation.
            initial_population (int, optional): The initial number of people/agents in the node.
            region (int, optional): Whether the node has a road network (1 for true, 0 for false).
            seaport (int, optional):  Whether the node has a seaport (1 for true, 0 for false).
            larval_habitat_multiplier (list(float), optional): The value(s) by which to scale the larval habitat
                availability specified in the configuration file with Larval_Habitat_Types.
            initial_vectors_per_species ((dict or int), optional): The initial number of vectors per species in the
                node.
            infectivity_multiplier (float, optional): TODO: unknown
            extra_attributes (dict, optional): An arbitrary dict of attribute key/values to add to the node.
        """
        super().__init__()
        self.airport = airport
        self.altitude = altitude
        self.area = area
        self.birth_rate = birth_rate
        self.country = country
        self.growth_rate = growth_rate
        self.initial_population = initial_population
        self.initial_vectors_per_species = initial_vectors_per_species
        self.larval_habitat_multiplier = larval_habitat_multiplier
        self.latitude = latitude
        self.longitude = longitude
        self.metadata = metadata
        self.name = name
        self.region = region
        self.seaport = seaport
        self.infectivity_multiplier = infectivity_multiplier
        self.extra_attributes = extra_attributes

    def from_dict(self, node_attributes: dict):
        self.airport = node_attributes.get("Airport")
        self.altitude = node_attributes.get("Altitude")
        self.area = node_attributes.get("Area")
        self.country = node_attributes.get("country")
        self.growth_rate = node_attributes.get("GrowthRate")
        self.name = node_attributes.get("FacilityName")
        self.latitude = node_attributes.get("Latitude")
        self.longitude = node_attributes.get("Longitude")
        self.metadata = node_attributes.get("Metadata")
        self.initial_population = node_attributes.get("InitialPopulation")
        self.larval_habitat_multiplier = node_attributes.get("LarvalHabitatMultiplier")
        self.initial_vectors_per_species = node_attributes.get("InitialVectorsPerSpecies")
        self.birth_rate = node_attributes.get("BirthRate")
        self.seaport = node_attributes.get("Seaport")
        self.region = node_attributes.get("Region")
        self.infectivity_multiplier = node_attributes.get("InfectivityMultiplier")
        return self

    def to_dict(self) -> dict:
        node_attributes = self.parameter_dict
        if self.birth_rate is not None:
            node_attributes.update({"BirthRate": self.birth_rate})

        if self.area is not None:
            node_attributes.update({"Area": self.area})

        if self.latitude is not None:
            node_attributes.update({"Latitude": self.latitude})

        if self.longitude is not None:
            node_attributes.update({"Longitude": self.longitude})

        if self.initial_population is not None:
            node_attributes.update({"InitialPopulation": int(self.initial_population)})

        if self.name:
            node_attributes.update({"FacilityName": self.name})

        if self.larval_habitat_multiplier is not None:
            node_attributes.update({"LarvalHabitatMultiplier": self.larval_habitat_multiplier})

        if self.initial_vectors_per_species:
            node_attributes.update({"InitialVectorsPerSpecies": self.initial_vectors_per_species})

        if self.airport is not None:
            node_attributes.update({"Airport": self.airport})

        if self.altitude is not None:
            node_attributes.update({"Altitude": self.altitude})

        if self.seaport is not None:
            node_attributes.update({"Seaport": self.seaport})

        if self.region is not None:
            node_attributes.update({"Region": self.region})

        if self.country is not None:
            node_attributes.update({"country": self.country})

        if self.growth_rate is not None:
            node_attributes.update({"GrowthRate": self.growth_rate})

        if self.metadata is not None:
            node_attributes.update({"Metadata": self.metadata})

        if self.infectivity_multiplier is not None:
            node_attributes.update({"InfectivityMultiplier": self.infectivity_multiplier})

        if self.extra_attributes is not None:
            node_attributes.update(self.extra_attributes)

        return node_attributes
