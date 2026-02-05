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
        assert(header.num_channels==0)
        assert(header.dtk_version=="unknown-branch (unknown)")
        assert(header.time_stamp==f"{datetime.now():%a %B %d %Y %H:%M:%S}")
        assert(header.report_type=="InsetChart")
        assert(header.report_version=="0.0")
        assert(header.step_size==1)
        assert(header.start_time==0)
        assert(header.num_time_steps==0)

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

        assert(header.num_channels==TestHeader._NUM_CHANNELS)
        assert(header.dtk_version==TestHeader._DTK_VERSION)
        assert(header.time_stamp==f"{TestHeader._TIME_STAMP:%a %B %d %Y %H:%M:%S}")
        assert(header.report_type==TestHeader._REPORT_TYPE)
        assert(header.report_version==TestHeader._REPORT_VERSION)
        assert(header.step_size==TestHeader._TIME_STEP)
        assert(header.start_time==TestHeader._START_TIME)
        assert(header.num_time_steps==TestHeader._TIME_STEPS)

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

        assert(header.num_channels==TestHeader._NUM_CHANNELS)
        assert(header.dtk_version==TestHeader._DTK_VERSION)
        assert(header.time_stamp==f"{TestHeader._TIME_STAMP:%a %B %d %Y %H:%M:%S}")
        assert(header.report_type==TestHeader._REPORT_TYPE)
        assert(header.report_version==TestHeader._REPORT_VERSION)
        assert(header.step_size==TestHeader._TIME_STEP)
        assert(header.start_time==TestHeader._START_TIME)
        assert(header.num_time_steps==TestHeader._TIME_STEPS)

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

        assert(header.as_dictionary()==source)

        return


class TestChannel():

    _TITLE = "Gas Mileage"
    _UNITS = "picometers per tun"
    _DATA = [1, 1, 2, 3, 5, 8]

    def test_ctor(self):

        channel = Channel(TestChannel._TITLE, TestChannel._UNITS, TestChannel._DATA)

        assert(channel.title==TestChannel._TITLE)
        assert(channel.units==TestChannel._UNITS)
        assert(channel.data==TestChannel._DATA)

        return

    def test_setters(self):

        channel = Channel(None, None, [_ for _ in range(6)])

        channel.title = TestChannel._TITLE
        channel.units = TestChannel._UNITS

        for index in range(6):
            channel.data[index] = TestChannel._DATA[index]

        assert(channel.title==TestChannel._TITLE)
        assert(channel.units==TestChannel._UNITS)
        assert(channel.data==TestChannel._DATA)

        return

    def test_as_dictionary(self):

        channel = Channel(TestChannel._TITLE, TestChannel._UNITS, TestChannel._DATA)

        test_dict = {TestChannel._TITLE: {"Units": TestChannel._UNITS,"Data": TestChannel._DATA}}
        assert(channel.as_dictionary()==test_dict)

        return


