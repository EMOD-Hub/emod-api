import math
import numpy as np
import pandas as pd
import os

from scipy import sparse as sp
from scipy.sparse import linalg as la
from typing import Union

from emod_api.demographics.age_distribution import AgeDistribution
from emod_api.demographics.mortality_distribution import MortalityDistribution


def generate_equilibrium_age_distribution(birth_rate: float = 40.0, mortality_rate: float = 20.0) -> AgeDistribution:
    """
    Create an AgeDistribution object representing an equilibrium for birth and mortality rates.

    Args:
        birth_rate: (float) The birth rate in units of births/year/1000-women
        mortality_rate: (float) The mortality rate in units of deaths/year/1000 people

    Returns:
        an AgeDistribution object
    """
    from emod_api.demographics.age_distribution import AgeDistribution

    # convert to daily rate per person, EMOD units
    birth_rate = (birth_rate / 1000) / 365  # what is actually used below
    mortality_rate = (mortality_rate / 1000) / 365  # what is actually used below

    birth_rate = math.log(1 + birth_rate)
    mortality_rate = -1 * math.log(1 - mortality_rate)

    # It is important for the age distribution computation that the age-spacing be very fine; I've used 30 days here.
    # With coarse spacing, the computation in practice doesn't work as well.
    age_dist_tuple = _computeAgeDist(birth_rate, [i * 30 for i in range(1200)], 1200 * [mortality_rate], 12 * [1.0])

    # The final demographics file, though, can use coarser binning interpolated from the finely-spaced computed distribution.
    age_bins = list(range(16)) + [20 + 5 * i for i in range(14)]
    cum_pop_fraction = np.interp(age_bins, [i / 365 for i in age_dist_tuple[2]], age_dist_tuple[1]).tolist()
    age_bins.extend([90])
    cum_pop_fraction.extend([1.0])
    distribution = AgeDistribution(ages_years=age_bins, cumulative_population_fraction=cum_pop_fraction)
    return distribution


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


def generate_mortality_over_time_from_data(data_csv: Union[str, os.PathLike],
                                           base_year: int) -> MortalityDistribution:
    """
    Generate a MortalityDistribution object from a data csv file.

    Args:
        data_csv: Path to csv file with the mortality rates by calendar year and age bucket.
        base_year: The calendar year the sim is treating as the base.

    Returns:
        a MortalityDistribution object.
    """
    if base_year < 0:
        raise ValueError(f"User passed negative value of base_year: {base_year}.")
    if base_year > 2050:
        raise ValueError(f"User passed too large value of base_year: {base_year}.")

    # Load csv. Convert rate arrays into DTK-compatiable JSON structures.
    rates = []  # array of arrays, but leave that for a minute
    df = pd.read_csv(data_csv)
    header = df.columns
    year_start = int(header[1]) # someone's going to come along with 1990.5, etc. Sigh.
    year_end = int(header[-1])
    if year_end <= year_start:
        raise ValueError(f"Failed check that {year_end} is greater than {year_start} in csv dataset.")
    num_years = year_end - year_start + 1
    rel_years = list()
    for year in range(year_start, year_start + num_years):
        mort_data = list(df[str(year)])
        rel_years.append(year - base_year)

    age_key = None
    for trykey in df.keys():
        if trykey.lower().startswith("age"):
            age_key = trykey
            raw_age_bins = list(df[age_key])

    if age_key is None:
        raise ValueError("Failed to find 'Age_Bin' (or similar) column in the csv dataset. Cannot process.")

    age_bins = list()
    try:
        for age_bin in raw_age_bins:
            left_age = float(age_bin.split("-")[0])
            age_bins.append(left_age)

    except Exception as ex:
        raise ValueError(f"Ran into error processing the values in the Age-Bin column. {ex}")

    for idx in range(len(age_bins)):  # 18 of these
        # mort_data is the array of mortality rates (by year bin) for age_bin
        mort_data = list(df.transpose()[idx][1:])
        rates.append(mort_data)  # 28 of these, 1 for each year, eg

    distribution = MortalityDistribution(ages_years=age_bins, mortality_rate_matrix=rates, calendar_years=rel_years)
    return distribution
