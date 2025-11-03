import numpy as np
import math
import scipy.sparse        as sp
import scipy.sparse.linalg as la
import scipy.spatial.distance as dist
import pandas as pd
import json
from copy import deepcopy

from emod_api.demographics.node import Node
from emod_api.demographics.DemographicsFile import DemographicsFile

##Most everything in here needs to be updated or refactored for future purposes

# This probably belongs in a (small) loadbalancing section of emodapi, not demographics
def SpatialLoadBalancing(nCores, nodeInfoTable, outFile):
    """Create load balancing file based off of distance metric

    """

    lats = nodeInfoTable.latitude
    longs = nodeInfoTable.longitude
    pops = nodeInfoTable.population
    nodeIDs = nodeInfoTable.nodeID

    nodeData = pd.DataFrame(zip(lats, longs, pops), index=nodeIDs, columns=['lats', 'longs', 'pops'])

    # calculate euclidean distances between the nodes
    distances = dist.squareform(dist.pdist(np.vstack((longs, lats)).T, 'euclidean'))
    distances = pd.DataFrame(distances, index=nodeIDs, columns=nodeIDs)

    # Seed our initial list with N nodes that are maximally distant from each other
    coreNodes = []
    for _ in range(nCores):
        coreNodes.append([])
    corePops = [0 for _ in range(nCores)]

    startNodes = []
    startNodes.append(distances.max().idxmax())
    startNodes.append(distances.loc[startNodes[0]].idxmax())
    for i in range(2, nCores):
        tmpdist = distances.loc[startNodes[0]]
        for j in range(1, i):
            tmpdist *= distances.loc[startNodes[j]]
        startNodes.append(tmpdist.idxmax())

    # assign nodes
    tmpdist = deepcopy(distances)
    target_pop = nodeData['pops'].sum() / nCores

    for ix in range(nCores):
        while corePops[ix] < target_pop and len(tmpdist.index) > 0:
            node2add = tmpdist[startNodes[ix]].idxmin()
            coreNodes[ix].append(node2add)
            corePops[ix] += nodeData.loc[node2add]['pops']
            tmpdist.drop(node2add, axis=0, inplace=True)

    output = {'Load_Balance_Scheme_Nodes_On_Core_Matrix': [[int(y) for y in cN] for cN in coreNodes]}

    with open(outFile, 'w') as file:
        json.dump(output, file, indent=4)


def AdjustPopsToStartDate(nodes, PopFile, StartYear):
    #All of this gets much more complicated in the non-uniform demographics case, will need to evolve
    #demography back given differential growth rates; need a way to handle
    PopHistory = pd.read_csv(PopFile)
    NigeriaTotalPop = PopHistory[PopHistory['country'] == 'Nigeria'].groupby('year')['value'].sum()

    currPops = [node.pop for node in nodes]
    currTotalPop = sum(currPops)
    targetPop = NigeriaTotalPop[StartYear]
    scaleFac = targetPop/currTotalPop

    for node in nodes:
        node.pop = int(node.pop*scaleFac)
    return nodes


"""
The remaining functions here are (I believe) to spport various actual demographics profiles (fertility and mortality).
"""
def BuildInterpolatedBirthRateMap_UniformDemog(PopFile, DemoFile, StartYear, Duration, country='Nigeria'):
    """ Generate birth rate map from VIMC_POP_AGE File

    :param PopFile: VIMC_POP_AGE File Name
    :param DemoFile: Democgraphics file
    :param StartYear: Starting year for birth rate map
    :param Duration: Duration of simulation
    :param country: Country name

    """
    PopHistory = pd.read_csv(PopFile)
    CountryTotalPop = PopHistory[PopHistory['country'].str.lower() == country.lower()].groupby('year')['value'].sum()

    DF = DemographicsFile.from_file(DemoFile)
    BRScales = DF.content['Defaults']['IndividualAttributes']['META_TestBrScales']
    GrowthRates = DF.content['Defaults']['IndividualAttributes']['META_GrowthRates']
    BRMap = {'Times': [], 'Values': []}
    BRMap['Times'] = [i*365 for i in range(Duration+1)]
    for i in range(Duration+1):
        GrowthRate = CountryTotalPop[StartYear+i+1]/CountryTotalPop[StartYear+i]
        BRScale = np.interp(GrowthRate, GrowthRates, BRScales)
        BRMap['Values'].append(BRScale)

    return BRMap


