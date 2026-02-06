from enum import Enum


class DemographicDistributionFlag(Enum):
    CONSTANT = 0
    UNIFORM = 1
    GAUSSIAN = 2
    EXPONENTIAL = 3
    POISSON = 4
    LOG_NORMAL = 5
    BIMODAL = 6
    WEIBULL = 7

    # Not supported for demographics
    # DUAL_CONSTANT = -1
    # DUAL_EXPONENTIAL = -2
