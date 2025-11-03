import copy
import numpy as np
import math
import scipy.sparse as sp
import scipy.sparse.linalg as la

from emod_api.demographics.fertility_distribution_old import FertilityDistributionOld as FertilityDistribution
from emod_api.demographics.mortality_distribution_old import MortalityDistributionOld as MortalityDistribution


import warnings
warnings.warn('DemographicsTemplates is deprecated. Please use appropriate methods directly with emodpy and emod-api '
              'Demographics objects.', DeprecationWarning, stacklevel=2)


class DemographicsTemplatesConstants:
    """Mortality_Rates_Mod30_5yrs_Xval: Mod 30 values closest to the 5 yr age boundaries based on when EMOD actually updates individual mortality rates.
                                        The distribution is constant for about 5 years (e.g. values at 0.6 days and 1829.5 days) and linearly interpolated between the 5 yr boundaries. """
    Mortality_Rates_Mod30_5yrs_Xval = [0.6, 1829.5, 1829.6, 3659.5, 3659.6, 5489.5,
                                       5489.6, 7289.5, 7289.6, 9119.5, 9119.6, 10949.5,
                                       10949.6, 12779.5, 12779.6, 14609.5, 14609.6, 16439.5,
                                       16439.6, 18239.5, 18239.6, 20069.5, 20069.6, 21899.5,
                                       21899.6, 23729.5, 23729.6, 25559.5, 25559.6, 27389.5,
                                       27389.6, 29189.5, 29189.6, 31019.5, 31019.6, 32849.5,
                                       32849.6, 34679.5, 34679.6, 36509.5, 36509.6, 38339.5]


# Migration
def _set_migration_model_fixed_rate(config):
    config.parameters.Migration_Model = "FIXED_RATE_MIGRATION"
    return config


def _set_enable_migration_model_heterogeneity(config):
    config.parameters.Enable_Migration_Heterogeneity = 1
    return config


def _set_migration_pattern_srt(config):
    config.parameters.Migration_Pattern = "SINGLE_ROUND_TRIPS"
    return config


def _set_migration_pattern_rwd(config):
    config.parameters.Migration_Pattern = "RANDOM_WALK_DIFFUSION"
    return config


def _set_regional_migration_filenames(config, file_name):
    config.parameters.Regional_Migration_Filename = file_name
    return config


def _set_local_migration_filename(config, file_name):
    config.parameters.Local_Migration_Filename = file_name
    return config


def _set_demographic_filenames(config, file_names):
    config.parameters.Demographics_Filenames = file_names
    return config


def _set_local_migration_roundtrip_probability(config, probability_of_return):
    config.parameters.Local_Migration_Roundtrip_Probability = probability_of_return
    return config


def _set_regional_migration_roundtrip_probability(config, probability_of_return):
    config.parameters.Regional_Migration_Roundtrip_Probability = probability_of_return
    return config


# Susceptibility
def _set_suscept_complex(config):
    config.parameters.Susceptibility_Initialization_Distribution_Type = "DISTRIBUTION_COMPLEX"
    return config


def _set_suscept_simple(config):
    config.parameters.Susceptibility_Initialization_Distribution_Type = "DISTRIBUTION_SIMPLE"
    return config


# Age Structure
def _set_age_simple(config):
    config.parameters.Age_Initialization_Distribution_Type = "DISTRIBUTION_SIMPLE"
    return config


def _set_age_complex(config):
    config.parameters.Age_Initialization_Distribution_Type = "DISTRIBUTION_COMPLEX"
    return config


# Initial Prevalence
def _set_init_prev(config):
    config.parameters.Enable_Initial_Prevalence = 1
    return config


# Mortality
def _set_enable_natural_mortality(config):
    config.parameters.Enable_Natural_Mortality = 1
    return config


def _set_mortality_age_gender(config):
    config.parameters.Death_Rate_Dependence = "NONDISEASE_MORTALITY_BY_AGE_AND_GENDER"
    return config


def _set_mortality_age_gender_year(config):
    config.parameters.Death_Rate_Dependence = "NONDISEASE_MORTALITY_BY_YEAR_AND_AGE_FOR_EACH_GENDER"
    return config


# Fertility
def _set_fertility_age_year(config):
    config.parameters.Birth_Rate_Dependence = "INDIVIDUAL_PREGNANCIES_BY_AGE_AND_YEAR"
    return config


def _set_population_dependent_birth_rate(config):
    config.parameters.Birth_Rate_Dependence = "POPULATION_DEP_RATE"
    return config


# Risk
def _set_enable_demog_risk(config):
    config.parameters.Enable_Demographics_Risk = 1
    return config