class TestChannels():
    def test_fromFile(self):

        chart = ChannelReport(os.path.join(manifest.reports_folder, "InsetChart.json"))
        assert(chart.header.time_stamp=="Wed November 27 2019 14:49:15")
        assert(chart.header.dtk_version=="0 unknown-branch (unknown) May 31 2019 15:04:44")
        assert(chart.header.report_type=="InsetChart")
        assert(chart.header.report_version=="3.2")
        assert(chart.header.start_time==0)
        assert(chart.header.step_size==1)
        assert(chart.header.num_time_steps==365)
        assert(chart.header.num_channels==16)
        assert(len(chart.channels)==16)
        assert(chart.channels["Births"].units=="Births")
        assert(round(1e10*chart.channels["Infected"].data[10])==12226)

        test_set = set({
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
            })
        assert(set(chart.channel_names)==test_set)

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

        assert(chart.num_channels==2)
        assert(chart.dtk_version==VERSION)
        assert(chart.time_stamp==TIMESTAMP)
        assert(chart.report_type==REPORTTYPE)
        assert(chart.report_version==REPORTVERSION)
        assert(chart.step_size==STEPSIZE)
        assert(chart.start_time==STARTTIME)
        assert(chart.num_time_steps==TIMESTEPS)
        assert(len(chart.channels)==NUMCHANNELS)
        assert(chart.channels[CHANNELA].units==UNITSA)
        assert(len(chart.channels[CHANNELA].data)==TIMESTEPS)
        assert(list(chart.channels[CHANNELA].data)==adata)
        assert(chart.channels[CHANNELB].units==UNITSB)
        assert(len(chart.channels[CHANNELB].data)==TIMESTEPS)
        assert(list(chart.channels[CHANNELB].data)==bdata)
        assert(set(chart.channel_names)=={CHANNELA, CHANNELB})

        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)
            filename = path / "TestChart.json"
            chart.write_file(str(filename), indent=2)

            roundtrip = ChannelReport(str(filename))

            assert(roundtrip.num_channels==2)
            assert(roundtrip.dtk_version==VERSION)
            assert(roundtrip.time_stamp==TIMESTAMP)
            assert(roundtrip.report_type==REPORTTYPE)
            assert(roundtrip.report_version==REPORTVERSION)
            assert(roundtrip.step_size==STEPSIZE)
            assert(roundtrip.start_time==STARTTIME)
            assert(roundtrip.num_time_steps==TIMESTEPS)
            assert(len(roundtrip.channels)==NUMCHANNELS)
            assert(roundtrip.channels[CHANNELA].units==UNITSA)
            assert(len(roundtrip.channels[CHANNELA].data)==TIMESTEPS)
            assert(list(roundtrip.channels[CHANNELA].data)==adata)
            assert(roundtrip.channels[CHANNELB].units==UNITSB)
            assert(len(roundtrip.channels[CHANNELB].data)==TIMESTEPS)
            assert(list(roundtrip.channels[CHANNELB].data)==bdata)
            assert(set(roundtrip.channel_names)=={CHANNELA, CHANNELB})

        return

    def test_timeStampFromString(self):

        now = datetime.now()
        time_stamp = f"{now:%a %B %d %Y %H:%M:%S}"
        icj = ChannelReport()
        icj.time_stamp = time_stamp
        assert(icj.time_stamp==time_stamp)

        return

    def test_timeStampFromDatetime(self):

        now = datetime.now()
        icj = ChannelReport()
        icj.time_stamp = now
        time_stamp = f"{now:%a %B %d %Y %H:%M:%S}"
        assert(icj.time_stamp==time_stamp)

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

        assert(report.dtk_version==TestHeader._DTK_VERSION)
        assert(report.time_stamp==f"{TestHeader._TIME_STAMP:%a %B %d %Y %H:%M:%S}")
        assert(report.report_type==TestHeader._REPORT_TYPE)
        assert(report.report_version==TestHeader._REPORT_VERSION)
        assert(report.step_size==TestHeader._TIME_STEP)
        assert(report.start_time==TestHeader._START_TIME)
        assert(report.num_time_steps==TestHeader._TIME_STEPS)

        return

    def test_asDataframe(self):

        chart = ChannelReport(os.path.join(manifest.reports_folder, "InsetChart.json"))
        df = chart.as_dataframe()

        assert(len(df.columns)==16)
        assert(round(1e10*df.Infected[10])==12226)
        assert(df["Statistical Population"][364]==7544187)

        test_set = set({
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
            })
        assert(set(df.columns)==test_set)

        return

    def test_badNumChannels(self):

        header = Header()
        with pytest.raises(Exception) as e_info:
            Header.num_channels.__set__(header, 0)
        with pytest.raises(Exception) as e_info:
            Header.num_channels.__set__(header, -10)

        return

    def test_badStepSize(self):

        icj = ChannelReport()
        with pytest.raises(Exception) as e_info:
            ChannelReport.step_size.__set__(icj, 0)
        with pytest.raises(Exception) as e_info:
            ChannelReport.step_size.__set__(icj, -10)

        return

    def test_badStartTime(self):

        icj = ChannelReport()
        with pytest.raises(Exception) as e_info:
            ChannelReport.start_time.__set__(icj, -10)

        return

    def test_badNumberOfTimeSteps(self):

        icj = ChannelReport()
        with pytest.raises(Exception) as e_info:
            ChannelReport.num_time_steps.__set__(icj, 0)
        with pytest.raises(Exception) as e_info:
            ChannelReport.num_time_steps.__set__(icj, -10)

        return

    def test_unevenNumberOfTimeSteps(self):

        # InsetChart with channels with different numbers of time steps.
        chart = ChannelReport(kwargs={"Channels": 2})
        chart.channels["foo"] = Channel("foo", "units", [1, 1, 2, 3, 5, 8])
        chart.channels["bar"] = Channel("bar", "units", [1, 2, 3, 4, 5])
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)
            filename = path / "BadChart.json"
            with pytest.raises(Exception) as e_info:
                ChannelReport.write_file(chart, str(filename))

        return

    def test_missingHeaderInFile(self):

        with pytest.raises(Exception) as e_info:
            ChannelReport(os.path.join(manifest.reports_folder, "missingHeader.json"))

        return

    def test_missingChannelsInFile(self):

        with pytest.raises(Exception) as e_info:
            ChannelReport(os.path.join(manifest.reports_folder, "missingChannels.json"))

        return

    def test_missingUnitsInFileChannel(self):

        with pytest.raises(Exception) as e_info:
            ChannelReport(os.path.join(manifest.reports_folder, "missingUnits.json"))

        return

    def test_missingDataInFileChannel(self):

        with pytest.raises(Exception) as e_info:
            ChannelReport(os.path.join(manifest.reports_folder, "missingData.json"))

        return


class TestInsetJson():
    @pytest.fixture(autouse=True)
    # Set-up and tear-down for each test
    def run_every_test(self, request) -> None:
        self.inset_path = manifest.reports_folder

    def test_icj_to_csv(self):
        inset_chart_json_to_csv_dataframe_pd(self.inset_path)
        csv_path = os.path.join(self.inset_path, "InsetChart.csv")
        assert(os.path.isfile(csv_path))

        csv_df = pd.read_csv(csv_path)
        json_path = os.path.join(self.inset_path, "InsetChart.json")
        assert(os.path.isfile(json_path))

        with open(json_path) as jc:
            json_dict = json.load(jc)

        for channel in json_dict["Channels"]:
            assert(channel in csv_df.columns)


class TestPropReport():
    @pytest.fixture(autouse=True)
    # Set-up and tear-down for each test
    def run_every_test(self, request) -> None:
        self.report_path = os.path.join(manifest.reports_folder, 'prop_dir')

    @pytest.mark.skip("known issue")
    def test_prop_report_json_to_csv(self):
        assert(self.report_path.exists())
        prop_report_json_to_csv(self.report_path)

        csv_path = self.report_path / "prop_report_infected.csv"
        assert(csv_path.exists())
        df = pd.read_csv(csv_path)
        assert("Infected:" in df.columns)
