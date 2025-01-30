import numpy as np
import math
import scipy.sparse        as sp
import scipy.sparse.linalg as la
from collections import defaultdict
from emod_api.demographics.PropertiesAndAttributes import IndividualAttributes, NodeAttributes
import copy
from pathlib import Path

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

class CrudeRate(): # would like to derive from float
    def __init__(self, init_rate):
        self._time_units = 365
        self._people_units = 1000
        self._rate = init_rate
    def get_dtk_rate(self):
        return self._rate / self._time_units / self._people_units

class YearlyRate(CrudeRate): # would like to derive from float
    def __init__(self, init_rate):
        self._time_units = 365
        self._people_units = 1
        if type(init_rate) is CrudeRate:
            self._rate = init_rate._rate/1000.
        else:
            self._rate = init_rate

class DtkRate(CrudeRate):
    def __init__(self, init_rate):
        super().__init__(init_rate)
        self._time_units = 1
        self._people_units = 1
        self._rate = init_rate


# Migration
def _set_migration_model_fixed_rate(config):
    config.parameters.Migration_Model = "FIXED_RATE_MIGRATION"
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
def _set_suscept_complex( config ):
    config.parameters.Susceptibility_Initialization_Distribution_Type = "DISTRIBUTION_COMPLEX"
    return config

def _set_suscept_simple( config ):
    config.parameters.Susceptibility_Initialization_Distribution_Type = "DISTRIBUTION_SIMPLE"
    return config

# Age Structure
def _set_age_simple( config ):
    config.parameters.Age_Initialization_Distribution_Type = "DISTRIBUTION_SIMPLE"
    return config

def _set_age_complex( config ):
    config.parameters.Age_Initialization_Distribution_Type = "DISTRIBUTION_COMPLEX"
    return config

# Initial Prevalence
def _set_init_prev( config ):
    config.parameters.Enable_Initial_Prevalence = 1
    return config

# Mortality
def _set_enable_natural_mortality( config ):
    config.parameters.Enable_Natural_Mortality = 1
    return config

def _set_mortality_age_gender( config ):
    config.parameters.Death_Rate_Dependence = "NONDISEASE_MORTALITY_BY_AGE_AND_GENDER"
    return config

def _set_mortality_age_gender_year( config ):
    config.parameters.Death_Rate_Dependence = "NONDISEASE_MORTALITY_BY_YEAR_AND_AGE_FOR_EACH_GENDER"
    return config

# Fertility
def _set_fertility_age_year( config ):
    config.parameters.Birth_Rate_Dependence = "INDIVIDUAL_PREGNANCIES_BY_AGE_AND_YEAR"
    return config

def _set_enable_births( config ):
    config.parameters.Birth_Rate_Dependence = "POPULATION_DEP_RATE"
    return config

# Risk
def _set_enable_demog_risk( config ):
    config.parameters.Enable_Demographics_Risk = 1
    return config
