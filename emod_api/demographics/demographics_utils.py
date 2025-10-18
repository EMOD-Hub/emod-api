import json

params = {
    "Demographics_Filenames": [],
    "Population_Scale_Type": "FIXED_SCALING",
    "x_Base_Population": 1,
    "Enable_Aging": 1,
    "Age_Initialization_Distribution_Type": "DISTRIBUTION_SIMPLE",
    "Enable_Demographics_Birth": 1,
    "Enable_Demographics_Initial": 1,
    "Enable_Demographics_Other": 0,
    "Enable_Demographics_Reporting": 0,
    "Enable_Demographics_Builtin": 0,
    "Enable_Demographics_Risk": 0,
    "Enable_Immunity_Initialization_Distribution": 0,  # compatibility with EMOD v2.0 and earlier
    "Susceptibility_Initialization_Distribution_Type": "DISTRIBUTION_OFF",
    "Enable_Initial_Prevalence": 1,
    "Enable_Vital_Dynamics": 1,
    "Death_Rate_Dependence": "NONDISEASE_MORTALITY_BY_AGE_AND_GENDER",
    "Enable_Birth": 1,
    "Birth_Rate_Dependence": "POPULATION_DEP_RATE",
    "Birth_Rate_Time_Dependence": "NONE",
    "x_Birth": 1,
    "Enable_Disease_Mortality": 0,
    "Base_Mortality": 0,
    "Mortality_Time_Course": "DAILY_MORTALITY",
    "x_Other_Mortality": 1,
    "Enable_Natural_Mortality": 1,
    "Individual_Sampling_Type": "TRACK_ALL",
    "Base_Individual_Sample_Rate": 1,  # all parameters below are unused without sampling
    "Max_Node_Population_Samples": 40,
    "Sample_Rate_0_18mo": 1,
    "Sample_Rate_10_14": 1,
    "Sample_Rate_15_19": 1,
    "Sample_Rate_18mo_4yr": 1,
    "Sample_Rate_20_Plus": 1,
    "Sample_Rate_5_9": 1,
    "Sample_Rate_Birth": 2,
}

distribution_types = {
    "CONSTANT_DISTRIBUTION": 0,
    "UNIFORM_DISTRIBUTION": 1,
    "GAUSSIAN_DISTRIBUTION": 2,
    "EXPONENTIAL_DISTRIBUTION": 3,
    "POISSON_DISTRIBUTION": 4,
    "LOG_NORMAL": 5,
    "BIMODAL_DISTRIBUTION": 6,
}


def set_risk_mod(filename, distribution, par1, par2):
    """
    Set the ``RiskDistributionFlag``, ``RiskDistribution1`` and ``RiskDistribution2`` in a demographics file.

    :param filename: The demographics file location
    :param distribution: The selected distribution (need to come from ``distribution_types``)
    :param par1: Parameter 1 of the distribution
    :param par2: Parameter 2 of the distribution (may be unused depending on the selected distribution)
    :return: Nothing
    """
    set_demog_distributions(filename, [("Risk", distribution, par1, par2)])


def set_immune_mod(filename, distribution, par1, par2):
    """
    Set the ``ImmunityDistributionFlag``, ``ImmunityDistribution1`` and ``ImmunityDistribution2`` in a demographics file.

    :param filename: The demographics file location
    :param distribution: The selected distribution (need to come from `distribution_types`)
    :param par1: Parameter 1 of the distribution
    :param par2: Parameter 2 of the distribution (may be unused depending on the selected distribution)
    :return: Nothing
    """
    set_demog_distributions(filename, [("Immunity", distribution, par1, par2)])


def apply_to_defaults_or_nodes(demog, fn, *args):
    """
    Apply the ``fn`` function either to the ``Defaults`` dictionary or to each of the nodes depending
    if the ``IndividualAttributes`` parameter is present in the ``Defaults`` or not.

    .. todo::
        This function should be refactored to look at both the ``Defaults`` and each individual nodes.
        It will make sure that if a node override the default ``IndividualAttributes`` the change will still
        be effective.

    :param demog: The demographic file represented as a dictionary
    :param fn: The function to apply the ``Defaults`` or individual nodes
    :param args: Argument list needed by ``fn``
    :return: Nothing
    """
    if "Defaults" in demog and "IndividualAttributes" in demog["Defaults"]:
        fn(demog["Defaults"], *args)
    else:
        for node in demog["Nodes"]:
            fn(node, *args)


def set_demog_distributions(filename, distributions):
    """
    Apply distributions to a given demographics file.
    The distributions needs to be formatted as a list of (name, distribution, par1, par2) with:

    * **name:** Immunity, Risk, Age, Prevalence or MigrationHeterogeneity
    * **distribution:** One distribution contained in ``distribution_types``
    * **par1, par2:** the values for the distribution parameters

    .. code-block:: python

        # Set the PrevalenceDistribution to a uniform distribution with 0.1 and 0.2
        # and the ImmunityDistributionFlag to a constant distribution with 1
        demog = json.load(open("demographics.json","r"))
        distributions = list()
        distributions.add(("Prevalence","UNIFORM_DISTRIBUTION",0.1,0.2))
        distributions.add(("Immunity","CONSTANT_DISTRIBUTION",1,0))
        set_demog_distribution(demog, distributions)

    :param filename: the demographics file as json
    :param distributions: the different distributions to set contained in a list
    :return: Nothing
    """
    with open(filename, "r") as demogjson_file:
        demog = json.loads(demogjson_file.read())

    def set_attributes(d, dist_type, par1, par2):
        d["IndividualAttributes"].update(
            {
                dist_type + "DistributionFlag": distribution_types[distribution],
                dist_type + "Distribution1": par1,
                dist_type + "Distribution2": par2,
            }
        )

    for (dist_type, distribution, par1, par2) in distributions:
        if distribution not in distribution_types.keys():
            raise Exception("Don't recognize distribution type %s" % distribution)

        apply_to_defaults_or_nodes(demog, set_attributes, dist_type, par1, par2)

    with open(filename, "w") as output_file:
        output_file.write(json.dumps(demog, sort_keys=True, indent=4))


