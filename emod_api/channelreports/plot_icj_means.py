import json
import numpy as np
import matplotlib.pyplot as plt
import os
import sqlite3


def collect(exp_id: str,
            chan: str = "Infected",
            tag: str = None,
            smoothing: bool = True) -> dict:
    """
    Collect all the time series data for a given channel for a given experiment from InsetChart.json
    files in local subdirectory that have been downoaded from COMPS, assuming following structure.

        exp_id/
           sim_id/
               InsetChart.json

    Args:
        exp_id: Experiment Id that has had data downloaded to current working diretory.
        chan:   Channel name
        tag:    key=value. Using results.db (sqlite3, from emodpy), limit results to just where key=value.
                If value is set to SWEEP, find all values for key and plot all values separately (but with mean/spread from other tags).

    Returns:
        Array of channel data for further processing.
    """

    chan_data = {}
    groupby_values = {}
    if tag:
        if len(tag.split("=")) == 1:
            raise ValueError("When passing tag, has to have key=value format.")

        groupby_key = tag.split("=")[0]
        groupby_value = tag.split("=")[1]
        db = os.path.join("latest_experiment", "results.db")
        con = sqlite3.connect(db)
        cur = con.cursor()
        if groupby_value == "SWEEP":
            query = f"SELECT sim_id, {groupby_key} FROM results"
            all_results = cur.execute(query)
            for result in all_results:
                sim_id = result[0]
                groupby_value = result[1]
                if groupby_value not in groupby_values:
                    groupby_values[groupby_value] = list()
                groupby_values[groupby_value].append(sim_id)
        else: # select only sim_id's where gb key == value
            query = f"SELECT sim_id FROM results where {groupby_key} = {groupby_value}"
            all_results = cur.execute(query)
            groupby_values["ref"] = list()
            for result in all_results:
                sim_id = result[0]
                groupby_values["ref"].append(sim_id)
    else:
        groupby_values["ref"] = os.listdir(exp_id)
        groupby_values["ref"].remove("results.db")

    def moving_average(x, w=7):
        return np.convolve(x, np.ones(w), 'valid') / w

    max_len = 0
    # poi = param of interest
    for value in groupby_values:
        simdirs = groupby_values[value]
        for sim in simdirs:
            thedir = os.path.join(exp_id, sim)

            if value not in chan_data:
                chan_data[value] = []
            if not os.path.exists(thedir + "/InsetChart.json"):
                continue
            with open(thedir + "/InsetChart.json") as fp:
                icj = json.loads(fp.read())
            if chan not in icj["Channels"]:
                raise ValueError(f"Can't find channel {chan} in file. Did find {icj['Channels'].keys()}.")
            new_data = np.asarray(icj["Channels"][chan]["Data"])
            if smoothing:
                new_data = moving_average(new_data)
            chan_data[value].append(new_data)
            if len(new_data) > max_len:
                max_len = len(new_data)
    if max_len == 0:
        raise ValueError(f"No InsetChart.json files with channel data for {chan} and experiment {exp_id}.")
    """
    If users run simulations that end when prevalence is zero, the length of the time series can vary
    We need to get them all the same to calc the mean.
    """
    data_for_plotting = {}
    for poi in chan_data:
        data_for_plotting[poi] = []
        for data in chan_data[poi]:
            if len(data) < max_len:
                data = np.pad(data, (0, max_len - len(data)))
            data_for_plotting[poi].append(data)

    return data_for_plotting


def display(chan_data, save=False, chan_name="Infected", exp_id=None):
    """
    Plot mean and std dev of the array/list of time series-es in chan_data.
    """
    mean_chan_data = None
    spread_chan_data = None
    fig, ax = plt.subplots(1)
    if exp_id:
        plt.title(exp_id, loc="center")
    for poi_chan_data in sorted(chan_data):
        prev_list = chan_data[poi_chan_data]
        if len(prev_list) == 0:
            raise ValueError("Input channel data array seems to have no data.")
        mean_chan_data = np.mean(np.array(prev_list), axis=0)
        if len(chan_data) == 1 and save:
            ref_json = {"Channels": {"Channel": {"Data": []}}}
            ref_json["Channels"]["Channel"]["Data"] = list(mean_chan_data)
            with open("mean_ref.json", "w") as fp:
                json.dump(ref_json, fp, indent=4)
        spread_chan_data = np.std(np.array(prev_list), axis=0)

        t = np.arange(len(mean_chan_data))
        ax.plot(t, mean_chan_data, label=poi_chan_data)
        plt.xlim(0, len(mean_chan_data))
        ax.fill_between(t, mean_chan_data + spread_chan_data, mean_chan_data - spread_chan_data, facecolor='yellow', alpha=0.5)
    ax.set_xlabel("Simulation Time")
    ax.set_ylabel(chan_name)
    plt.legend()
    plt.show()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Mean 'InsetChart' Report Plotting")
    parser.add_argument('-c', '--channel', action='store', default="Infected", help='channel(s) to display [Infected]')
    parser.add_argument('-e', '--experiment_id', action='store', default=None, help='experiment id to plot, data assumed to be local')
    parser.add_argument('-t', '--tag', action='store', default=None, help='key=value tag constraint')
    args = parser.parse_args()
    if not args.experiment_id:
        with open("COMPS_ID") as fp:
            args.experiment_id = fp.read()

    # check that folder with name experiment_id exists
    if not os.path.exists(str(args.experiment_id)):
        raise ValueError(f"Don't see folder for {args.experiment_id}.")

    chan_data = collect(args.experiment_id, args.channel, args.tag)
    display(chan_data, False, args.channel, args.experiment_id)
