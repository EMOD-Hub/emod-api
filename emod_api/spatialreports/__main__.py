#!/usr/bin/env python3

import os
from argparse import ArgumentParser
from emod_api.spatialreports.spatial import SpatialReport

MATPLOTLIB = True
try:
    import matplotlib
    matplotlib.use('TkAgg')
    import matplotlib.pyplot as plt
except ModuleNotFoundError:
    print("This example requires the matplotlib package.")
    MATPLOTLIB = False

SCRIPT_PATH = os.path.realpath(__file__)
WORKING_DIRECTORY = os.path.dirname(SCRIPT_PATH)


def main(filename: str):

    report = SpatialReport(filename)

    plt.xkcd()

    y_axis_guess = os.path.basename(filename).strip("SpatialReport_").strip(".bin")
    # Show node-wise time series data
    for node_id in report.node_ids:
        plt.plot(report[node_id].data, label=f"Node {node_id}")
    plt.title(f"{y_axis_guess} for Nodes")
    plt.legend()
    plt.xlabel("Time Step")
    plt.ylabel(f"{y_axis_guess}")
    plt.show()

    return


def dump_source():

    with open(SCRIPT_PATH, "r") as file:
        print(file.read())

    return


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument(
        "-f", "--filename", default=None, help="spatial report filename"
    )
    parser.add_argument(
        "-g",
        "--get",
        default=False,
        action="store_true",
        help="Write source code for this example to stdout.",
    )

    args = parser.parse_args()

    if args.get:
        dump_source()
    elif args.filename and MATPLOTLIB:
        main(args.filename)
    else:
        parser.print_help()
