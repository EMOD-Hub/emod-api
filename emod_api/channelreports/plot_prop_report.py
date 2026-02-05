#! /usr/bin/env python3

"""Command line utility for plotting property reports."""

import argparse
from functools import reduce
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from emod_api.channelreports.utils import read_json_file, get_report_channels, accumulate_channel_data, save_to_csv, plot_traces
from emod_api.channelreports.utils import _validate_property_report_channels, _validate_property_report_ips


def main(args: argparse.Namespace):

    """
    Plot specified property report with the given options.
    """

    json_data = read_json_file(args.filename)
    channel_data = get_report_channels(json_data)
    channel_keys = sorted(channel_data)

    if args.verbose:
        print("Channels:Pools-")
        print(json.dumps(channel_keys, indent=4))

    if args.list:
        list_channels_and_ips(channel_keys)
        return

    _validate_property_report_channels(args.channels, channel_data)
    _validate_property_report_ips(args.groupby, channel_data)

    if args.normalize and ("Statistical Population" not in args.channels):
        args.channels.append("Statistical Population")

    trace_values = accumulate_channel_data(args.channels, args.verbose, args.groupby, channel_data)

    if args.csv is None:
        call_plot_traces(args, trace_values)
    else:
        save_to_csv(trace_values, args.csv, args.transpose)

    return


def list_channels_and_ips(channel_keys: list[str]) -> None:

    """
    List the channels and properties found in a property report from the
    CHANNEL:IP:value,...,IP:value keys of the channel dictionary.
    """

    # keys look like "CHANNEL:IP:value,...,IP:value"
    channels = sorted(set([key.split(":", 1)[0] for key in channel_keys]))

    print("\nChannels:")
    for channel in channels:
        print(f"\t{channel}")

    # Each channel _should_ have the same set of IPs, but we'll check them all
    csvkvps = [key.split(":", 1)[1] for key in channel_keys]            # For each channel get a comma separated list of IP:value pairs (see format above)
    kvplists = [csv.split(",") for csv in csvkvps]                      # For each CSV convert to actual list by splitting on ","
    ips = [map(lambda t: t.split(":")[0], kvps) for kvps in kvplists]   # Convert each IP:value entry to just IP
    properties = sorted(reduce(lambda s, e: s.union(e), ips, set()))    # Add all IPs to an initially empty set

    print("\nIPs:")
    for prop in properties:
        print(f"\t{prop}")

    print()

    return


def call_plot_traces(args: argparse.Namespace,
                     trace_values: dict[str, np.ndarray]) -> None:

    """
    Call the internal `plot_traces` function and, optionally, save the results to disk.
    """

    if args.verbose:
        print(sorted(trace_values))

    if args.normalize:
        stat_pop = "Statistical Population"
        traces = {key: value for (key, value) in trace_values.items() if not key.startswith(stat_pop)}
        # reduce the various statistical population traces to a single vector
        norms = reduce(lambda x, y: np.array(y) + x, [value for (key, value) in trace_values.items() if key.startswith(stat_pop)], 0)
    else:
        traces = trace_values
        norms = None

    figure = plot_traces(traces, norms, args.overlay, args.channels, args.filename, args.legend)

    if args.saveFigure:
        print("Saving figure 'propertyReport.png'...")
        figure.savefig('propertyReport.png')

    plt.show()

    return


def prop_report_json_to_csv(output_path: str,
                            channel_name: str = "Infected",
                            groupby: str = "Geographic"):
    """
    Converts selected channel of PropertyReportXXX.json into a CSV file, rolled up into a single property.

    Args:
        output_path: Subdirectory in which to find a file called PropertyReportXXX.json.
            XXX can be blank or a disease named like 'TB'.
        channel_name: Name of the channel to process from the property report.
            Defaults to "Infected".
        groupby: Property to group by. Defaults to "Geographic".

    Returns:

    Raises:
        ValueError: If no PropertyReportXXX.json file is found in the directory.
    """

    def find_file_starting_with(directory, prefix):
        path = Path(directory)
        for file in path.iterdir():
            if file.name.startswith(prefix) and file.is_file() and file.name.endswith("json"):
                return str(file)
        return None

    prop_report_path = find_file_starting_with(output_path, "PropertyReport")
    if not prop_report_path:
        raise ValueError(f"No json file starting with 'PropertyReport' found in '{output_path}'.")

    # This class probably exists somewhere else. Maybe we can move it to a common utils.py file or getit from elsewhere.
    class DynamicObject:
        def __init__(self):
            object.__setattr__(self, 'members', {})

        def __setattr__(self, name, value):
            self.members[name] = value

        def __getattr__(self, name):
            return self.members.get(name)

    faux_args = DynamicObject()
    faux_args.filename = prop_report_path
    csv_out_name = "prop_report_" + channel_name.replace(' ', '_').lower() + ".csv"
    faux_args.csv = csv_out_name
    faux_args.channels = [channel_name]
    faux_args.channels.append("Statistical Population")
    faux_args.normalize = True
    faux_args.groupby = [groupby]
    main(faux_args)


def process_cmd_line() -> argparse.Namespace:

    """
    Put command line processing here rather than in `if 'name' == '__main__'`.
    """

    parser = argparse.ArgumentParser(description='Property Report Plotting')
    parser.add_argument('filename', nargs='?', default='PropertyReport.json', help='property report filename [PropertyReport.json]')
    parser.add_argument('-c', '--channel', action='append', help='channel(s) to display [Infected]', metavar='channelName', dest='channels')
    parser.add_argument('-g', '--groupby', action='append', help="IP(s) under which to aggregate other IP keys and values")
    parser.add_argument('-n', '--normalize', help='plot channel(s) normalized by statistical population', action='store_true')
    parser.add_argument('-o', '--overlay', help='overlay pools of the same channel', action='store_true')
    parser.add_argument('-s', '--save', help="save figure to file 'propertyReport.png'", action='store_true', dest='saveFigure')
    parser.add_argument('-v', '--verbose', action="store_true")
    parser.add_argument('--no-legend', action="store_false", dest="legend")     # Note args.legend default to True, passing --no-legend sets args.legend to False
    parser.add_argument('-l', '--list', action="store_true", help="List channels and IP keys found in the report. No plotting is performed with this option.")
    parser.add_argument("--csv", type=Path, default=None, help="Write data for selected channel(s) to given file.")
    parser.add_argument("-t", "--transpose", action="store_true", help="write channels as columns rather than rows (only in effect with '--csv' option)")

    args = parser.parse_args()

    if not args.channels:
        args.channels = ['Infected']

    if args.groupby is not None and len(args.groupby) == 1 and args.groupby[0].lower() == "all":
        args.groupby = []

    if not args.list:
        print(f"Filename:              '{args.filename}'")
        print(f"Channel(s):            {args.channels}")
        print(f"Groupby:               {args.groupby}")
        print(f"Normalize:             {args.normalize}")
        print(f"Overlay:               {args.overlay}")
        print(f"Save:                  {args.saveFigure}")
        if args.csv:
            print(f"CSV filename:          '{args.csv}'")
        print(f"Transpose CSV:         {args.transpose}")

    return args


if __name__ == '__main__':

    main(process_cmd_line())
