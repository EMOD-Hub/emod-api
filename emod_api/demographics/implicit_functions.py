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


def _set_demographic_filenames(config, filenames):
    config.parameters.Demographics_Filenames = filenames
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
