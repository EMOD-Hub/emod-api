#!/usr/bin/env python3

"""Module for reading InsetChart.json channels."""

from datetime import datetime
import json

_CHANNELS = "Channels"
_DTK_VERSION = "DTK_Version"
_DATETIME = "DateTime"
_REPORT_TYPE = "Report_Type"
_REPORT_VERSION = "Report_Version"
_SIMULATION_TIMESTEP = "Simulation_Timestep"
_START_TIME = "Start_Time"
_TIMESTEPS = "Timesteps"

_KNOWN_KEYS = {
    _CHANNELS,
    _DTK_VERSION,
    _DATETIME,
    _REPORT_TYPE,
    _REPORT_VERSION,
    _SIMULATION_TIMESTEP,
    _START_TIME,
    _TIMESTEPS,
}

_TYPE_INSETCHART = "InsetChart"

_UNITS = "Units"
_DATA = "Data"

_HEADER = "Header"


class Header(object):

    # Allow callers to send an arbitrary dictionary, potentially, with extra key:value pairs.
    def __init__(self, **kwargs):

        self._channelCount = kwargs[_CHANNELS] if kwargs and _CHANNELS in kwargs else 0
        self._dtkVersion = (
            kwargs[_DTK_VERSION] if kwargs and _DTK_VERSION in kwargs else "unknown-branch (unknown)"
        )
        self._timeStamp = (
            kwargs[_DATETIME]
            if kwargs and _DATETIME in kwargs
            else f"{datetime.now():%a %B %d %Y %H:%M:%S}"
        )
        self._reportType = (
            kwargs[_REPORT_TYPE]
            if kwargs and _REPORT_TYPE in kwargs
            else _TYPE_INSETCHART
        )
        self._reportVersion = (
            kwargs[_REPORT_VERSION] if kwargs and _REPORT_VERSION in kwargs else "0.0"
        )
        self._stepSize = (
            kwargs[_SIMULATION_TIMESTEP]
            if kwargs and _SIMULATION_TIMESTEP in kwargs
            else 1
        )
        self._startTime = kwargs[_START_TIME] if kwargs and _START_TIME in kwargs else 0
        self._numTimeSteps = (
            kwargs[_TIMESTEPS] if kwargs and _TIMESTEPS in kwargs else 0
        )
        self._tags = {key: kwargs[key] for key in kwargs if key not in _KNOWN_KEYS}

        return

    @property
    def num_channels(self) -> int:
        return self._channelCount

    @num_channels.setter
    def num_channels(self, count: int):
        """> 0"""
        assert count > 0, "numChannels must be > 0"
        self._channelCount = count
        return

    @property
    def dtk_version(self) -> str:
        return self._dtkVersion

    @dtk_version.setter
    def dtk_version(self, version: str):
        """major.minor"""
        self._dtkVersion = f"{version}"

    @property
    def time_stamp(self) -> str:
        return self._timeStamp

    @time_stamp.setter
    def time_stamp(self, timestamp: (datetime, str)):
        """datetime or string"""
        self._timeStamp = (
            f"{timestamp:%a %B %d %Y %H:%M:%S}"
            if isinstance(timestamp, datetime)
            else f"{timestamp}"
        )
        return

    @property
    def report_type(self) -> str:
        return self._reportType

    @report_type.setter
    def report_type(self, report_type: str):
        self._reportType = f"{report_type}"
        return

    @property
    def report_version(self) -> str:
        return self._reportVersion

    @report_version.setter
    def report_version(self, version: str):
        self._reportVersion = f"{version}"
        return

    @property
    def step_size(self) -> int:
        """>= 1"""
        return self._stepSize

    @step_size.setter
    def step_size(self, size: int):
        """>= 1"""
        self._stepSize = int(size)
        assert self._stepSize >= 1, "stepSize must be >= 1"
        return

    @property
    def start_time(self) -> int:
        """>= 0"""
        return self._startTime

    @start_time.setter
    def start_time(self, time: int):
        """>= 0"""
        self._startTime = int(time)
        assert self._startTime >= 0, "startTime must be >= 0"
        return

    @property
    def num_time_steps(self) -> int:
        """>= 1"""
        return self._numTimeSteps

    @num_time_steps.setter
    def num_time_steps(self, count: int):
        """>= 1"""
        self._numTimeSteps = int(count)
        assert self._numTimeSteps > 0, "numTimeSteps must be > 0"
        return

    def as_dictionary(self) -> dict:
        # https://stackoverflow.com/questions/38987/how-do-i-merge-two-dictionaries-in-a-single-expression
        return {
            **{
                _CHANNELS: self.num_channels,
                _DTK_VERSION: self.dtk_version,
                _DATETIME: self.time_stamp,
                _REPORT_TYPE: self.report_type,
                _REPORT_VERSION: self.report_version,
                _SIMULATION_TIMESTEP: self.step_size,
                _START_TIME: self.start_time,
                _TIMESTEPS: self.num_time_steps,
            },
            **self._tags,
        }


class Channel(object):
    def __init__(self, title, units, data):
        self._title = title
        self._units = units
        self._data = data
        return

    @property
    def title(self) -> str:
        return self._title

    @title.setter
    def title(self, title: str):
        self._title = f"{title}"
        return

    @property
    def units(self) -> str:
        return self._units

    @units.setter
    def units(self, units: str):
        self._units = f"{units}"
        return

    @property
    def data(self):
        return self._data

    def __getitem__(self, item):
        """Index into channel data by time step"""
        return self._data[item]

    def __setitem__(self, key, value):
        """Update channel data by time step"""
        self._data[key] = value
        return

    def as_dictionary(self) -> dict:
        return {self.title: {_UNITS: self.units, _DATA: list(self.data)}}


