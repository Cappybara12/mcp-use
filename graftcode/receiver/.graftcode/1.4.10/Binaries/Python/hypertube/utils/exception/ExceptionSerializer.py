import os
import traceback

from hypertube.utils.ExceptionType import ExceptionType
from hypertube.utils.Command import Command
from hypertube.utils.CommandType import CommandType
from hypertube.utils.RuntimeName import RuntimeName


class ExceptionSerializer:

    @staticmethod
    def serialize_exception(exception, command):
        exception_command = Command(RuntimeName.python, CommandType.Exception, [])
        stack_classes = []
        stack_methods = []
        stack_lines = []
        stack_files = []

        try:
            tb = exception.__traceback__
            trace = traceback.extract_tb(tb)
            exception_message = str(exception)
            exception_name = exception.__class__.__name__

            for frame_summary in trace:
                class_name = ExceptionSerializer.safe_get_class_name(frame_summary)
                method_name = ExceptionSerializer.safe_get_method_name(frame_summary)
                file_name = ExceptionSerializer.safe_get_file_name(frame_summary)
                line = ExceptionSerializer.safe_get_line(frame_summary)

                if "hypertube" not in file_name and "reflect" not in class_name:
                    stack_classes.append(class_name)
                    stack_methods.append(method_name)
                    stack_lines.append(str(line))
                    stack_files.append(file_name)

            stack_classes_str = "|".join(stack_classes)
            stack_methods_str = "|".join(stack_methods)
            stack_lines_str = "|".join(stack_lines)
            stack_files_str = "|".join(stack_files)

            exception_command = exception_command.add_arg_to_payload(
                ExceptionSerializer.get_exception_code(exception_name))
            exception_command = exception_command.add_arg_to_payload(str(command))
            exception_command = exception_command.add_arg_to_payload(exception_name)
            exception_command = exception_command.add_arg_to_payload(str(exception_message))
            exception_command = exception_command.add_arg_to_payload(stack_classes_str)
            exception_command = exception_command.add_arg_to_payload(stack_methods_str)
            exception_command = exception_command.add_arg_to_payload(stack_lines_str)
            exception_command = exception_command.add_arg_to_payload(stack_files_str)

        except Exception as ex:
            exception_command = Command(RuntimeName.python, CommandType.Exception, [])
            exception_command = exception_command.add_arg_to_payload(
                ExceptionSerializer.get_exception_code(ex.__class__.__name__))
            exception_command = exception_command.add_arg_to_payload(command if command else "Command is null")
            exception_command = exception_command.add_arg_to_payload("Python Exception Serialization Error")
            exception_command = exception_command.add_arg_to_payload(str(ex))
            exception_command = exception_command.add_arg_to_payload("ExceptionSerializer")
            exception_command = exception_command.add_arg_to_payload("serialize_exception")
            exception_command = exception_command.add_arg_to_payload("undefined")
            exception_command = exception_command.add_arg_to_payload("ExceptionSerializer.py")

        return exception_command

    @staticmethod
    def safe_get_class_name(frame_summary):
        try:
            return ExceptionSerializer.format_class_name_from_file(frame_summary.filename)
        except Exception:
            return "undefined"

    @staticmethod
    def safe_get_method_name(frame_summary):
        try:
            return frame_summary.name if frame_summary.name else "undefined"
        except Exception:
            return "undefined"

    @staticmethod
    def safe_get_file_name(frame_summary):
        try:
            return frame_summary.filename if frame_summary.filename else "undefined"
        except Exception:
            return "undefined"

    @staticmethod
    def safe_get_line(frame_summary):
        try:
            return frame_summary.lineno if frame_summary.lineno >= 0 else 0
        except Exception:
            return 0

    @staticmethod
    def get_exception_code(exception_name):
        return ExceptionType.to_enum(exception_name)

    Exception = 0
    IOException = 1
    FileNotFoundException = 2
    RuntimeException = 3
    ArithmeticException = 4
    IllegalArgumentException = 5
    IndexOutOfBoundsException = 6
    NullPointerException = 7

    @staticmethod
    def format_class_name_from_file(filename):
        return os.path.splitext(os.path.split(filename)[1])[0]