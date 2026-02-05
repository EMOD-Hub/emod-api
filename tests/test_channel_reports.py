import os
from pathlib import Path
import tempfile
from emod_api.channelreports.channels import ChannelReport, Header, Channel
from emod_api.channelreports.icj_to_csv import inset_chart_json_to_csv_dataframe_pd
from emod_api.channelreports.plot_prop_report import prop_report_json_to_csv
from datetime import datetime
from random import random, randint
import pandas as pd
import json
from tests import manifest
import pytest


class TestHeader():

    _NUM_CHANNELS = 42
    _DTK_VERSION = "master (223ec6f9)"
    _TIME_STAMP = datetime(2019, 12, 4, hour=3, minute=14, second=15)
    _REPORT_TYPE = "ChannelReport"
    _REPORT_VERSION = "4.2"
    _TIME_STEP = 30
    _START_TIME = 3650
    _TIME_STEPS = 365

    def test_empty_ctor(self):

        header = Header()
        self.assertEqual(header.num_channels, 0)
        self.assertEqual(header.dtk_version, "unknown-branch (unknown)")
        self.assertEqual(header.time_stamp, f"{datetime.now():%a %B %d %Y %H:%M:%S}")
        self.assertEqual(header.report_type, "InsetChart")
        self.assertEqual(header.report_version, "0.0")
        self.assertEqual(header.step_size, 1)
        self.assertEqual(header.start_time, 0)
        self.assertEqual(header.num_time_steps, 0)

        return

    def test_ctor_with_args(self):

        header = Header(
            **{
                "Channels": TestHeader._NUM_CHANNELS,
                "DTK_Version": TestHeader._DTK_VERSION,
                "DateTime": f"{TestHeader._TIME_STAMP:%a %B %d %Y %H:%M:%S}",
                "Report_Type": TestHeader._REPORT_TYPE,
                "Report_Version": TestHeader._REPORT_VERSION,
                "Simulation_Timestep": TestHeader._TIME_STEP,
                "Start_Time": TestHeader._START_TIME,
                "Timesteps": TestHeader._TIME_STEPS,
            }
        )

        self.assertEqual(header.num_channels, TestHeader._NUM_CHANNELS)
        self.assertEqual(header.dtk_version, TestHeader._DTK_VERSION)
        self.assertEqual(
            header.time_stamp, f"{TestHeader._TIME_STAMP:%a %B %d %Y %H:%M:%S}"
        )
        self.assertEqual(header.report_type, TestHeader._REPORT_TYPE)
        self.assertEqual(header.report_version, TestHeader._REPORT_VERSION)
        self.assertEqual(header.step_size, TestHeader._TIME_STEP)
        self.assertEqual(header.start_time, TestHeader._START_TIME)
        self.assertEqual(header.num_time_steps, TestHeader._TIME_STEPS)

        return

    def test_setters(self):

        header = Header()

        header.num_channels = TestHeader._NUM_CHANNELS
        header.dtk_version = TestHeader._DTK_VERSION
        header.time_stamp = TestHeader._TIME_STAMP
        header.report_type = TestHeader._REPORT_TYPE
        header.report_version = TestHeader._REPORT_VERSION
        header.step_size = TestHeader._TIME_STEP
        header.start_time = TestHeader._START_TIME
        header.num_time_steps = TestHeader._TIME_STEPS

        self.assertEqual(header.num_channels, TestHeader._NUM_CHANNELS)
        self.assertEqual(header.dtk_version, TestHeader._DTK_VERSION)
        self.assertEqual(
            header.time_stamp, f"{TestHeader._TIME_STAMP:%a %B %d %Y %H:%M:%S}"
        )
        self.assertEqual(header.report_type, TestHeader._REPORT_TYPE)
        self.assertEqual(header.report_version, TestHeader._REPORT_VERSION)
        self.assertEqual(header.step_size, TestHeader._TIME_STEP)
        self.assertEqual(header.start_time, TestHeader._START_TIME)
        self.assertEqual(header.num_time_steps, TestHeader._TIME_STEPS)

        return

    def test_as_dictionary(self):

        source = {
            "Channels": TestHeader._NUM_CHANNELS,
            "DTK_Version": TestHeader._DTK_VERSION,
            "DateTime": TestHeader._TIME_STAMP,
            "Report_Type": TestHeader._REPORT_TYPE,
            "Report_Version": TestHeader._REPORT_VERSION,
            "Simulation_Timestep": TestHeader._TIME_STEP,
            "Start_Time": TestHeader._START_TIME,
            "Timesteps": TestHeader._TIME_STEPS,
            "Signature": "This message was brought to you by the numbers 0 and 1.",
        }

        header = Header(**source)

        self.assertDictEqual(header.as_dictionary(), source)

        return


