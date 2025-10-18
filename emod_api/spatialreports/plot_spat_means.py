"""
This script assumes local SpatialReport_XXX.bin files which have been downloaded (from COMPS)
using pyCOMPS getexpout function or equivalent. Note that this interacts with files on an experiment
basis, not simulation basis. It assumes the files are in a subdirectory named after the experiment id,
and then in subdirectories of that named after the simulation id.

<exp_id>/
  <sim1_id>/
      SpatialReport_XXX.bin
  <sim2_id>/
      SpatialReport_XXX.bin

The idea is that the data is most interesting not on a simulation basis, but for an experiment,
especially aggregated on a certain sweep param and value. This plot calculates means and plots those.

Option 1: For each node, plot the mean of the specified channel for all files (values) found in experiment.
Option 2: For each node, plot the mean of the specified channel for all files (values) found in experiment _limited_ by specified tag key-value pair.
There is little to no assistance here so you need to specify a valid key and value.
"""

import os
import emod_api.spatialreports.spatial as sr
import matplotlib.pyplot as plt
import numpy as np
import sqlite3


def collect(exp_id, chan="Prevalence", tag=None):
    node_chan_data = {}
    node_chan_means = {}
    groupby_values = {}
    if tag:
        if len(tag.split("=")) == 1:
            raise ValueError("When passing tag, has to have key=value format.")

        groupby_key = tag.split("=")[0]
        groupby_value = tag.split("=")[1]
        db = os.path.join("latest_experiment", "results.db")
        con = sqlite3.connect(db)
        cur = con.cursor()

        query = f"SELECT sim_id FROM results where CAST({groupby_key} AS DECIMAL)-CAST({groupby_value} AS DECIMAL)<0.0001"
        all_results = cur.execute(query)
        groupby_values["ref"] = list()
        for result in all_results:
            sim_id = result[0]
            groupby_values["ref"].append(sim_id)
    else:
        groupby_values["ref"] = os.listdir(exp_id)
        if "results.db" in groupby_values["ref"]:
            groupby_values["ref"].remove("results.db")

    for sim_id in groupby_values["ref"]:
        report_path = os.path.join(str(exp_id), sim_id, "SpatialReport_" + chan + ".bin")
        data = sr.SpatialReport(report_path)
        for node_id in data.node_ids:
            chan_data = data[node_id].data
            if node_id not in node_chan_data:
                node_chan_data[node_id] = list()
                node_chan_means[node_id] = list()
            node_chan_data[node_id].append(chan_data)
            node_chan_means[node_id] = np.zeros(len(node_chan_data[node_id]))
    for node in node_chan_data.keys():
        node_chan_means[node] = np.mean(np.array(node_chan_data[node]), axis=0)

    return node_chan_means


def plot(exp_id, chan="Prevalence", tag=None):

    node_chan_means = collect(exp_id, chan, tag)

    for node in node_chan_means.keys():
        plt.plot(node_chan_means[node], label=f"node={node}")
    plt.xlabel("Timestep")
    plt.ylabel(chan)
    plt.title(f"Mean values of {chan} over time by node.")
    plt.legend()
    plt.show()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Spatial Report Plotting')
    parser.add_argument('-c', '--channel', action='store', default="Prevalence", help='channel(s) to display [Prevalence]')
    parser.add_argument('-e', '--experiment_id', action='store', default=None, help='experiment id to plot, data assumed to be local')
    parser.add_argument('-t', '--tag', action='store', default="", help='tag constraint')
    args = parser.parse_args()
    if not args.experiment_id:
        with open("COMPS_ID", "r") as fp:
            args.experiment_id = fp.read()
    if not args.channel:
        args.channel = 'Prevalence' # should not be necessary

    # check that folder with name experiment_id exists
    if not os.path.exists(str(args.experiment_id)):
        raise ValueError(f"Don't see folder for {args.experiment_id}.")

    plot(str(args.experiment_id), args.channel, tag=args.tag)