# Innate immunity (malaria support)
# TODO: Move to emodpy-malaria?
#  https://github.com/InstituteforDiseaseModeling/emodpy-malaria-old/issues/707
def _set_immune_variation_type_cytokine_killing(config):
    config.parameters.Innate_Immune_Variation_Type = 'CYTOKINE_KILLING'
    return config


# TODO: Move to emodpy-malaria?
#  https://github.com/InstituteforDiseaseModeling/emodpy-malaria-old/issues/707
def _set_immune_variation_type_pyrogenic_threshold(config):
    config.parameters.Innate_Immune_Variation_Type = 'PYROGENIC_THRESHOLD'
    return config


#
# Risk
#


"""
This submodule contains a bunch of json blobs that are valid pieces of a demographics json file
They serve as presets or templates to help build up a demographics.json without having to know
the json. This doesn't represent a full solution from dev team pov but the encapsulation and
abstraction of this API does at least provide a good step in the right direction.
"""


def NoRisk():
    """
    NoRisk puts everyone at 0 risk.
    """
    return {"RiskDist_Description": "No risk",
            "RiskDistributionFlag": 0, # 0 = CONSTANT
            "RiskDistribution1": 0,
            "RiskDistribution2": 0}


def FullRisk(demog, description=""):
    """
    FullRisk puts everyone at 100% risk.
    """
    if not description:
        description = "Setting full risk using default values"

    setting = {"RiskDist_Description": "Full risk",
               "RiskDistributionFlag": 0, # 0 = CONSTANT
               "RiskDistribution1": 1,
               "RiskDistribution2": 0,
               "RiskDistribution_Description": description}
    demog.SetDefaultFromTemplate(setting, _set_enable_demog_risk)


def InitRiskUniform(demog,
                    min_lim: float = 0,
                    max_lim: float = 1,
                    description: str = ""):
    """
    InitRiskUniform puts everyone at somewhere between 0% risk and 100% risk, drawn uniformly.

    Args:
        min_lim: Low end of uniform distribution. Must be >=0, <1.
        max_lim: High end of uniform distribution. Must be >=min, <=1.
        description: Why were these values chosen?

    Returns:

    Raises:

    """
    if not description:
        description = f"Risk is drawn from a uniform distribution, min_lim={min_lim} and max_lim={max_lim}"

    if min_lim < 0:
        raise ValueError(f"min_lim value of {min_lim} is less than 0. Not valid.")
    setting = {"RiskDist_Description": "Uniformly distributed risk",
               "RiskDistributionFlag": 1,
               "RiskDistribution1": min_lim,
               "RiskDistribution2": max_lim,
               "RiskDistribution_Description": description}
    demog.SetDefaultFromTemplate(setting, _set_enable_demog_risk)


def InitRiskLogNormal(demog, mean=0.0, sigma=1.0):
    """
    InitRiskLogNormal puts everyone at somewhere between 0% risk and 100% risk, drawn from LogNormal.

    Args:
        mean (float): Mean of lognormal distribution.
        sigma (float): Sigma of lognormal distribution.

    Returns:

    Raises:

    """
    setting = {"RiskDist_Description": "LogNormal distributed risk",
               "RiskDistributionFlag": 5, # lognormal
               "RiskDistribution1": mean,
               "RiskDistribution2": sigma}
    demog.SetDefaultFromTemplate(setting, _set_enable_demog_risk)


def InitRiskExponential(demog,
                        mean: float = 1.0):
    """
    InitRiskExponential puts everyone at somewhere between 0% risk and 100% risk, drawn from Exponential.

    Args:
        mean: Mean of exponential distribution.

    Returns:

    Raises:

    """
    setting = {"RiskDist_Description": "Exponentially distributed risk",
               "RiskDistributionFlag": 3, # exponential
               "RiskDistribution1": mean,
               "RiskDistribution2": 0}
    demog.SetDefaultFromTemplate(setting, _set_enable_demog_risk)


#
# Initial Prevalence
# config: Enable_Initial_Prevalence=1
#
def NoInitialPrevalence(demog):
    """
    NoInitialPrevalence disables initial prevalence; outbreak seeding must be done from an Outbreak intervention (or serialized population).

    Args:
        demog (Demographics): Demographics object

    Returns:

    Raises:

    """

    setting = {"PrevalenceDist_Description": "No initial prevalence",
               "InitialPrevalence": 0}
    # why not just disable it at config?
    demog.SetDefaultFromTemplate(setting)