class TestChannel():

    _TITLE = "Gas Mileage"
    _UNITS = "picometers per tun"
    _DATA = [1, 1, 2, 3, 5, 8]

    def test_ctor(self):

        channel = Channel(TestChannel._TITLE, TestChannel._UNITS, TestChannel._DATA)

        self.assertEqual(channel.title, TestChannel._TITLE)
        self.assertEqual(channel.units, TestChannel._UNITS)
        self.assertListEqual(channel.data, TestChannel._DATA)

        return

    def test_setters(self):

        channel = Channel(None, None, [_ for _ in range(6)])

        channel.title = TestChannel._TITLE
        channel.units = TestChannel._UNITS

        for index in range(6):
            channel.data[index] = TestChannel._DATA[index]

        self.assertEqual(channel.title, TestChannel._TITLE)
        self.assertEqual(channel.units, TestChannel._UNITS)
        self.assertListEqual(channel.data, TestChannel._DATA)

        return

    def test_as_dictionary(self):

        channel = Channel(TestChannel._TITLE, TestChannel._UNITS, TestChannel._DATA)

        self.assertDictEqual(
            channel.as_dictionary(),
            {
                TestChannel._TITLE: {
                    "Units": TestChannel._UNITS,
                    "Data": TestChannel._DATA,
                }
            },
        )

        return


