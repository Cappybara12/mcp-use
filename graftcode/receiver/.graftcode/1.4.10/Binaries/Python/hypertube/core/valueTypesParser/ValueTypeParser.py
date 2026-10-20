import uuid
from datetime import datetime, time, timedelta

from urllib.parse import ParseResult

from hypertube.utils.DrawingTypes import Color, Point, color_channel
from hypertube.utils.Command import Command
from hypertube.utils.CommandType import CommandType



def _datetime_to_command(obj: datetime, runtime_name) -> Command:
    return Command(runtime_name, CommandType.ComplexValueType, ["datetime.datetime", obj.isoformat()])


def _uuid_to_command(obj: uuid.UUID, runtime_name) -> Command:
    return Command(runtime_name, CommandType.ComplexValueType, ["uuid.UUID", str(obj)])


def _time_to_command(obj: time, runtime_name) -> Command:
    return Command(runtime_name, CommandType.ComplexValueType, ["datetime.time", obj.isoformat()])


def _timedelta_to_command(obj: timedelta, runtime_name) -> Command:
    total_micros = obj.days * 86_400_000_000 + obj.seconds * 1_000_000 + obj.microseconds
    return Command(runtime_name, CommandType.ComplexValueType, ["datetime.timedelta", total_micros])


def _point_to_command(obj: Point, runtime_name) -> Command:
    return Command(runtime_name, CommandType.ComplexValueType, ["hypertube.utils.drawing_types.Point", obj.x, obj.y])


def _color_to_command(obj: Color, runtime_name) -> Command:
    return Command(
        runtime_name, CommandType.ComplexValueType,
        ["hypertube.utils.drawing_types.Color", color_channel(obj.a), color_channel(obj.r), color_channel(obj.g), color_channel(obj.b)],
    )


def _uri_to_command(obj: ParseResult, runtime_name) -> Command:
    href = obj.geturl() if isinstance(obj, ParseResult) else str(obj)
    return Command(runtime_name, CommandType.ComplexValueType, ["urllib.parse.ParseResult", href])


_PARSABLE_VALUE_TYPES = {
    datetime: _datetime_to_command,
    uuid.UUID: _uuid_to_command,
    time: _time_to_command,
    timedelta: _timedelta_to_command,
    Point: _point_to_command,
    Color: _color_to_command,
    ParseResult: _uri_to_command,
}


class ValueTypeParser:

    @staticmethod
    def is_parsable_value_type(type_) -> bool:
        return type_ in _PARSABLE_VALUE_TYPES

    @staticmethod
    def get_command_for_parsable_value_type(obj, runtime_name) -> Command:
        return _PARSABLE_VALUE_TYPES[type(obj)](obj, runtime_name)