def BuildInterpolatedBirthRateMap_HeterogeneousDemog(population_filename, demographics_filename):
    return None


def computeMortalityDist(dot_name, DemoDf):
    """
    Compute daily mortality rate from a probability of survival table.
    mortality formulated as probability of dying between age x and age x+1.  <5 bins from MICS 2017, 5-15 from World
    Bank, 15-50 from DHS, 50+ constant rate assumed 1% chance of living to 90.  Certain death above age 90.
    Edo and Enugu states are not reported in MICS due to small sample; took average of all bordering states for child mortality

    :param dot_name: Key indexing into the keys of the DemoDf
    :param DemoDf: Dict with deaths per 1000 for 'NN' (neonates), 'PN' (pst-neonates), and 'CH' (children).  dot_name is the key index into these
    """
    ageBins = [0, 29.5 / 365, 1, 5, 15, 50, 90]
    OverFiveRates = [.02, .12, .99]
    state = dot_name.split(':')[1]
    BaseMort = [DemoDf['NN'][state]/1000, DemoDf['PN'][state]/1000, DemoDf['CH'][state]/1000]+OverFiveRates

    mortVec = [0]
    for i in range(len(BaseMort)):
        binWidth = ageBins[i+1]-ageBins[i]
        rate = 1.0 - (1.0 - BaseMort[i]) ** (1.0 / (365.0*binWidth))
        mortVec.extend(2 * [rate])
    mortVec.extend([.99])
    newAgeBins = []
    for age in ageBins:
        newAgeBins.extend([age, age+.0001])
    return newAgeBins, mortVec

def MortalityAndAgeDistributions(dot_name, DemoDf, birthRate):

    mortDistBins, EMODmortDist = computeMortalityDist(dot_name, DemoDf)
    mortDist = {
            "NumDistributionAxes": 2,
            "AxisNames": ["gender","age"],
            "AxisUnits": ["male=0,female=1","years"],
            "AxisScaleFactors": [1,365],
            "NumPopulationGroups": [2,len(mortDistBins)],
            "PopulationGroups": [
                [0,1],
                mortDistBins
            ],
            "ResultScaleFactor":1,
            "ResultUnits": "daily probability of dying",
            "ResultValues": [
                EMODmortDist,
                EMODmortDist
            ]
        }

    MonthlyAgeDist, MonthlyAgeBins = computeAgeDist(birthRate, [i*365 for i in mortDistBins], EMODmortDist, 12*[1.0])[1:]

    #Compute population growth rates at various scalars on the birth rate, to help with figuring out how to
    #reduce birth rate over time to slow population growth
    #Should probably separate into it's own function, but easier to deal with here.
    BRScalars = [0.8, 0.85, 0.9, 0.95, 1.0, 1.05, 1.1]
    GrowthRates = []
    for testBR in BRScalars:
        GrowthRates.append(computeAgeDist(testBR*birthRate, [i*365 for i in mortDistBins], EMODmortDist, 12*[1.0])[0])

    #computeAgeDist returns in 30 day age bins, much too tight for our needs
    EMODAgeBins = list(range(16)) + [20+5*i for i in range(14)]
    EMODAgeDist = np.interp(EMODAgeBins, [i/365 for i in MonthlyAgeBins], MonthlyAgeDist).tolist()
    EMODAgeBins.extend([90])
    EMODAgeDist.extend([1.0])
    ageDist = {
        "NumDistributionAxes": 0,
        "ResultUnits": "years",
        "ResultScaleFactor": 365,
        "ResultValues": EMODAgeBins,
        "DistributionValues": EMODAgeDist
    }

    mortAndAgeDists = {
        "DESC_MortDist": "Mortality distributions from DHS 2013",
        "MortalityDistribution": mortDist,
        "DESC_AgeDist": "Steady State Age distribution from birth rate and mortality rates",
        "AgeDistribution": ageDist
    }

    return mortAndAgeDists, BRScalars, GrowthRates


def computeAgeDist(bval,mvecX,mvecY,fVec):
    """compute equilibrium age distribution given age-specific mortality and crude birth rates

    :param bval: crude birth rate in births per day per person
    :param mvecX: list of age bins in days
    :param mvecY: List of per day mortality rate for the age bins
    :param fVec: Seasonal forcing per month


    returns ??, MonthlyAgeDist, MonthlyAgeBins
    author: Kurt Frey
    """

    max_yr = 90
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