class TestChannels():
    def test_fromFile(self):

        chart = ChannelReport(os.path.join(manifest.reports_folder, "InsetChart.json"))
        self.assertEqual(chart.header.time_stamp, "Wed November 27 2019 14:49:15")
        self.assertEqual(
            chart.header.dtk_version, "0 unknown-branch (unknown) May 31 2019 15:04:44"
        )
        self.assertEqual(chart.header.report_type, "InsetChart")
        self.assertEqual(chart.header.report_version, "3.2")
        self.assertEqual(chart.header.start_time, 0)
        self.assertEqual(chart.header.step_size, 1)
        self.assertEqual(chart.header.num_time_steps, 365)
        self.assertEqual(chart.header.num_channels, 16)

        self.assertEqual(len(chart.channels), 16)
        self.assertEqual(chart.channels["Births"].units, "Births")
        self.assertAlmostEqual(
            chart.channels["Infected"].data[10], 0.000001222560626957, 16
        )

        self.assertSetEqual(
            set(chart.channel_names),
            {
                "Births",
                "Campaign Cost",
                "Daily (Human) Infection Rate",
                "Disease Deaths",
                "Exposed Population",
                "Human Infectious Reservoir",
                "Infected",
                "Infectious Population",
                "Log Prevalence",
                "New Infections",
                "Newly Symptomatic",
                "Recovered Population",
                "Statistical Population",
                "Susceptible Population",
                "Symptomatic Population",
                "Waning Population",
            },
        )

        return

    def test_writeFile(self):
        timestamp = datetime.now()
        NUMCHANNELS = 2
        VERSION = "abcdef0 test-branch (clorton) Nov 26 2019 22:17:00"
        TIMESTEPS = 730
        TIMESTAMP = f"{timestamp:%a %B %d %Y %H:%M:%S}"
        REPORTTYPE = "TestCharts"
        REPORTVERSION = "20.19"
        STEPSIZE = 42
        STARTTIME = 314159
        chart = ChannelReport(
            **{
                "Channels": NUMCHANNELS,
                "DTK_Version": VERSION,
                "DateTime": TIMESTAMP,
                "Report_Type": REPORTTYPE,
                "Report_Version": REPORTVERSION,
                "Simulation_Timestep": STEPSIZE,
                "Start_Time": STARTTIME,
                "Timesteps": TIMESTEPS,
            }
        )
        CHANNELA = "ChannelA"
        UNITSA = "prngs"
        adata = [randint(0, 8192) for _ in range(TIMESTEPS)]
        chart.channels[CHANNELA] = Channel(CHANNELA, UNITSA, adata)
        CHANNELB = "ChannelB"
        UNITSB = "probability"
        bdata = [random() for _ in range(TIMESTEPS)]
        chart.channels[CHANNELB] = Channel(CHANNELB, UNITSB, bdata)

        self.assertEqual(chart.num_channels, 2)
        self.assertEqual(chart.dtk_version, VERSION)
        self.assertEqual(chart.time_stamp, TIMESTAMP)
        self.assertEqual(chart.report_type, REPORTTYPE)
        self.assertEqual(chart.report_version, REPORTVERSION)
        self.assertEqual(chart.step_size, STEPSIZE)
        self.assertEqual(chart.start_time, STARTTIME)
        self.assertEqual(chart.num_time_steps, TIMESTEPS)

        self.assertEqual(len(chart.channels), NUMCHANNELS)

        self.assertEqual(chart.channels[CHANNELA].units, UNITSA)
        self.assertEqual(len(chart.channels[CHANNELA].data), TIMESTEPS)
        self.assertListEqual(list(chart.channels[CHANNELA].data), adata)

        self.assertEqual(chart.channels[CHANNELB].units, UNITSB)
        self.assertEqual(len(chart.channels[CHANNELB].data), TIMESTEPS)
        self.assertListEqual(list(chart.channels[CHANNELB].data), bdata)

        self.assertSetEqual(set(chart.channel_names), {CHANNELA, CHANNELB})

        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)
            filename = path / "TestChart.json"
            chart.write_file(str(filename), indent=2)

            roundtrip = ChannelReport(str(filename))

            self.assertEqual(roundtrip.num_channels, 2)
            self.assertEqual(roundtrip.dtk_version, VERSION)
            self.assertEqual(roundtrip.time_stamp, TIMESTAMP)
            self.assertEqual(roundtrip.report_type, REPORTTYPE)
            self.assertEqual(roundtrip.report_version, REPORTVERSION)
            self.assertEqual(roundtrip.step_size, STEPSIZE)
            self.assertEqual(roundtrip.start_time, STARTTIME)
            self.assertEqual(roundtrip.num_time_steps, TIMESTEPS)

            self.assertEqual(len(roundtrip.channels), NUMCHANNELS)

            self.assertEqual(roundtrip.channels[CHANNELA].units, UNITSA)
            self.assertEqual(len(roundtrip.channels[CHANNELA].data), TIMESTEPS)
            self.assertListEqual(list(roundtrip.channels[CHANNELA].data), adata)

            self.assertEqual(roundtrip.channels[CHANNELB].units, UNITSB)
            self.assertEqual(len(roundtrip.channels[CHANNELB].data), TIMESTEPS)
            self.assertListEqual(list(roundtrip.channels[CHANNELB].data), bdata)

            self.assertSetEqual(set(roundtrip.channel_names), {CHANNELA, CHANNELB})

        return

    def test_timeStampFromString(self):

        now = datetime.now()
        time_stamp = f"{now:%a %B %d %Y %H:%M:%S}"
        icj = ChannelReport()
        icj.time_stamp = time_stamp
        self.assertEqual(icj.time_stamp, time_stamp)

        return

    def test_timeStampFromDatetime(self):

        now = datetime.now()
        icj = ChannelReport()
        icj.time_stamp = now
        time_stamp = f"{now:%a %B %d %Y %H:%M:%S}"
        self.assertEqual(icj.time_stamp, time_stamp)

        return

    def test_setters(self):

        report = ChannelReport()

        report.dtk_version = TestHeader._DTK_VERSION
        report.time_stamp = TestHeader._TIME_STAMP
        report.report_type = TestHeader._REPORT_TYPE
        report.report_version = TestHeader._REPORT_VERSION
        report.step_size = TestHeader._TIME_STEP
        report.start_time = TestHeader._START_TIME
        report.num_time_steps = TestHeader._TIME_STEPS

        self.assertEqual(report.dtk_version, TestHeader._DTK_VERSION)
        self.assertEqual(
            report.time_stamp, f"{TestHeader._TIME_STAMP:%a %B %d %Y %H:%M:%S}"
        )
        self.assertEqual(report.report_type, TestHeader._REPORT_TYPE)
        self.assertEqual(report.report_version, TestHeader._REPORT_VERSION)
        self.assertEqual(report.step_size, TestHeader._TIME_STEP)
        self.assertEqual(report.start_time, TestHeader._START_TIME)
        self.assertEqual(report.num_time_steps, TestHeader._TIME_STEPS)

        return

    def test_asDataframe(self):

        chart = ChannelReport(os.path.join(manifest.reports_folder, "InsetChart.json"))
        df = chart.as_dataframe()

        self.assertEqual(len(df.columns), 16)
        self.assertAlmostEqual(df.Infected[10], 0.000001222560626957, 16)
        self.assertEqual(df["Statistical Population"][364], 7544187)

        self.assertSetEqual(
            set(df.columns),
            {
                "Births",
                "Campaign Cost",
                "Daily (Human) Infection Rate",
                "Disease Deaths",
                "Exposed Population",
                "Human Infectious Reservoir",
                "Infected",
                "Infectious Population",
                "Log Prevalence",
                "New Infections",
                "Newly Symptomatic",
                "Recovered Population",
                "Statistical Population",
                "Susceptible Population",
                "Symptomatic Population",
                "Waning Population",
            },
        )

        return

    def test_badNumChannels(self):

        header = Header()
        self.assertRaises(AssertionError, Header.num_channels.__set__, header, 0)
        self.assertRaises(AssertionError, Header.num_channels.__set__, header, -10)

        return

    def test_badStepSize(self):

        icj = ChannelReport()
        self.assertRaises(AssertionError, ChannelReport.step_size.__set__, icj, 0)
        self.assertRaises(AssertionError, ChannelReport.step_size.__set__, icj, -10)

        return

    def test_badStartTime(self):

        icj = ChannelReport()
        self.assertRaises(AssertionError, ChannelReport.start_time.__set__, icj, -10)

        return

    def test_badNumberOfTimeSteps(self):

        icj = ChannelReport()
        self.assertRaises(AssertionError, ChannelReport.num_time_steps.__set__, icj, 0)
        self.assertRaises(
            AssertionError, ChannelReport.num_time_steps.__set__, icj, -10
        )

        return

    def test_unevenNumberOfTimeSteps(self):

        # InsetChart with channels with different numbers of time steps.
        chart = ChannelReport(kwargs={"Channels": 2})
        chart.channels["foo"] = Channel("foo", "units", [1, 1, 2, 3, 5, 8])
        chart.channels["bar"] = Channel("bar", "units", [1, 2, 3, 4, 5])
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)
            filename = path / "BadChart.json"

            self.assertRaises(
                AssertionError, ChannelReport.write_file, chart, str(filename)
            )

        return

    def test_missingHeaderInFile(self):

        self.assertRaises(
            AssertionError,
            ChannelReport,
            os.path.join(manifest.reports_folder, "missingHeader.json"),
        )

        return

    def test_missingChannelsInFile(self):

        self.assertRaises(
            AssertionError,
            ChannelReport,
            os.path.join(manifest.reports_folder, "missingChannels.json"),
        )

        return

    def test_missingUnitsInFileChannel(self):

        self.assertRaises(
            AssertionError,
            ChannelReport,
            os.path.join(manifest.reports_folder, "missingUnits.json"),
        )

        return

    def test_missingDataInFileChannel(self):

        self.assertRaises(
            AssertionError,
            ChannelReport,
            os.path.join(manifest.reports_folder, "missingData.json"),
        )

        return


