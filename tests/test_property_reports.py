from functools import reduce
from pathlib import Path
import os
import tempfile

from emod_api.channelreports.utils import property_report_to_csv, read_json_file, get_report_channels, accumulate_channel_data, save_to_csv, plot_traces
from emod_api.channelreports.utils import __get_trace_name as utils__get_trace_name, __index_for as utils__index_for, __title_for as utils__title_for

import numpy as np

from tests import manifest


class TestPublicApi():
    """Test cases for public API."""

    prop_file = os.path.join(manifest.proprep_folder, "propertyReport.json")
    prop_file_short = os.path.join(manifest.proprep_folder, "propertyReportTruncated.json")

    def test_property_report_to_csv(self):

        handle, filename = tempfile.mkstemp()
        os.close(handle)
        csv_file = Path(filename)

        property_report_to_csv(
            source_file=self.prop_file,
            csv_file=csv_file,
            channels=["Infected", "New Infections"],
            groupby=["Age_Bin"])

        self.assertTrue(csv_file.exists())

        csv_file.unlink()

        return

    def test_property_report_to_csv_bad_channels(self):

        with self.assertRaises(ValueError):
            property_report_to_csv(
                source_file=self.prop_file,
                csv_file="this-is-an-error.csv",
                channels=["Zombified", "New Infections"],
                groupby=["Age_Bin"])

        return

    def test_property_report_to_csv_bad_groupby_ip(self):

        with self.assertRaises(ValueError):
            property_report_to_csv(
                source_file=self.prop_file,
                csv_file="this-is-an-error.csv",
                channels=["Infected", "New Infections"],
                groupby=["AgeAtDriversLicense"])

        return

    def test_read_json_file(self):

        property_report = read_json_file(filename=self.prop_file)

        # Test a selected few data points.
        self.assertEqual(property_report["Header"]["DateTime"], "Tue May 24 13:28:37 2022")
        self.assertTrue("Channels" in property_report)
        self.assertEqual(len(property_report["Channels"]), property_report["Header"]["Channels"])

        return

    def test_get_report_channels(self):

        property_report = read_json_file(filename=self.prop_file)
        channels = get_report_channels(property_report)

        self.assertEqual(len(channels), property_report["Header"]["Channels"])

        return

    def test_get_report_channels_bad(self):

        property_report = dict(fname="John", lname="Doe", age="42")

        with self.assertRaises(KeyError):
            _ = get_report_channels(property_report)

        return

    def test_accumulate_channel_data(self):

        json_data = read_json_file(filename=self.prop_file)
        channel_data = get_report_channels(json_data)

        # No roll-up IP(s), no normalization
        trace_values = accumulate_channel_data(channels=["Infected"], verbose=False, groupby=None, channel_data=channel_data)

        self.assertEqual(len(trace_values), 108)   # 4 age bins * 3 QoC * 3 QoC1 * 3 QoC2 = 108 traces

        # Two channels, no roll-up IP(s), no normalization
        trace_values = accumulate_channel_data(channels=["Infected", "New Infections"], verbose=False, groupby=None, channel_data=channel_data)

        self.assertEqual(len(trace_values), 216)   # 2 channels * 4 age bins * 3 QoC * 3 QoC1 * 3 QoC2 = 216 traces

        # Roll-up under Age_Bin, no normalization
        trace_values = accumulate_channel_data(channels=["Infected"], verbose=False, groupby=["Age_Bin"], channel_data=channel_data)

        self.assertEqual(len(trace_values), 4)   # 4 age bins

        # Roll-up under Age_Bin and QualityOfCare, no normalization
        trace_values = accumulate_channel_data(channels=["Infected"], verbose=False, groupby=["Age_Bin", "QualityOfCare"], channel_data=channel_data)

        self.assertEqual(len(trace_values), 12)   # 4 age bins * 3 QoC = 12

        # Roll-up _all_ IPs, no normalization
        trace_values = accumulate_channel_data(channels=["Infected"], verbose=False, groupby=[], channel_data=channel_data)

        self.assertEqual(len(trace_values), 1)    # 1 channel

        # Two channels, roll-up _all_ IPs, no normalization
        trace_values = accumulate_channel_data(channels=["Infected", "New Infections"], verbose=False, groupby=[], channel_data=channel_data)

        self.assertEqual(len(trace_values), 2)    # 2 channels

        # No roll-up IP(s), normalize on Statistical Population
        trace_values = accumulate_channel_data(channels=["Infected", "Statistical Population"], verbose=False, groupby=None, channel_data=channel_data)

        self.assertEqual(len([key for key in trace_values if key.startswith("Infected")]), 108)
        # reduce the various statistical population traces to a single vector
        stat_pop = reduce(lambda x, y: np.array(y, dtype=np.int32) + x, [values for (key, values) in trace_values.items() if key.startswith("Statistical Population")], 0)
        self.assertListEqual(list(stat_pop[:256]),
            [19160, 19120, 19180, 19240, 19280, 19280, 19280, 19320, 19340, 19380, 19380, 19400, 19480, 19500, 19520, 19580,
             19600, 19640, 19660, 19680, 19680, 19700, 19700, 19700, 19700, 19720, 19720, 19700, 19720, 19700, 19700, 19720,
             19780, 19800, 19840, 19860, 19860, 19880, 19900, 19920, 19920, 20020, 20040, 20000, 19980, 20000, 20100, 20160,
             20160, 20140, 20180, 20240, 20240, 20240, 20240, 20220, 20240, 20280, 20260, 20260, 20260, 20260, 20240, 20260,
             20260, 20280, 20300, 20360, 20380, 20380, 20420, 20420, 20460, 20440, 20500, 20500, 20520, 20540, 20520, 20560,
             20540, 20560, 20580, 20580, 20620, 20620, 20640, 20640, 20640, 20620, 20640, 20680, 20740, 20720, 20780, 20800,
             20840, 20880, 20880, 20880, 20940, 20940, 20940, 20980, 21000, 21000, 21040, 21020, 21060, 21080, 21060, 21100,
             21100, 21140, 21180, 21260, 21260, 21240, 21260, 21240, 21240, 21220, 21240, 21240, 21260, 21280, 21280, 21260,
             21280, 21360, 21360, 21380, 21460, 21460, 21480, 21500, 21520, 21520, 21560, 21600, 21620, 21620, 21660, 21660,
             21760, 21760, 21740, 21760, 21760, 21760, 21800, 21840, 21820, 21880, 21860, 21860, 21920, 21980, 21960, 21960,
             21980, 22000, 22000, 22000, 22000, 22020, 22040, 22100, 22100, 22160, 22160, 22160, 22180, 22180, 22200, 22320,
             22300, 22320, 22300, 22340, 22340, 22340, 22360, 22360, 22340, 22360, 22360, 22400, 22420, 22420, 22460, 22420,
             22420, 22420, 22500, 22520, 22540, 22580, 22600, 22640, 22660, 22660, 22720, 22780, 22800, 22800, 22820, 22880,
             22860, 22840, 22820, 22820, 22780, 22800, 22860, 22920, 22940, 22960, 22940, 22940, 23040, 23040, 23060, 23040,
             23040, 23060, 23080, 23140, 23200, 23260, 23260, 23360, 23360, 23400, 23440, 23480, 23460, 23480, 23500, 23560,
             23600, 23640, 23620, 23620, 23640, 23680, 23660, 23720, 23600, 23620, 23640, 23660, 23660, 23720, 23740, 23780])

        # Two channels, roll-up _all_ IPs, normalize on Statistical Population
        trace_values = accumulate_channel_data(channels=["Infected", "New Infections", "Statistical Population"], verbose=False, groupby=[], channel_data=channel_data)

        self.assertEqual(len(trace_values), 3)  # 3 channels
        self.assertListEqual(list(trace_values["Infected"][:256]),
            [   0,    0,    0,  240,  240,  240,  240,  260,  260,  260,  260,  280,  300,  340,  360,  380,
              460,  460,  480,  520,  540,  580,  620,  660,  700,  700,  700,  740,  780,  840,  900,  940,
             1000, 1000, 1000, 1020, 1060, 1060, 1100, 1120, 1140, 1200, 1240, 1260, 1280, 1300, 1320, 1320,
             1360, 1360, 1400, 1500, 1620, 1580, 1620, 1620, 1620, 1620, 1620, 1640, 1660, 1660, 1680, 1700,
             1740, 1760, 1760, 1760, 1800, 1880, 1900, 1940, 1960, 1960, 1960, 2000, 2040, 2040, 2000, 2040,
             2040, 2040, 2060, 2080, 2120, 2120, 2140, 2160, 2180, 2200, 2240, 2240, 2280, 2340, 2320, 2320,
             2320, 2300, 2320, 2320, 2340, 2340, 2360, 2340, 2380, 2380, 2380, 2400, 2420, 2420, 2420, 2420,
             2400, 2400, 2400, 2400, 2400, 2400, 2400, 2400, 2400, 2380, 2360, 2360, 2360, 2360, 2360, 2340,
             2340, 2340, 2340, 2340, 2340, 2340, 2340, 2340, 2340, 2340, 2340, 2360, 2360, 2360, 2380, 2380,
             2380, 2380, 2380, 2380, 2380, 2380, 2380, 2380, 2380, 2400, 2400, 2400, 2400, 2400, 2400, 2400,
             2460, 2500, 2500, 2520, 2540, 2520, 2520, 2500, 2500, 2500, 2500, 2500, 2500, 2500, 2500, 2500,
             2500, 2500, 2500, 2500, 2500, 2500, 2500, 2500, 2500, 2500, 2500, 2500, 2500, 2500, 2500, 2500,
             2500, 2500, 2500, 2500, 2500, 2500, 2500, 2500, 2500, 2500, 2500, 2500, 2500, 2500, 2500, 2500,
             2500, 2500, 2500, 2500, 2480, 2480, 2480, 2480, 2480, 2460, 2460, 2460, 2460, 2460, 2460, 2460,
             2460, 2460, 2460, 2460, 2460, 2460, 2460, 2460, 2460, 2460, 2460, 2460, 2460, 2460, 2460, 2460,
             2460, 2460, 2460, 2460, 2460, 2460, 2460, 2460, 2460, 2460, 2460, 2460, 2460, 2460, 2460, 2460])
        self.assertListEqual(list(trace_values["Statistical Population"][:256]),
            [19160, 19120, 19180, 19240, 19280, 19280, 19280, 19320, 19340, 19380, 19380, 19400, 19480, 19500, 19520, 19580,
             19600, 19640, 19660, 19680, 19680, 19700, 19700, 19700, 19700, 19720, 19720, 19700, 19720, 19700, 19700, 19720,
             19780, 19800, 19840, 19860, 19860, 19880, 19900, 19920, 19920, 20020, 20040, 20000, 19980, 20000, 20100, 20160,
             20160, 20140, 20180, 20240, 20240, 20240, 20240, 20220, 20240, 20280, 20260, 20260, 20260, 20260, 20240, 20260,
             20260, 20280, 20300, 20360, 20380, 20380, 20420, 20420, 20460, 20440, 20500, 20500, 20520, 20540, 20520, 20560,
             20540, 20560, 20580, 20580, 20620, 20620, 20640, 20640, 20640, 20620, 20640, 20680, 20740, 20720, 20780, 20800,
             20840, 20880, 20880, 20880, 20940, 20940, 20940, 20980, 21000, 21000, 21040, 21020, 21060, 21080, 21060, 21100,
             21100, 21140, 21180, 21260, 21260, 21240, 21260, 21240, 21240, 21220, 21240, 21240, 21260, 21280, 21280, 21260,
             21280, 21360, 21360, 21380, 21460, 21460, 21480, 21500, 21520, 21520, 21560, 21600, 21620, 21620, 21660, 21660,
             21760, 21760, 21740, 21760, 21760, 21760, 21800, 21840, 21820, 21880, 21860, 21860, 21920, 21980, 21960, 21960,
             21980, 22000, 22000, 22000, 22000, 22020, 22040, 22100, 22100, 22160, 22160, 22160, 22180, 22180, 22200, 22320,
             22300, 22320, 22300, 22340, 22340, 22340, 22360, 22360, 22340, 22360, 22360, 22400, 22420, 22420, 22460, 22420,
             22420, 22420, 22500, 22520, 22540, 22580, 22600, 22640, 22660, 22660, 22720, 22780, 22800, 22800, 22820, 22880,
             22860, 22840, 22820, 22820, 22780, 22800, 22860, 22920, 22940, 22960, 22940, 22940, 23040, 23040, 23060, 23040,
             23040, 23060, 23080, 23140, 23200, 23260, 23260, 23360, 23360, 23400, 23440, 23480, 23460, 23480, 23500, 23560,
             23600, 23640, 23620, 23620, 23640, 23680, 23660, 23720, 23600, 23620, 23640, 23660, 23660, 23720, 23740, 23780])

        return

    def test_save_to_csv(self):

        json_data = read_json_file(filename=self.prop_file_short)
        channel_data = get_report_channels(json_data)

        trace_values = accumulate_channel_data(
            channels=["Infected", "Statistical Population"],
            verbose=False,
            groupby=None,
            channel_data=channel_data
        )

        handle, filename = tempfile.mkstemp()
        os.close(handle)
        csv_file = Path(filename)

        save_to_csv(trace_values=trace_values, filename=csv_file)

        self.assertTrue(csv_file.exists())

        csv_file.unlink()

        return

    def test_plot_traces(self):

        json_data = read_json_file(filename=self.prop_file)
        channel_data = get_report_channels(json_data)

        stat_pop = "Statistical Population"

        channels = ["Infected", stat_pop]
        trace_values = accumulate_channel_data(
            channels=channels,
            verbose=False,
            groupby=["Age_Bin"],
            channel_data=channel_data
        )

        traces = {key: value for (key, value) in trace_values.items() if not key.startswith(stat_pop)}
        # reduce the various statistical population traces to a single vector
        norms = reduce(lambda x, y: np.array(y) + x, [value for (key, value) in trace_values.items() if key.startswith(stat_pop)], 0)

        figure = plot_traces(
            trace_values=traces,
            norm_values=norms,
            overlay=False,
            channels=channels,
            title="Property Report Visualization",
            legend=True)

        self.assertTrue(figure is not None)     # TODO - how to verify figure?

        return


