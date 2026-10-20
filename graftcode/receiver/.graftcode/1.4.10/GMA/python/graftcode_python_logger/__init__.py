from .logger_factory import GCLoggerFactory
from .logger_options import GCLoggerOptions, LogLevel
from .operation_context import OperationContext
from .session_scope import SessionScope

__all__ = [
    "GCLoggerFactory",
    "GCLoggerOptions",
    "LogLevel",
    "OperationContext",
    "SessionScope",
]

# First check if FastAPI is installed before trying to import the integration
try:
    import fastapi  # noqa

    # Only import FastAPI integration if FastAPI is available
    try:
        from .telemetry.fastapi_integration import (  # noqa
            LoggingMiddleware,
            setup_request_logging,
            track_endpoint_operation,
        )

        __all__.extend(
            [
                "LoggingMiddleware",
                "setup_request_logging",
                "track_endpoint_operation",
            ]
        )
    except ImportError:
        # FastAPI integration module couldn't be imported
        pass
except ImportError:
    # FastAPI is not installed, do not attempt to import integration
    pass