class TestInsetJson():
    @classmethod
    def setUpClass(cls):
        cls.inset_path = manifest.reports_folder

    def test_icj_to_csv(self):
        inset_chart_json_to_csv_dataframe_pd(self.inset_path)
        csv_path = os.path.join(self.inset_path, "InsetChart.csv")
        self.assertTrue(os.path.isfile(csv_path), f"No InsetChart.csv file at {csv_path}")

        csv_df = pd.read_csv(csv_path)
        json_path = os.path.join(self.inset_path, "InsetChart.json")
        self.assertTrue(os.path.isfile(json_path), f"No InsetChart.json file at {json_path}")

        with open(json_path) as jc:
            json_dict = json.load(jc)

        for channel in json_dict["Channels"]:
            self.assertIn(channel, csv_df.columns, f"Column {channel} was not found in the csv at {csv_path}")


class TestPropReport():
    @classmethod
    def setUpClass(self):
        self.report_path = os.path.join(manifest.reports_folder, 'prop_dir')

    @pytest.mark.skip("known issue")
    def test_prop_report_json_to_csv(self):
        self.assertTrue(self.report_path.exists(), f"{self.report_path} cannot be found")
        prop_report_json_to_csv(self.report_path)

        csv_path = self.report_path / "prop_report_infected.csv"
        self.assertTrue(csv_path.exists(), f"{csv_path} cannot be found, should have been generated by prop_report_json_to_csv()")
        df = pd.read_csv(csv_path)
        self.assertIn("Infected:", df.columns, msg=f"Infected column not in {self.report_path}")