class TestInternalApi():

    def test__get_trace_name(self):

        """
        Infected:Age_Bin:Age_Bin_Property_From_0_To_20,QualityOfCare:High,QualityOfCare1:High,QualityOfCare2:High
        """

        self.assertEqual(utils__get_trace_name("Infected", ["Age_Bin:Age_Bin_Property_From_0_To_20", "QualityOfCare:High", "QualityOfCare1:High", "QualityOfCare2:High"], None),
                         "Infected:Age_Bin:Age_Bin_Property_From_0_To_20,QualityOfCare:High,QualityOfCare1:High,QualityOfCare2:High")
        self.assertEqual(utils__get_trace_name("Infected", ["Age_Bin:Age_Bin_Property_From_0_To_20", "QualityOfCare:High", "QualityOfCare1:High", "QualityOfCare2:High"], ["Age_Bin"]),
                         "Infected:Age_Bin:Age_Bin_Property_From_0_To_20")
        self.assertEqual(utils__get_trace_name("Infected", ["Age_Bin:Age_Bin_Property_From_0_To_20", "QualityOfCare:High", "QualityOfCare1:High", "QualityOfCare2:High"], []), "Infected")

        return

    def test__index_for(self):

        trace_name = "New Infections"
        channels = ["Infected", "New Infections"]
        trace_keys = ["Infected", "New Infections"]

        # "Infected" is in plot #1, "New Infections" in plot #2
        self.assertEqual(utils__index_for(trace_name, channels, trace_keys, normalize=False, overlay=False), 2)

        # "Infected" is in plot #1, "Infected" normalized in plot #2, "New Infections" in plot #3, and "New Infections" normalized in plot #4
        self.assertEqual(utils__index_for(trace_name, channels, trace_keys, normalize=True, overlay=False), 3)

        return

    def test__title_for(self):

        trace_name = "Infected"
        channels = ["Infected", "New Infections"]
        self.assertEqual(utils__title_for(trace_name, channels, False), trace_name)

        trace_name = "New Infections"
        self.assertEqual(utils__title_for(trace_name, channels, False), trace_name)

        # TODO - test with overlay=True when overlay functionality is fixed

        return