# 
# Risk
#
"""
This submodule contains a bunch of json blobs that are valid pieces of a demographics json file.
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

def FullRisk( demog, description="" ):
    """
    FullRisk puts everyone at 100% risk.
    """
    if not description:
        description = f"Setting full risk using default values"

    setting = {"RiskDist_Description": "Full risk",
            "RiskDistributionFlag": 0, # 0 = CONSTANT
            "RiskDistribution1": 1,
            "RiskDistribution2": 0,
            "RiskDistribution_Description": description}
    demog.SetDefaultFromTemplate( setting, _set_enable_demog_risk  )

def InitRiskUniform( demog, min_lim=0, max_lim=1, description="" ):
    """
    InitRiskUniform puts everyone at somewhere between 0% risk and 100% risk, drawn uniformly.

    Args:
        min (float): Low end of uniform distribution. Must be >=0, <1.
        max (float): High end of uniform distribution. Must be >=min, <=1.
        description: Why were these values chosen?

    Returns:
        json object aka python dict that can be directly passed to Demographics::SetDefaultFromTemplate

    Raises:
        None

    """
    if not description:
        description = f"Risk is drawn from a uniform distribution, min_lim={min_lim} and max_lim={max_lim}"

    if min_lim<0:
        raise ValueError( f"min_lim value of {min_lim} is less than 0. Not valid." )
    setting = {"RiskDist_Description": "Uniformly distributed risk",
               "RiskDistributionFlag": 1,
               "RiskDistribution1": min_lim,
               "RiskDistribution2": max_lim,
               "RiskDistribution_Description": description}
    demog.SetDefaultFromTemplate( setting, _set_enable_demog_risk  )

def InitRiskLogNormal( demog, mean=0.0, sigma=1.0 ):
    """
    InitRiskLogNormal puts everyone at somewhere between 0% risk and 100% risk, drawn from LogNormal.

    Args:
        mean (float): Mean of lognormal distribution.
        sigma (float): Sigma of lognormal distribution.

    Returns:
        json object aka python dict that can be directly passed to Demographics::SetDefaultFromTemplate

    Raises:
        None

    """
    setting = {"RiskDist_Description": "LogNormal distributed risk",
            "RiskDistributionFlag": 5, # lognormal
            "RiskDistribution1": mean,
            "RiskDistribution2": sigma }
    demog.SetDefaultFromTemplate( setting, _set_enable_demog_risk )

def InitRiskExponential( demog, mean=1.0 ):
    """
    InitRiskExponential puts everyone at somewhere between 0% risk and 100% risk, drawn from Exponential.

    Args:
        mean (float): Mean of exponential distribution. 

    Returns:
        json object aka python dict that can be directly passed to Demographics::SetDefaultFromTemplate

    Raises:
        None

    """
    setting = {"RiskDist_Description": "Exponentially distributed risk",
            "RiskDistributionFlag": 3, # exponential
            "RiskDistribution1": mean,
            "RiskDistribution2": 0 }
    demog.SetDefaultFromTemplate( setting, _set_enable_demog_risk )

# 
# Initial Prevalence
# config: Enable_Initial_Prevalence=1
#
def NoInitialPrevalence( demog ):
    """
    NoInitialPrevalence disables initial prevalence; outbreak seeding must be done from an Outbreak intervention (or serialized population).

    Args:
        demog: emod-api.demographics.Demographics instance.

    Returns:
        None

    Raises:
        None
    """

    setting = {"PrevalenceDist_Description": "No initial prevalence",
               "InitialPrevalence": 0,
              }
    # why not just disable it at config?
    demog.SetDefaultFromTemplate( setting )

def InitPrevUniform( demog, low_prev, high_prev, description="" ):
    # old
    if not description:
        description = f"Drawing prevalence from uniform distribution, low_prev={low_prev} and high_prev={high_prev}"

    setting = {"PrevalenceDist_Description": f"Uniform draw from {low_prev} to {high_prev}",
               "PrevalenceDistributionFlag": 1,
               "PrevalenceDistribution1": low_prev,
               "PrevalenceDistribution2": high_prev,
               "PrevalenceDistribution_Description": description}
    # new
    #setting.update( { "InitialPrevalence": prevalence } )
    demog.SetDefaultFromTemplate( setting, _set_init_prev )

# 
# Initial Susceptibility (1-Immunity)
#

def InitSusceptConstant( demog ):
    # set config.Susceptibility_... SIMPLE
    setting = {"SusceptibilityDistributionFlag": 0,
            "SusceptibilityDistribution1": 1,
            "SusceptibilityDistribution2": 0 }
    demog.SetDefaultFromTemplate( setting, _set_suscept_simple )

def EveryoneInitiallySusceptible( demog, setting=1.0 ):
    # set config.Susceptibility_Initialization_Distribution_Type=COMPLEX
    suscDist = {
        "SusceptibilityDist_Description": f"Everyone is initially susceptible with probability {setting}",
        "SusceptibilityDistribution": {
            "DistributionValues": [0, 36500],
            "ResultScaleFactor": 1,
            "ResultValues": [setting, setting]
        }
    }
    demog.SetDefaultFromTemplate( suscDist, _set_suscept_complex )

def StepFunctionSusceptibility( demog, protected_setting=0.0, threshold_age=365*5.0 ):
    # set config.Susceptibility_Initialization_Distribution_Type=COMPLEX
    suscDist = {
        "SusceptibilityDist_Description": "Youngers are somewhat protected",
        "SusceptibilityDistribution": {
            "DistributionValues": [0, threshold_age, threshold_age, 36500],
            "ResultScaleFactor": 1,
            "ResultValues": [protected_setting, protected_setting, 1.0, 1.0]
        }
    }
    demog.SetDefaultFromTemplate( suscDist, _set_suscept_complex )

def SimpleSusceptibilityDistribution( demog, meanAgeAtInfection=2.5): 
    """
    Rough initialization to reduce burn-in and prevent huge outbreaks at sim start.  
    For ages 0 through 99 the susceptibility distribution is set to an exponential distribution with an average age at infection.
    The minimum susceptibility is 2.5% at old ages.

    Args:
        demog (:py:class:`~emod_api.demographics.Demographics.Demographics`): Demographics object to update
        meanAgeAtInfection (float, optional): Rough average age at infection in years.

    Note:
    Requires that ``config.parameters.Susceptibility_Initialization_Distribution_Type=DISTRIBUTION_COMPLEX``

    """
    # set config.Susceptibility_Initialization_Distribution_Type=COMPLEX
    # This function is first to be switched over to be reversed.
    # Calling code in emodpy will call this and pass the demographics instance then we
    # call SetDefaultFromTemplate on the demog object so we can also pass the setter function
    suscDist = {
        "SusceptibilityDist_Description": f"Rough initialization to reduce burn-in and prevent huge outbreaks at "
                                          f"sim start.  Exponential distribution, Average age at infection "
                                          f"~{meanAgeAtInfection} years, minimum susceptibility is 2.5% at old ages",
        "SusceptibilityDistribution": {
            "DistributionValues":  [i * 365 for i in range(100)],
            "ResultScaleFactor": 1,
            "ResultValues":  [1.0, 1.0] + [0.025 + 0.975 * math.exp(-(i - 1) / (meanAgeAtInfection / math.log(2)))
                                           for i in range(2, 100, 1)]
        }
    }
    demog.SetDefaultFromTemplate( suscDist, _set_suscept_complex )

def DefaultSusceptibilityDistribution( demog ): 
    # set config.Susceptibility_Initialization_Distribution_Type=COMPLEX
    suscDist = {
        "SusceptibilityDist_Description": "Rough initialization to reduce burn-in and prevent huge outbreaks at sim "
                                          "start.  Exponential distribution, Average age at infection ~3.5 years,"
                                          "minimum susceptibility is 2.5% at old ages",
        "SusceptibilityDistribution": {
            "DistributionValues": [i * 365 for i in range(100)],
            "ResultScaleFactor": 1,
            "ResultValues":  [1.0, 1.0] + [0.025 + 0.975 * math.exp(-(i - 1) / (2.5 / math.log(2)))
                                           for i in range(2, 100, 1)]
        }
    }
    demog.SetDefaultFromTemplate( suscDist, _set_suscept_complex )

#
# Mortality
#
def MortalityRateByAge(demog, age_bins, mort_rates):
    """
        Set (non-disease) mortality rates by age bins. No checks are done on input arrays.

        Args:
            age_bins: list of age bins, with ages in years.
            mort_rates: list of mortality rates, where mortality rate is daily probability of dying..

        Returns:
            N/A.
    """
    # Note that the first input axis is sex (or gender). There are two values, but the rates are applied
    # equally for both here. The second input axis is age bin, and that is much more configurable.
    mort_dist = {
        "MortalityDistribution": {
        "NumDistributionAxes": 2,
        "AxisNames": ["gender", "age"],
        "AxisUnits": ["male=0,female=1", "years"],
        "AxisScaleFactors": [1, 365],
        "PopulationGroups": [
            [0, 1],
            age_bins
        ],
        "ResultScaleFactor": 1,
        "ResultUnits": "daily probability of dying",
        "ResultValues": [
            mort_rates,
            mort_rates
        ]
    }
    }
    demog.SetDefaultFromTemplate( mort_dist, _set_mortality_age_gender )

def _ConstantMortality(mortality_rate: float):
    if type(mortality_rate) is float:
        #temp = -1 * (math.log(1 - mortality_rate) / 365)
        temp = -1 * (math.log(1 - mortality_rate))
        new_mortality_rate = [[temp], [temp]]
    else:  # assume list
        new_mortality_rate = copy.deepcopy(mortality_rate)
        for v in range(len(mortality_rate)):
            for i in range(len(mortality_rate[v])):
                new_mortality_rate[v][i] = -1 * (math.log(1 - mortality_rate[v][i]) / 365)

    default_mortality = IndividualAttributes.MortalityDistribution(num_population_axes=2,
                                                                   axis_names=["gender", "age"],
                                                                   axis_units=["male=0,female=1", "years"],
                                                                   axis_scale_factors=[1, 365],
                                                                   population_groups=[[0, 1], [0]],
                                                                   result_scale_factor=1,
                                                                   result_units="daily probability of dying",
                                                                   result_values=[new_mortality_rate[0],
                                                                                  new_mortality_rate[1]])
    return default_mortality

def MortalityStructureNigeriaDHS(demog):
    morts = [ 0,0.0019158015385118965,0.0019158015385118965,0.0001717560763629944, 0.0001717560763629944, 4.9704718676046866e-05,4.9704718676046866e-05,5.534972988163744e-06,5.534972988163744e-06, 1.0006476080515192e-05,1.0006476080515192e-05,0.0003153728749953899,0.0003153728749953899,0.99]
    mort_dist = {
        "MortalityDistribution": {
        "NumDistributionAxes": 2,
        "AxisNames": ["gender","age"],
        "AxisUnits": ["male=0,female=1","years"],
        "AxisScaleFactors": [1,365],
        "PopulationGroups": [
            [0,1],
            [0,0.0001,0.08082191780821918,0.08092191780821918,1,1.0001,5,5.0001,15,15.0001,50,50.0001,90,90.0001]
        ],
        "ResultScaleFactor":1,
        "ResultUnits": "daily probability of dying",
        "ResultValues": [morts, morts]
        }
    }
    demog.SetDefaultFromTemplate( mort_dist, _set_mortality_age_gender )

#
# Fertilty
#
def get_fert_dist_from_rates( rates ):
    """
    Create dictionary with DTK-compatible distributions from input vectors of fertility (crude) rates.

    Args:
        rates: Array/vector of crude rates for whole population, for a range of years.

    """
    fert_dist = {
        "FertilityDistribution": {
            "NumDistributionAxes": 2,
            "AxisNames": ["age","year"],
            "AxisUnits": ["years","simulation_year"],
            "AxisScaleFactors": [365,1],
            "NumPopulationGroups": [
                2,
                len(rates)
            ],
            "PopulationGroups": [
                [0,125],
                [x for x in range(len(rates))]
            ],
            "ResultScaleFactor": 2.73972602739726e-03,
            "ResultUnits": "annual births per 1000 individuals",
            "ResultValues": [ rates, rates ]
        }
    }
    return IndividualAttributes.FertilityDistribution().from_dict( fertility_distribution=fert_dist["FertilityDistribution"] )


def get_fert_dist(path_to_csv, verbose=False):
    """
        This function takes a fertility csv file (by year and age bin) and populates a DTK demographics.json file,
        and the corresponding config file to do individual pregnancies by age and year from data.

        Args:
            demog: emod_api.demographics.Demographics instance.
            path_to_csv: absolute path to csv input file. The file should have columns for 5-year age bins
            labelled "15-19", etc. up to "45-49", and a column named "Years" with values like "1950-1955".
            There can be extra columns and the columns can be anywhere.

        Returns:
            (complex) dictionary. fertility distribution, ready to be added to demographics file.
    """
    fert_dist = {
        "FertilityDistribution": {
            "NumDistributionAxes": 2,
            "AxisNames": ["age","year"],
            "AxisUnits": ["years","simulation_year"],
            "AxisScaleFactors": [365,1],
            "PopulationGroups": [
                [],
                []
            ],
            "ResultScaleFactor": 2.73972602739726e-06,
            "ResultUnits": "annual births per 1000 individuals",
            "ResultValues": []
        }
    }
    # open and parse csv. We expect the age bins to be 5 year buckets
    import csv

    data = defaultdict( dict )
    age_bins=["15-19","20-24","25-29","30-34","35-39","40-45","45-49"]
    with open(path_to_csv, mode='r') as csv_file:
        csv_reader = csv.DictReader(csv_file)
        line_count = 0
        for row in csv_reader:
            if line_count == 0:
                if verbose:
                    print(f'Fertility data file column names are {", ".join(row)}')
                line_count += 1
            year = row["Years"]
            for age_bin in age_bins:
                #if year not in data:
                #    data[year] = {}
                data[year][age_bin] = row[age_bin]
            line_count += 1
        if verbose:
            print(f'Found {line_count} rows of fertility data.')
        if line_count == 0:
            raise ValueError( f"Read no fertility data from {path_to_csv}." )
    # Need to construct [ 1950, 1954.99, 1955, 1959.99, etc] from ["1950-1955", etc.]
    def bounds_from_buckets( bucket_list, off_by_one=False ):
        boundaries = []
        for yr_buck in bucket_list:
            edges = yr_buck.split('-')
            lhs = int(edges[0])
            rhs = int(edges[1])
            if off_by_one:
                rhs += 1
            boundaries.append( lhs )
            boundaries.append( rhs-0.01 )  # magic number alert
        return boundaries

    num_age_bins = len(age_bins)
    age_bin_boundaries = bounds_from_buckets( age_bins, True )
    fert_dist["FertilityDistribution"]["PopulationGroups"][0] = age_bin_boundaries

    sim_year_boundaries = bounds_from_buckets( list( data.keys() ) )
    num_years = len(data.keys())
    fert_dist["FertilityDistribution"]["PopulationGroups"][1] = sim_year_boundaries

    # transpose the data. Put all the 15-19's into a single list
    for age_bin in age_bins:
        age_bin_values = []
        for data_row in data:
            age_bin_values.append( float(data[data_row][age_bin]) )
            age_bin_values.append( float(data[data_row][age_bin]) )
        fert_dist["FertilityDistribution"]["ResultValues"].append( age_bin_values )
        fert_dist["FertilityDistribution"]["ResultValues"].append( age_bin_values )
    return fert_dist

#
# Age Structure
#
def InitAgeUniform( demog ):
    setting = { "AgeDistributionFlag": 1,
                "AgeDistribution1": 0,
                "AgeDistribution2": 18250 }
    demog.SetDefaultFromTemplate( setting, _set_age_simple )

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

def AgeStructureUNWPP( demog ):
    setting = {
            "AgeDistribution": {
                "NumDistributionAxes": 0,
                "ResultUnits": "years",
                "ResultScaleFactor": 365,
                "ResultValues": [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90],
                "DistributionValues": [0, 0.164, 0.3077, 0.4317, 0.5381, 0.6289, 0.7066, 0.7721, 0.8256, 0.8690, 0.9036,
                                       0.9316, 0.9537, 0.9708, 0.9833, 0.9918, 0.9968, 0.9991, 1.0]
                }
            }
    demog.SetDefaultFromTemplate( setting, _set_age_complex )

def _EquilibriumAgeDistFromBirthAndMortRates(birth_rate=YearlyRate(40/1000.), mort_rate=YearlyRate(20/1000.)):
    """
    Set age distribution based on birth and death rates.

    Args:
        birth_rate: births per person per year.
        mort_rate: deaths per person per year.

    Returns:
        dictionary which can be inserted into demographics object.

    """
    BirthRate = math.log(1 + birth_rate.get_dtk_rate())
    MortRate = -1 * math.log(1 - mort_rate.get_dtk_rate())
    
    # It is important for the age distribution computation that the age-spacing be very fine; I've used 30 days here.
    # With coarse spacing, the computation in practice doesn't work as well.
    ageDist = _computeAgeDist(BirthRate, [i * 30 for i in range(1200)], 1200 * [MortRate], 12 * [1.0])

    # The final demographics file, though, can use coarser binning interpolated from the finely-spaced computed distribution.
    EMODAgeBins = list(range(16)) + [20+5*i for i in range(14)]
    EMODAgeDist = np.interp(EMODAgeBins, [i/365 for i in ageDist[2]], ageDist[1]).tolist()
    EMODAgeBins.extend([90])
    EMODAgeDist.extend([1.0])
    setting = { "AgeDistribution": {
            "NumDistributionAxes": 0,
            "ResultUnits": "years",
            "ResultScaleFactor": 365,
            "ResultValues": EMODAgeBins,
            "DistributionValues": EMODAgeDist
            }
        }
    return setting


def birthrate_multiplier(pop_dat_file: Path, base_year: int, start_year: int, max_daily_mort: float=0.01):
    """
    Create a birth rate multiplier from UN World Population data file.
    Args:
        pop_dat_file: path to UN World Population data file
        base_year: Base year/Reference year
        start_year: Read in the pop_dat_file starting with year 'start_year'
        max_daily_mort: Maximum daily mortality rate

    Returns:
        bith_rate_multiplier_x, birth_rate_multiplier_y
    """
    # Load reference data
    year_vec, year_init, pop_mat, pop_init = _read_un_worldpop_file(pop_dat_file, base_year, start_year)

    t_delta = np.diff(year_vec)
    pow_vec = 365.0*t_delta
    mortvecs = _calculate_mortility_vectors(pop_mat, t_delta, max_daily_mort)

    tot_pop  = np.sum(pop_mat, axis=0)
    tpop_mid = (tot_pop[:-1]+tot_pop[1:])/2.0
    pop_corr = np.exp(-mortvecs[0, :]*pow_vec/2.0)

    brate_vec = np.round(pop_mat[0, 1:]/tpop_mid/t_delta*1000.0, 1)/pop_corr
    brate_val = np.interp(year_init, year_vec[:-1], brate_vec)

    # Calculate birth rate multiplier
    yrs_off = year_vec[:-1]-year_init
    yrs_dex = (yrs_off>0)

    birth_rate_mult_x_temp = np.array([0.0] + (365.0*yrs_off[yrs_dex]).tolist())
    birth_rate_mult_y_temp = np.array([1.0] + (brate_vec[yrs_dex]/brate_val).tolist())
    bith_rate_multiplier_x = np.zeros(2*len(birth_rate_mult_x_temp)-1)
    birth_rate_multiplier_y = np.zeros(2*len(birth_rate_mult_y_temp)-1)

    bith_rate_multiplier_x[0::2] = birth_rate_mult_x_temp[0:]
    birth_rate_multiplier_y[0::2] = birth_rate_mult_y_temp[0:]
    bith_rate_multiplier_x[1::2] = birth_rate_mult_x_temp[1:]-0.5
    birth_rate_multiplier_y[1::2] = birth_rate_mult_y_temp[0:-1]

    return bith_rate_multiplier_x, birth_rate_multiplier_y


def _calculate_mortility_vectors(pop_mat, t_delta, max_daily_mort):
    pow_vec = 365.0 * t_delta
    diff_ratio = (pop_mat[:-1, :-1]-pop_mat[1:,1:])/pop_mat[:-1, :-1]
    mortvecs   = 1.0-np.power(1.0-diff_ratio, 1.0/pow_vec)
    mortvecs   = np.minimum(mortvecs, max_daily_mort)
    mortvecs   = np.maximum(mortvecs,            0.0)
    return mortvecs


def _calculate_birth_rate_vector(pop_mat, mortvecs, t_delta, year_vec, year_init):
    pow_vec = 365.0*t_delta
    tot_pop    = np.sum(pop_mat, axis=0)
    tpop_mid   = (tot_pop[:-1]+tot_pop[1:])/2.0
    pop_corr   = np.exp(-mortvecs[0, :]*pow_vec/2.0)

    brate_vec  = np.round(pop_mat[0, 1:]/tpop_mid/t_delta*1000.0, 1)/pop_corr
    brate_val  = np.interp(year_init, year_vec[:-1], brate_vec)
    return brate_vec, brate_val

def _read_un_worldpop_file(pop_dat_file, base_year, start_year):
    pop_input = np.loadtxt(pop_dat_file, dtype=int, delimiter=',')

    year_vec = pop_input[0, :] - base_year
    year_init = start_year - base_year
    pop_mat = pop_input[1:, :] + 0.1

    pop_init = [np.interp(year_init, year_vec, pop_mat[idx, :]) for idx in range(pop_mat.shape[0])]
    return year_vec, year_init, pop_mat, pop_init


def demographicsBuilder(pop_dat_file: Path, base_year: int, start_year: int=1950, max_daily_mort: float=0.01,
                        mortality_rate_x_values: list=DemographicsTemplatesConstants.Mortality_Rates_Mod30_5yrs_Xval,
                        years_per_age_bin: int=5):
    """
    Build demographics from UN World Population data.
    Args:
        pop_dat_file: path to UN World Population data file
        base_year: Base year/Reference year
        start_year: Read in the pop_dat_file starting with year 'start_year'
        years_per_age_bin: The number of years in one age bin, i.e. in one row of the UN World Population data file
        max_daily_mort: Maximum daily mortality rate
        mortality_rate_x_values: The distribution of non-disease mortality for a population.

    Returns:
        IndividualAttributes, NodeAttributes
    """
    Days_per_Year = 365

    year_vec, year_init, pop_mat, pop_init = _read_un_worldpop_file(pop_dat_file, base_year, start_year)

    # create age bins in days
    pop_age_days = [bin_index * years_per_age_bin * Days_per_Year for bin_index in range(len(pop_init))]

    # Calculate vital dynamics
    t_delta = np.diff(year_vec)
    mortvecs = _calculate_mortility_vectors(pop_mat, t_delta, max_daily_mort)
    brate_vec, brate_val = _calculate_birth_rate_vector(pop_mat, mortvecs, t_delta, year_vec, year_init)
    birth_rate = brate_val/365.0/1000.0

    na = NodeAttributes()
    na.birth_rate = birth_rate

    age_y = pop_age_days
    age_init_cdf = np.cumsum(pop_init[:-1])/np.sum(pop_init)
    age_x = [0] + age_init_cdf.tolist()

    ad = IndividualAttributes.AgeDistribution()
    ad.distribution_values = age_x
    ad.result_scale_factor = 1
    ad.result_values = age_y

    mort_vec_x = mortality_rate_x_values
    mort_year = np.zeros(2*year_vec.shape[0]-3)
    mort_year[0::2] = year_vec[0:-1]
    mort_year[1::2] = year_vec[1:-1]-1e-4
    mort_year = mort_year.tolist()

    mort_mat = np.zeros((len(mort_vec_x), len(mort_year)))
    mort_mat[0:-2:2, 0::2] = mortvecs
    mort_mat[1:-2:2, 0::2] = mortvecs
    mort_mat[0:-2:2, 1::2] = mortvecs[:, :-1]
    mort_mat[1:-2:2, 1::2] = mortvecs[:, :-1]
    mort_mat[-2:, :] = max_daily_mort

    md = IndividualAttributes.MortalityDistribution()
    md.axis_names = ['age', 'year']
    md.axis_scale_factors = [1, 1]
    md.num_distribution_axes = 2
    md.num_population_groups = [len(mort_vec_x), len(mort_year)]
    md.population_groups = [mort_vec_x, mort_year]
    md.result_scale_factor = 1
    md.result_values = mort_mat.tolist()

    ia = IndividualAttributes()
    ia.age_distribution = ad
    ia.mortality_distribution_female = md
    ia.mortality_distribution_male = md

    return ia, na