# the following two methods need a refactor
# we can have a single demographics file object and adjust attribute depending on usage
def set_static_demographics(cb, use_existing=False):
    """
    Create a static demographics based on the demographics file specified in the config file
    of the :py:class:`DTKConfigBuilder` object passed to the function.

    This function takes the current demographics file and adjust the birth rate/death rate
    to get a static population (the deaths are always compensated by new births).

    .. todo::
        Make sure that the population is 1000 individuals. For now rely on the fact that the base
        demographics file will be 1000 Initial Population.

    :param cb: The config builder object
    :param use_existing: If ``True`` will only take the demographics file name and add the .static to it. If ``False`` will create a static demographics file based on the specified demographics file.
    :return: Nothing
    """
    demog_filenames = cb.get_param("Demographics_Filenames")
    if len(demog_filenames) != 1:
        raise Exception("Expecting only one demographics filename.")
    demog_filename = demog_filenames[0]
    static_demog_filename = demog_filename.replace("compiled.", "").replace(
        ".json", ".static.json", 1
    )
    cb.set_param("Demographics_Filenames", [static_demog_filename])
    cb.set_param("Birth_Rate_Dependence", "FIXED_BIRTH_RATE")

    if use_existing:
        return

    with open(demog_filename, "r") as demogjson_file:
        demog = json.loads(demogjson_file.read())

    birthrate = 0.12329
    exponential_age_param = 0.000118
    population_removal_rate = 45
    mod_mortality = {
        "NumDistributionAxes": 2,
        "AxisNames": ["gender", "age"],
        "AxisUnits": ["male=0,female=1", "years"],
        "AxisScaleFactors": [1, 365],
        "NumPopulationGroups": [2, 1],
        "PopulationGroups": [[0, 1], [0]],
        "ResultUnits": "annual deaths per 1000 individuals",
        "ResultScaleFactor": 2.74e-06,
        "ResultValues": [[population_removal_rate], [population_removal_rate]],
    }

    def set_attributes(d):
        if "IndividualAttributes" not in d:
            d["IndividualAttributes"] = {}

        d["IndividualAttributes"].update(
            {
                "MortalityDistribution": mod_mortality,
                "AgeDistributionFlag": distribution_types["EXPONENTIAL_DISTRIBUTION"],
                "AgeDistribution1": exponential_age_param,
            }
        )
        d["NodeAttributes"].update({"BirthRate": birthrate})

    apply_to_defaults_or_nodes(demog, set_attributes)

    output_file_path = demog_filename.replace(".json", ".static.json", 1)
    with open(output_file_path, "w") as output_file:
        output_file.write(json.dumps(demog, sort_keys=True, indent=4))


def set_growing_demographics(cb, use_existing=False):
    """
    This function creates a growing population. It works the same way as the :any:`set_static_demographics` but with
    a birth rate more important than the death rate which leads to a growing population.

    .. todo::
        Make sure that the population is 1000 individuals. For now rely on the fact that the base
        demographics file will be 1000 Initial Population.

    :param cb: The :py:class:`DTKConfigBuilder <dtk.utils.core.DTKConfigBuilder>` object
    :param use_existing: If ``True`` will only take the demographics file name and add the .growing to it. If ``False`` will create a growing demographics file based on the specified demographics file.
    :return: Nothing
    """

    demog_filenames = cb.get_param("Demographics_Filenames")
    if len(demog_filenames) != 1:
        raise Exception("Expecting only one demographics filename.")
    demog_filename = demog_filenames[0]
    growing_demog_filename = demog_filename.replace("compiled.", "").replace(
        ".json", ".growing.json", 1
    )
    cb.set_param("Demographics_Filenames", [growing_demog_filename])
    cb.set_param("Birth_Rate_Dependence", "POPULATION_DEP_RATE")

    if use_existing:
        return

    with open(demog_filename, "r") as demogjson_file:
        demog = json.loads(demogjson_file.read())

    birthrate = 0.0001
    mod_mortality = {
        "NumDistributionAxes": 2,
        "AxisNames": ["gender", "age"],
        "AxisUnits": ["male=0,female=1", "years"],
        "AxisScaleFactors": [1, 365],
        "NumPopulationGroups": [2, 5],
        "PopulationGroups": [[0, 1], [0, 2, 10, 100, 2000]],
        "ResultUnits": "annual deaths per 1000 individuals",
        "ResultScaleFactor": 2.74e-06,
        "ResultValues": [[60, 8, 2, 20, 400], [60, 8, 2, 20, 400]],
    }

    def set_attributes(d):
        d["IndividualAttributes"].update({"MortalityDistribution": mod_mortality})
        d["NodeAttributes"].update({"BirthRate": birthrate})

    apply_to_defaults_or_nodes(demog, set_attributes)

    output_file_path = demog_filename.replace(".json", ".growing.json", 1)
    with open(output_file_path, "w") as output_file:
        output_file.write(json.dumps(demog, sort_keys=True, indent=4))
