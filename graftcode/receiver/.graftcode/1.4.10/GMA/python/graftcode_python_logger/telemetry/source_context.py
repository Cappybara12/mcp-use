import inspect
import logging
import os
from types import FrameType
from typing import Optional, Tuple


def _get_class_info(frame: FrameType) -> Tuple[Optional[str], str]:
    """
    Extract class name from a frame if the function is a method.

    Args:
        frame: Frame object to analyze

    Returns:
        A tuple of (class_name, function_name). class_name will be None
        if the function is not a class method.
    """
    function_name = frame.f_code.co_name

    # Check if this is a method call by looking at the first argument's name and locals
    args = frame.f_code.co_varnames
    if args and args[0] == "self" and "self" in frame.f_locals:
        instance = frame.f_locals["self"]
        class_name = instance.__class__.__name__
        return class_name, function_name

    # No class found
    return None, function_name


def add_source_context(record: logging.LogRecord) -> None:
    """
    Add source context information to the log record.

    This function analyzes the call stack to determine the module, class,
    function, file and line number that generated the log message, and
    adds this information to the log record as attributes.

    Args:
        record: Log record to enhance with source context
    """
    # Find the first non-logger frame
    frame_info = None
    frame = None
    class_name = None

    # Start from the 3rd frame to skip logging machinery
    current_frame = inspect.currentframe()
    for _ in range(3):
        if current_frame:
            current_frame = current_frame.f_back

    # Walk up the call stack to find the first non-logging frame
    frame = current_frame
    while frame:
        module_name = frame.f_globals.get("__name__", "")
        if not (
            module_name.startswith("logging")
            or module_name.startswith("graftcode_python_logger")
        ):
            frame_info = inspect.getframeinfo(frame)
            # Try to get class name
            class_name, function_name = _get_class_info(frame)
            break
        frame = frame.f_back

    if frame_info:
        record.source_file = os.path.basename(frame_info.filename)
        record.source_line = frame_info.lineno
        record.source_function = frame_info.function
        record.source_class = class_name

        # Get the module name
        module = inspect.getmodule(frame)
        record.source_module = module.__name__ if module else "unknown"

    # Ensure class name is available
    if not hasattr(record, "source_class") or record.source_class is None:
        # Try to get the class from the module name
        if hasattr(record, "source_module"):
            module_parts = record.source_module.split(".")
            if len(module_parts) > 0:
                record.source_class = module_parts[-1]
            else:
                record.source_class = "UnknownClass"
        else:
            record.source_class = "UnknownClass"
