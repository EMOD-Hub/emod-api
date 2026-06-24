from emod_api.utils.str_enum import StrEnum


class BirthRateDependence(StrEnum):
    """How BirthRate from the demographics file is interpreted by EMOD.

    Only modes that USE the BirthRate value are included here.
    to use ``INDIVIDUAL_PREGNANCIES_BY_AGE_AND_YEAR``
    use FertilityDistribution instead
    """
    FIXED_BIRTH_RATE = "FIXED_BIRTH_RATE"
    POPULATION_DEP_RATE = "POPULATION_DEP_RATE"
    DEMOGRAPHIC_DEP_RATE = "DEMOGRAPHIC_DEP_RATE"
    INDIVIDUAL_PREGNANCIES = "INDIVIDUAL_PREGNANCIES"
