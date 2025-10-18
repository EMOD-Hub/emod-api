"""
Helper functions, primarily for property reports, which are channel reports.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Union

import matplotlib.pyplot as plt
import numpy as np

from emod_api.channelreports.channels import ChannelReport

__all__ = [
    "property_report_to_csv",
    "read_json_file",
    "get_report_channels",
    "_validate_property_report_channels",
    "_validate_property_report_ips",
    "accumulate_channel_data",
    "__get_trace_name",
    "save_to_csv",
    "plot_traces",
    "__index_for",
    "__title_for"]


def property_report_to_csv(source_file: Union[str, Path],
                           csv_file: Union[str, Path],
                           channels: Optional[List[str]] = None,
                           groupby: Optional[List[str]] = None,
                           transpose: bool = False) -> None:

    """
    Write a property report to a CSV formatted file.

    Optionally selected a subset of available channels.
    Optionally "rolling-up" IP:value sub-channels into a "parent" IP.

    Args:
        source_file: filename of property report
        channels:    list of channels to output, None results in writing _all_ channels to output
        groupby:     list of IPs into which to aggregate remaining IPs, None indicates no grouping, [] indicates _all_ aggregated
        csv_file:    filename of CSV formatted result
        transpose:   write channels as columns rather than rows
    """

    json_data = read_json_file(Path(source_file))
    channel_data = get_report_channels(json_data)

    if channels is None:
        channels = sorted({key.split(":")[0] for key in channel_data})
    elif isinstance(channels, str):
        channels = [channels]

    if isinstance(groupby, str):
        groupby = [groupby]

    _validate_property_report_channels(channels, channel_data)
    _validate_property_report_ips(groupby, channel_data)

    trace_values = accumulate_channel_data(channels, False, groupby, channel_data)

    save_to_csv(trace_values, csv_file, transpose)

    return


def read_json_file(filename: Union[str, Path]) -> Dict:

    with Path(filename).open("r", encoding="utf-8") as file:
        json_data = json.load(file)

    return json_data


def get_report_channels(json_data: Dict) -> Dict:

    try:
        channel_data = json_data['Channels']
    except KeyError as exc:
        raise KeyError("Didn't find 'Channels' in JSON data.") from exc

    return channel_data


def _validate_property_report_channels(channels, channel_data) -> None:

    if channels:
        keys = set(map(lambda name: name.split(":", 1)[0], channel_data))
        not_found = [name for name in channels if name not in keys]
        if not_found:
            print("Valid channel names:")
            print("\n".join(keys))
            raise ValueError(f"Specified channel(s) - {not_found} - is/are not valid channel names.")

    return


def _validate_property_report_ips(groupby, channel_data) -> None:

    if groupby:
        first = next(iter(channel_data))
        ip_string = first.split(":", 1)[1]
        ips = [kvp.split(":")[0] for kvp in ip_string.split(",")]
        not_found = [ip for ip in groupby if ip not in ips]
        if not_found:
            print("Valid IPs:")
            print("\n".join(ips))
            raise ValueError(f"Specified groupby IP(s) - {not_found} - is/are not valid IP names.")

    return


def accumulate_channel_data(channels: List[str], verbose: bool, groupby: List[str], channel_data: Dict) -> Dict[str, np.ndarray]:

    """
    Extract selected channel(s) from property report data.

    Aggregate on groupby IP(s), if provided, otherwise on channel per unique
    IP:value pair (e.g., "QualityOfCare:High"), per main channel (e.g., "Infected").

    Args:
        channels:       names of channels to plot
        verbose:        output some "debugging"/progress information if true
        groupby:        IP(s) under which to aggregate other IP:value pairs
        channel_data:   data for channels keyed on channel name

    Returns:
        tuple of dictionary of aggregated data, keyed on channel name, and of Numpy array of normalization values
    """

    trace_values = {}
    pool_keys = sorted(channel_data)

    name_ip_pairs = map(lambda key: tuple(key.split(":", 1)), pool_keys)
    name_ip_pairs_to_process = filter(lambda p: p[0] in channels, name_ip_pairs)
    for (channel_title, key_value_pairs) in name_ip_pairs_to_process:

        if verbose:
            print(f"Processing channel '{channel_title}:{key_value_pairs}'")

        key_value_pairs = key_value_pairs.split(',')
        trace_name = __get_trace_name(channel_title, key_value_pairs, groupby)
        trace_data = np.array(channel_data[f"{channel_title}:{','.join(key_value_pairs)}"]['Data'], dtype=np.float32)

        if trace_name not in trace_values:
            if verbose:
                print(f"New trace: '{trace_name}'")
            trace_values[trace_name] = trace_data
        else:
            if verbose:
                print(f"Add to trace: '{trace_name}'")
            trace_values[trace_name] += trace_data

    return trace_values


def __get_trace_name(channel_title: str, key_value_pairs: List[str], groupby: List[str]) -> str:

    """
    Return "canonical" trace name for a given channel, IP:value list, and groupby list.

    Since we may be aggregating by IP values, trace name may not equal any particular channel name.

    Example:
        title = "Infected"
        key_value_pairs = ["Age_Bin:Age_Bin_Property_From_0_To_20","QualityOfCare:High","QualityOfCare1:High","QualityOfCare2:High"]

        groupby = None
        return "Infected:Age_Bin:Age_Bin_Property_From_0_To_20,QualityOfCare:High,QualityOfCare1:High,QualityOfCare2:High"

        groupby = ["Age_Bin"]
        return = "Infected:Age_Bin:Age_Bin_Property_From_0_To_20"

        groupby = ["Age_Bin", "QualityOfCare"]
        return = "Infected:Age_Bin:Age_Bin_Property_From_0_To_20,QualityOfCare:High"

        groupby = []
        return = "Infected"
    """

    # trace name will have channel title and any property:value pairs
    # which aren't being grouped

    trace_name = channel_title + ':'

    if groupby is None:
        trace_name = f"{channel_title}:{','.join(key_value_pairs)}"
    else:
        if len(groupby) > 0:
            kvps = filter(lambda pair: pair.split(":")[0] in groupby, key_value_pairs)
            trace_name = f"{channel_title}:{','.join(kvps)}"
        else:
            trace_name = channel_title

    return trace_name


def save_to_csv(trace_values: Dict[str, np.ndarray],
                filename: Union[str, Path],
                transpose: bool = False) -> None:

    """
    Save property report to CSV. Uses underlying ChannelReport.to_csv() function.

    Args:
        trace_values: full set of available channels, keyed on channel name
        filename:     destination file for CSV data
        transpose:    write channels as columns rather than rows
    """

    report = ChannelReport()

    for channel, data in trace_values.items():
        report.channels[channel] = data

    report.to_csv(Path(filename), transpose=transpose)  # by default, use _all_ the channels we just added

    return


def plot_traces(trace_values: Dict[str, np.ndarray],
                norm_values: Optional[Union[int, np.ndarray]],
                overlay: bool,
                channels: List[str],
                title: str,
                legend: bool) -> plt.Figure:

    """
    Plot trace data. One subplot per channel unless overlaying all variations of rolled-up IP(s) is requested.

    A trace (like old-time pen and ink EKG) may represent the aggregation of
    several IP values so trace may not equal any particular channel data.

    Args:
        trace_values: channel data, keyed on channel name
        norm_values:  normalization data for channels
        overlay:      whether or not to overlay all variations of a given channel on one subplot
        channels:     selection of channel names to plot
        title:        plot title
        legend:       whether or not to include a legend on plots

    Returns:
        plt.Figure
    """

    if len(trace_values) == 0:
        print("Didn't find requested channel(s) in property report.")
        return

    if not overlay:
        plot_count = len(trace_values)
    else:
        plot_count = len(channels)

    normalize = norm_values is not None
    if normalize:
        plot_count *= 2

    figure = plt.figure(title, figsize=(16, 9), dpi=300)
    trace_keys = sorted(trace_values)

    # plotting here
    for trace_name in trace_keys:
        plot_index = __index_for(trace_name, channels, trace_keys, normalize, overlay)
        plt.subplot(plot_count, 1, plot_index)
        plt.plot(trace_values[trace_name], label=trace_name)
        if normalize:
            plt.subplot(plot_count, 1, plot_index + 1)
            plt.ylim((0.0, 1.0))    # yes, this takes a tuple
            plt.plot(trace_values[trace_name] / norm_values, label=trace_name)

    # make it pretty
    _ = plt.subplot(plot_count, 1, 1)
    for trace_name in trace_keys:
        plot_index = __index_for(trace_name, channels, trace_keys, normalize, overlay)
        plot_title = __title_for(trace_name, channels, overlay)
        plt.subplot(plot_count, 1, plot_index)
        plt.title(plot_title)
        if legend:
            plt.legend()
        if normalize:
            plt.subplot(plot_count, 1, plot_index + 1)
            plt.title(f"{plot_title} normalized by 'Statistical Population'")
            if legend:
                plt.legend()

    plt.tight_layout()

    return figure


def __index_for(trace_name: str, channels: List[str], trace_keys: List[str], normalize: bool, overlay: bool) -> int:

    if overlay:
        # all pools of the same channel overlaid
        index = 0
        for channel in channels:
            if channel in trace_name:
                break
            index += 1
    else:
        # each trace separate
        index = trace_keys.index(trace_name)

    # if we're normalizing, there's a normalized trace per regular trace
    if normalize:
        index *= 2

    # matplotlib is 1-based (like MATLAB)
    return index + 1


def __title_for(trace_name: str, channels: List[str], overlay: bool):

    # use channel name
    if overlay:
        for channel in channels:
            if channel in trace_name:
                title = channel
                break
    else:
        title = trace_name

    return title