def InitPrevUniform(demog, low_prev, high_prev, description=""):
    # old
    if not description:
        description = f"Drawing prevalence from uniform distribution, low_prev={low_prev} and high_prev={high_prev}"

    setting = {"PrevalenceDist_Description": f"Uniform draw from {low_prev} to {high_prev}",
               "PrevalenceDistributionFlag": 1,
               "PrevalenceDistribution1": low_prev,
               "PrevalenceDistribution2": high_prev,
               "PrevalenceDistribution_Description": description}
    # new
    # setting.update( { "InitialPrevalence": prevalence } )
    demog.SetDefaultFromTemplate(setting, _set_init_prev)

#
# Initial Susceptibility (1-Immunity)
#


def InitSusceptConstant(demog):
    # set config.Susceptibility_... SIMPLE
    setting = {"SusceptibilityDistributionFlag": 0,
               "SusceptibilityDistribution1": 1,
               "SusceptibilityDistribution2": 0}
    demog.SetDefaultFromTemplate(setting, _set_suscept_simple)


def EveryoneInitiallySusceptible(demog, setting=1.0):
    # set config.Susceptibility_Initialization_Distribution_Type=COMPLEX
    suscDist = {"SusceptibilityDist_Description": f"Everyone is initially susceptible with probability {setting}",
                "SusceptibilityDistribution": {"DistributionValues": [0, 36500],
                                               "ResultScaleFactor": 1,
                                               "ResultValues": [setting, setting]}}
    demog.SetDefaultFromTemplate(suscDist, _set_suscept_complex)


def StepFunctionSusceptibility(demog, protected_setting=0.0, threshold_age=365 * 5.0):
    # set config.Susceptibility_Initialization_Distribution_Type=COMPLEX
    suscDist = {"SusceptibilityDist_Description": "Youngers are somewhat protected",

                "SusceptibilityDistribution": {"DistributionValues": [0, threshold_age, threshold_age, 36500],
                                               "ResultScaleFactor": 1,
                                               "ResultValues": [protected_setting, protected_setting, 1.0, 1.0]}}
    demog.SetDefaultFromTemplate(suscDist, _set_suscept_complex)


def SimpleSusceptibilityDistribution(demog,
                                     meanAgeAtInfection: float = 2.5):
    """
    Rough initialization to reduce burn-in and prevent huge outbreaks at sim start
    For ages 0 through 99 the susceptibility distribution is set to an exponential distribution with an average age at infection.
    The minimum susceptibility is 2.5% at old ages.

    Args:
        demog (Demographics): Demographics object
        meanAgeAtInfection: Rough average age at infection in years.

    Note:
    Requires that ``config.parameters.Susceptibility_Initialization_Distribution_Type=DISTRIBUTION_COMPLEX``

    """
    # set config.Susceptibility_Initialization_Distribution_Type=COMPLEX
    # This function is first to be switched over to be reversed.
    # Calling code in emodpy will call this and pass the demographics instance then we
    # call SetDefaultFromTemplate on the demog object so we can also pass the setter function
    res_vals = [1.0, 1.0] + [0.025 + 0.975 * math.exp(-(i - 1) / (meanAgeAtInfection / math.log(2))) for i in range(2, 100, 1)]
    desc = "Rough initialization to reduce burn-in and prevent huge outbreaks at sim start. "
    desc += f"Exponential distribution, Average age at infection ~{meanAgeAtInfection} years, minimum susceptibility is 2.5% at old ages"
    suscDist = {"SusceptibilityDist_Description": desc,
                "SusceptibilityDistribution": {"DistributionValues": [i * 365 for i in range(100)],
                                               "ResultScaleFactor": 1,
                                               "ResultValues": res_vals}}
    demog.SetDefaultFromTemplate(suscDist, _set_suscept_complex)


def DefaultSusceptibilityDistribution(demog):
    # set config.Susceptibility_Initialization_Distribution_Type=COMPLEX
    res_vals = [1.0, 1.0] + [0.025 + 0.975 * math.exp(-(i - 1) / (2.5 / math.log(2))) for i in range(2, 100, 1)]
    desc = "Rough initialization to reduce burn-in and prevent huge outbreaks at sim start. "
    desc += "Exponential distribution, Average age at infection ~3.5 years, minimum susceptibility is 2.5% at old ages"
    suscDist = {"SusceptibilityDist_Description": desc,
                "SusceptibilityDistribution": {"DistributionValues": [i * 365 for i in range(100)],
                                               "ResultScaleFactor": 1,
                                               "ResultValues": res_vals}}
    demog.SetDefaultFromTemplate(suscDist, _set_suscept_complex)


