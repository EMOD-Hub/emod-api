#!/usr/bin/python

import argparse
import os
import matplotlib

if os.environ.get("DISPLAY", "") == "":
    print("no display found. Using non-interactive Agg backend")
    matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import json
import sys
import pylab
from math import sqrt, ceil


def plotOneFromDisk():
    with open(sys.argv[1]) as ref_sim:
        ref_data = json.loads(ref_sim.read())

    idx = 0
    for chan_title in sorted(ref_data["Channels"]):
        try:
            subplot = plt.subplot(4, 5, idx)
            subplot.plot(ref_data["Channels"][chan_title]["Data"], "r-")
            plt.title(chan_title)
        except Exception as ex:
            print(f"{ex}, idx = {idx}")
        if idx == 4 * 5:
            break

    plt.show()


def plotCompareFromDisk(
    reference, comparison, label="", savefig=True, headless=False, closefig=True
):
    with open(reference) as ref_sim:
        ref_data = json.loads(ref_sim.read())

    with open(comparison) as test_sim:
        test_data = json.loads(test_sim.read())

    num_chans = ref_data["Header"]["Channels"]

    plt.figure(figsize=(20, 15))

    square_root = ceil(sqrt(num_chans))

    n_figures_x = square_root
    n_figures_y = ceil(
        float(num_chans) / float(square_root)
    )

    if label == "unspecified":
        label = sys.argv[1]

    ref_tstep = 1
    if "Simulation_Timestep" in ref_data["Header"]:
        ref_tstep = ref_data["Header"]["Simulation_Timestep"]

    tst_tstep = 1
    if "Simulation_Timestep" in test_data["Header"]:
        tst_tstep = test_data["Header"]["Simulation_Timestep"]

    idx = 1
    for chan_title in sorted(ref_data["Channels"]):
        if chan_title not in test_data["Channels"]:
            print("title on in test. ignore.")
            continue

        try:
            subplot = plt.subplot(n_figures_x, n_figures_y, idx)
            ref_x_len = len(ref_data["Channels"][chan_title]["Data"])
            tst_x_len = len(test_data["Channels"][chan_title]["Data"])
            ref_tstep = 1
            tst_tstep = 1
            if "Simulation_Timestep" in ref_data["Header"].keys():
                ref_tstep = ref_data["Header"]["Simulation_Timestep"]
                if "Simulation_Timestep" in test_data["Header"].keys():
                    tst_tstep = test_data["Header"]["Simulation_Timestep"]
            ref_x_data = np.arange(0, ref_x_len * ref_tstep, ref_tstep)
            tst_x_data = np.arange(0, tst_x_len * tst_tstep, tst_tstep)
            subplot.plot(
                ref_x_data,
                ref_data["Channels"][chan_title]["Data"],
                "r-",
                tst_x_data,
                test_data["Channels"][chan_title]["Data"],
                "b-",
            )
            plt.setp(subplot.get_xticklabels(), fontsize="5")
            plt.title(chan_title, fontsize="6")
            idx += 1
        except Exception as ex:
            print("Exception: " + str(ex))

    if reference == comparison:
        plt.suptitle(label + " " + reference)
    else:
        plt.suptitle(
            label + " reference(red)=" + reference + "  \n test(blue)=" + comparison
        )
    plt.subplots_adjust(bottom=0.05)

    if savefig:
        path_dir = "."  # dumb but might want to change
        plotname = "InsetChart"
        pylab.savefig(
            os.path.join(path_dir, plotname) + ".png",
            bbox_inches="tight",
            orientation="landscape",
        )  # , dpi=200 )
    if not headless:
        plt.show()
    if closefig:
        plt.close()


def plotBunch(all_data, plot_name, baseline_data=None, closefig=True):
    num_chans = all_data[0]["Header"]["Channels"]
    plt.suptitle(plot_name)
    plt.figure(figsize=(20, 15))
    square_root = 4
    if num_chans > 30:
        square_root = 6
    elif num_chans > 16:
        square_root = 5
    plots = []
    labels = []

    idx = 0
    for chan_title in sorted(all_data[0]["Channels"]):
        idx_x = idx % square_root
        idx_y = int(idx / square_root)

        try:
            subplot = plt.subplot2grid((square_root, square_root), (idx_y, idx_x))
            colors = ["b", "g", "c", "m", "y", "k"]

            if baseline_data is not None:
                tstep = 1
                if "Simulation_Timestep" in baseline_data["Header"]:
                    tstep = baseline_data["Header"]["Simulation_Timestep"]
                x_len = len(baseline_data["Channels"][chan_title]["Data"])
                x_data = np.arange(0, x_len * tstep, tstep)
                plots.append(
                    subplot.plot(
                        x_data,
                        baseline_data["Channels"][chan_title]["Data"],
                        "r-",
                        linewidth=2,
                    )
                )

            for sim_idx in range(0, len(all_data)):
                labels.append(str(sim_idx))

                x_len = len(all_data[sim_idx]["Channels"][chan_title]["Data"])

                tstep = 1
                if "Simulation_Timestep" in all_data[sim_idx]["Header"]:
                    tstep = all_data[sim_idx]["Header"]["Simulation_Timestep"]

                x_data = np.arange(0, x_len * tstep, tstep)

                plots.append(
                    subplot.plot(
                        x_data,
                        all_data[sim_idx]["Channels"][chan_title]["Data"],
                        colors[sim_idx % len(colors)] + "-",
                    )
                )

            plt.title(chan_title)
        except Exception as ex:
            print(str(ex))
        if idx == (square_root * square_root) - 1:
            break

        idx += 1

    plt.subplots_adjust(
        left=0.04, right=0.99, bottom=0.02, top=0.9, wspace=0.3, hspace=0.3
    )
    pylab.savefig(
        plot_name.replace(" ", "_") + ".png",
        bbox_inches="tight",
        orientation="landscape",
    )
    plt.show()
    if closefig:
        plt.close()


def main(reference, comparison, label, savefig, headless):
    if headless:
        savefig = True
    plotCompareFromDisk(reference, comparison, label, savefig, headless, closefig=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("reference", help="Reference chart(s) filename")
    parser.add_argument(
        "comparison", default=None, nargs="?", help="Comparison chart(s) filename"
    )
    parser.add_argument("label", default="", nargs="?", help="Plot label")
    parser.add_argument(
        "--savefig",
        action="store_true",
        default=False,
        help="Write plot image to disk.",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        default=False,
        help="Do not display; just save to disk.",
    )
    args = parser.parse_args()

    main(
        args.reference,
        args.comparison if args.comparison else args.reference,
        args.label,
        args.savefig,
        args.headless,
    )