class ChannelReport(object):
    def __init__(self, filename: str = None, **kwargs):

        if filename is not None:
            assert isinstance(filename, str), "filename must be a string"
            self._from_file(filename)
        else:
            self._header = Header(**kwargs)
            self._channels = {}

        return

    @property
    def header(self) -> Header:
        return self._header

    # pass-through to header

    @property
    def dtk_version(self) -> str:
        return self._header.dtk_version

    @dtk_version.setter
    def dtk_version(self, version: str):
        self._header.dtk_version = version
        return

    @property
    def time_stamp(self) -> str:
        return self._header.time_stamp

    @time_stamp.setter
    def time_stamp(self, time_stamp: (datetime, str)):
        self._header.time_stamp = time_stamp
        return

    @property
    def report_type(self) -> str:
        return self._header.report_type

    @report_type.setter
    def report_type(self, report_type: str):
        self._header.report_type = report_type
        return

    @property
    def report_version(self) -> str:
        """major.minor"""
        return self._header.report_version

    @report_version.setter
    def report_version(self, version: str):
        self._header.report_version = version
        return

    @property
    def step_size(self) -> int:
        """>= 1"""
        return self._header.step_size

    @step_size.setter
    def step_size(self, size: int):
        """>= 1"""
        self._header.step_size = size
        return

    @property
    def start_time(self) -> int:
        """>= 0"""
        return self._header.start_time

    @start_time.setter
    def start_time(self, time: int):
        """>= 0"""
        self._header.start_time = time
        return

    @property
    def num_time_steps(self) -> int:
        """> 0"""
        return self._header.num_time_steps

    @num_time_steps.setter
    def num_time_steps(self, count: int):
        """> 0"""
        self._header.num_time_steps = count
        return

    # end pass-through

    @property
    def num_channels(self) -> int:
        return len(self._channels)

    @property
    def channel_names(self) -> list:
        return sorted(self._channels.keys())

    @property
    def channels(self) -> dict:
        """Channel objects keyed on channel name/title"""
        return self._channels

    def __getitem__(self, item: str) -> Channel:
        """Return Channel object by channel name/title"""
        return self._channels[item]

    def as_dataframe(self):
        import pandas as pd

        dataframe = pd.DataFrame(
            {key: self.channels[key].data for key in self.channel_names}
        )
        return dataframe

    def write_file(self, filename: str, indent: int = 0, separators=(",", ":")):
        """Write inset chart to specified text file."""

        # in case this was generated locally, lets do some consistency checks
        assert len(self._channels) > 0, "Report has no channels."
        counts = set([len(channel.data) for title, channel in self.channels.items()])
        assert (
            len(counts) == 1
        ), f"Channels do not all have the same number of values ({counts})"

        self._header.num_channels = len(self._channels)
        self.num_time_steps = len(self._channels[self.channel_names[0]].data)

        with open(filename, "w") as file:
            channels = {}
            for _, channel in self.channels.items():
                # https://stackoverflow.com/questions/38987/how-do-i-merge-two-dictionaries-in-a-single-expression
                channels = {**channels, **channel.as_dictionary()}
            chart = {_HEADER: self.header.as_dictionary(), _CHANNELS: channels}
            json.dump(chart, file, indent=indent, separators=separators)

        return

    def _from_file(self, filename: str):
        def validate_file(_jason):

            assert _HEADER in _jason, f"'{filename}' missing '{_HEADER}' object."
            assert (
                _CHANNELS in _jason[_HEADER]
            ), f"'{filename}' missing '{_HEADER}/{_CHANNELS}' key."
            assert (
                _TIMESTEPS in _jason[_HEADER]
            ), f"'{filename}' missing '{_HEADER}/{_TIMESTEPS}' key."
            assert _CHANNELS in _jason, f"'{filename}' missing '{_CHANNELS}' object."
            num_channels = _jason[_HEADER][_CHANNELS]
            channels_len = len(_jason[_CHANNELS])
            assert num_channels == channels_len, (
                f"'{filename}': "
                + f"'{_HEADER}/{_CHANNELS}' ({num_channels}) does not match number of {_CHANNELS} ({channels_len})."
            )

            return

        def validate_channel(_channel, _title, _header):

            assert _UNITS in _channel, f"Channel '{_title}' missing '{_UNITS}' entry."
            assert _DATA in _channel, f"Channel '{_title}' missing '{_DATA}' entry."
            count = len(_channel[_DATA])
            assert (
                count == _header.num_time_steps
            ), f"Channel '{title}' data values ({count}) does not match header Time_Steps ({_header.num_time_steps})."

            return

        with open(filename, "rb") as file:
            jason = json.load(file)
            validate_file(jason)

            header_dict = jason[_HEADER]
            self._header = Header(**header_dict)
            self._channels = {}

            channels = jason[_CHANNELS]
            for title, channel in channels.items():
                validate_channel(channel, title, self._header)
                units = channel[_UNITS]
                data = channel[_DATA]
                self._channels[title] = Channel(title, units, data)

        return