#
# Mortality
#
def MortalityRateByAge(demog,
                       age_bins: list[float],
                       mort_rates: list[float]):
    """
        Set (non-disease) mortality rates by age bins. No checks are done on input arrays.

        Args:
            age_bins: list of age bins, with ages in years.
            mort_rates: list of mortality rates, where mortality rate is daily probability of dying..

        Returns:

    """
    # Note that the first input axis is sex (or gender). There are two values, but the rates are applied
    # equally for both here. The second input axis is age bin, and that is much more configurable.
    mort_dist = {"MortalityDistribution": {"AxisNames": ["gender", "age"],
                                           "AxisUnits": ["male=0,female=1", "years"],
                                           "AxisScaleFactors": [1, 365],
                                           "PopulationGroups": [[0, 1], age_bins],
                                           "ResultScaleFactor": 1,
                                           "ResultUnits": "daily probability of dying",
                                           "ResultValues": [mort_rates, mort_rates]}}
    demog.SetDefaultFromTemplate(mort_dist, _set_mortality_age_gender)


def _ConstantMortality(mortality_rate: float):
    if type(mortality_rate) is float:
        temp = -1 * (math.log(1 - mortality_rate))
        new_mortality_rate = [[temp], [temp]]
    else:  # assume list
        new_mortality_rate = copy.deepcopy(mortality_rate)
        for v in range(len(mortality_rate)):
            for i in range(len(mortality_rate[v])):
                new_mortality_rate[v][i] = -1 * (math.log(1 - mortality_rate[v][i]) / 365)

    default_mortality = MortalityDistribution(num_population_axes=2,
                                              axis_names=["gender", "age"],
                                              axis_units=["male=0,female=1", "years"],
                                              axis_scale_factors=[1, 365],
                                              population_groups=[[0, 1], [0]],
                                              result_scale_factor=1,
                                              result_units="daily probability of dying",
                                              result_values=[new_mortality_rate[0], new_mortality_rate[1]])
    return default_mortality


def MortalityStructureNigeriaDHS(demog):
    morts = [0, 0.0019158015385118965, 0.0019158015385118965, 0.0001717560763629944, 0.0001717560763629944, 4.9704718676046866e-05,
             4.9704718676046866e-05, 5.534972988163744e-06, 5.534972988163744e-06, 1.0006476080515192e-05, 1.0006476080515192e-05,
             0.0003153728749953899, 0.0003153728749953899, 0.99]
    mort_ages = [0, 0.0001, 0.08082191780821918, 0.08092191780821918, 1, 1.0001, 5, 5.0001, 15, 15.0001, 50, 50.0001, 90, 90.0001]
    mort_dist = {"MortalityDistribution": {"AxisNames": ["gender", "age"],
                                           "AxisUnits": ["male=0,female=1", "years"],
                                           "AxisScaleFactors": [1, 365],
                                           "PopulationGroups": [[0, 1], mort_ages],
                                           "ResultScaleFactor": 1,
                                           "ResultUnits": "daily probability of dying",
                                           "ResultValues": [morts, morts]}}
    demog.SetDefaultFromTemplate(mort_dist, _set_mortality_age_gender)


#
# Fertilty
#
def get_fert_dist_from_rates(rates: list[float]):
    """
    Create dictionary with DTK-compatible distributions from input vectors of fertility (crude) rates.

    Args:
        rates: Array/vector of crude rates for whole population, for a range of years.

    """
    fert_dist = {"FertilityDistribution": {"AxisNames": ["age", "year"],
                                           "AxisUnits": ["years", "simulation_year"],
                                           "AxisScaleFactors": [365, 1],
                                           "PopulationGroups": [[0, 125],
                                                                [x for x in range(len(rates))]],
                                           "ResultScaleFactor": 2.73972602739726e-03,
                                           "ResultUnits": "annual births per 1000 individuals",
                                           "ResultValues": [rates, rates]}}
    return FertilityDistribution().from_dict(fertility_distribution=fert_dist["FertilityDistribution"])


#
# Age Structure
#
def InitAgeUniform(demog):
    setting = {"AgeDistributionFlag": 1,
               "AgeDistribution1": 0,
               "AgeDistribution2": 18250}
    demog.SetDefaultFromTemplate(setting, _set_age_simple)


def _computeAgeDist(bval, mvecX, mvecY, fVec, max_yr=90):
    """
    Compute equilibrium age distribution given age-specific mortality and crude birth rates

    Args:
        bval: crude birth rate in births per day per person
        mvecX: list of age bins in days
        mvecY: List of per day mortality rate for the age bins
        fVec: Seasonal forcing per month
        max_yr : maximum agent age in years

    returns EquilibPopulationGrowthRate, MonthlyAgeDist, MonthlyAgeBins
    author: Kurt Frey
    """

    bin_size = 30
    day_to_year = 365

    # Age brackets
    avecY = np.arange(0, max_yr * day_to_year, bin_size) - 1

    # Mortality sampling
    mvecX = [-1] + mvecX + [max_yr * day_to_year + 1]
    mvecY = [mvecY[0]] + mvecY + [mvecY[-1]]
    mX = np.arange(0, max_yr * day_to_year, bin_size)
    mX[0] = 1
    mval = 1.0 - np.interp(mX, xp=mvecX, fp=mvecY)
    r_n = mval.size

    # Matrix construction
    BmatRC = (np.zeros(r_n), np.arange(r_n))
    Bmat = sp.csr_matrix(([bval * bin_size] * r_n, BmatRC), shape=(r_n, r_n))
    Mmat = sp.spdiags(mval[:-1] ** bin_size, -1, r_n, r_n)
    Dmat = Bmat + Mmat

    # Math
    (gR, popVec) = la.eigs(Dmat, k=1, sigma=1.0)
    gR = np.abs(gR ** (float(day_to_year) / float(bin_size)))
    popVec = np.abs(popVec) / np.sum(np.abs(popVec))

    # Apply seasonal forcing
    mVecR = [-2.0, 30.5, 30.6, 60.5, 60.6, 91.5, 91.6, 121.5,
             121.6, 152.5, 152.6, 183.5, 183.6, 213.5, 213.6, 244.5,
             245.6, 274.5, 274.6, 305.5, 305.6, 333.5, 335.6, 364.5]
    fVec = np.flipud([val for val in fVec for _ in (0, 1)])
    wfVec = np.array([np.mean(np.interp(np.mod(range(val + 1, val + 31), 365),
                                        xp=mVecR, fp=fVec)) for val in avecY]).reshape(-1, 1)
    popVec = popVec * wfVec / np.sum(popVec * wfVec)

    # Age sampling
    avecY[0] = 0
    avecX = np.clip(np.around(np.cumsum(popVec), decimals=7), 0.0, 1.0)
    avecX = np.insert(avecX, 0, np.zeros(1))

    return gR.tolist()[0], avecX[:-1].tolist(), avecY.tolist()


def AgeStructureUNWPP(demog):
    res_val = [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90]
    dist_val = [0, 0.164, 0.3077, 0.4317, 0.5381, 0.6289, 0.7066, 0.7721, 0.8256, 0.8690,
                0.9036, 0.9316, 0.9537, 0.9708, 0.9833, 0.9918, 0.9968, 0.9991, 1.0]
    setting = {"AgeDistribution": {"ResultUnits": "years",
                                   "ResultScaleFactor": 365,
                                   "ResultValues": res_val,
                                   "DistributionValues": dist_val}}
    demog.SetDefaultFromTemplate(setting, _set_age_complex)


def _EquilibriumAgeDistFromBirthAndMortRates(birth_rate=40.0, mortality_rate=20.0):
    """
    Set age distribution based on birth and death rates. Implicit function.

    Args:
        # birth_rate: births per person per year.
        birth_rate: (float) The birth rate in units of births/year/1000-women
        # mort_rate: deaths per person per year.
        mortality_rate: (float) The mortality rate in units of deaths/year/1000 people

    Returns:
        dictionary which can be inserted into demographics object.

    """
    # convert to daily rate per person, EMOD units
    birth_rate = (birth_rate / 1000) / 365 / 1  # what is actually used below
    mortality_rate = (mortality_rate / 1000) / 365 / 1 # what is actually used below

    birth_rate = math.log(1 + birth_rate)
    mortality_rate = -1 * math.log(1 - mortality_rate)

    # It is important for the age distribution computation that the age-spacing be very fine; I've used 30 days here.
    # With coarse spacing, the computation in practice doesn't work as well.
    ageDist = _computeAgeDist(birth_rate, [i * 30 for i in range(1200)], 1200 * [mortality_rate], 12 * [1.0])

    # The final demographics file, though, can use coarser binning interpolated from the finely-spaced computed distribution.
    EMODAgeBins = list(range(16)) + [20 + 5 * i for i in range(14)]
    EMODAgeDist = np.interp(EMODAgeBins, [i / 365 for i in ageDist[2]], ageDist[1]).tolist()
    EMODAgeBins.extend([90])
    EMODAgeDist.extend([1.0])
    setting = {"AgeDistribution": {"ResultUnits": "years",
                                   "ResultScaleFactor": 365,
                                   "ResultValues": EMODAgeBins,
                                   "DistributionValues": EMODAgeDist}}
    return setting
