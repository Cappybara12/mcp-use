from dataclasses import dataclass, field
from enum import IntEnum
from typing import Dict, Optional


class LogLevel(IntEnum):
    """
    Log levels that determine how detailed your logs will be.

    The values match standard Python logging library levels:
    - DEBUG (10): Detailed information, useful for troubleshooting
    - INFO (20): Confirmation that things are working as expected
    - WARNING (30): Indication that something unexpected happened
    - ERROR (40): Due to a serious problem, some function couldn't be performed
    - CRITICAL (50): A very serious error, application might stop running

    The numbers are spaced by 10 to allow creating custom levels in between.
    For example, you could create a VERBOSE level at 15 between DEBUG and INFO.
    """

    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50


@dataclass
class GCLoggerOptions:
    """
    Configuration options for the GraftCode logger.

    This class contains all the settings that control how your logs are created,
    formatted, and where they're sent. You can customize many aspects of logging
    through these settings.

    Basic Logging Settings:
    -----------------------
    minimum_log_level: The lowest severity level to record
    category_filters: Controls log levels for specific modules
    environment: Name of your deployment environment
    service_name: Name that identifies your service in logs
    app_service_name: Name of your specific application component

    Log Formatting Options:
    ----------------------
    custom_dimensions: Extra properties added to every log message
    enable_structured_console_logging: Whether to format logs to the console
    include_scopes: Whether to include operation hierarchy context
    include_source_context: Whether to add source code information to logs
    include_exception_stack_trace: Whether to include stack traces in logs
    default_class_name: Default name when class information isn't available

    Application Insights Settings:
    -----------------------------
    use_app_insights_from_env: Whether to get AppInsights connection from env var
    app_insights_connection_string: Direct connection string for AppInsights
    app_insights_env_var: Name of the env var with AppInsights connection
    app_insights_buffer_size: How many logs to collect before sending
    app_insights_export_interval: How often to send logs (in seconds)
    """

    # The lowest severity level of messages to be logged
    # For example, LogLevel.INFO will ignore DEBUG logs
    minimum_log_level: LogLevel = LogLevel.INFO

    # Specific log level settings for individual modules to reduce noise
    # Example: {"requests": LogLevel.WARNING} - only log warnings from 'requests'
    category_filters: Dict[str, LogLevel] = field(default_factory=dict)

    # The name of your deployment environment (helps filter logs by environment)
    # Common values: "Development", "Staging", "Production"
    environment: str = "Development"

    # Additional properties to include with every log message
    # Example: {"version": "1.0.0", "region": "west-us"}
    custom_dimensions: Dict[str, str] = field(default_factory=dict)

    # Whether to output nicely formatted logs to the console
    enable_structured_console_logging: bool = True

    # Whether to include parent-child operation relationships in logs
    include_scopes: bool = True

    # Whether to read the Application Insights connection from an env variable
    use_app_insights_from_env: bool = True

    # Direct connection string for Application Insights
    # Only used if use_app_insights_from_env is False
    app_insights_connection_string: Optional[str] = None

    # Whether to add source code information (file, class, method) to logs
    # This helps you trace exactly where each log came from
    include_source_context: bool = True

    # Whether to include full stack traces in exception logs
    # Helpful for debugging but can make logs larger
    include_exception_stack_trace: bool = True

    # Name that identifies your service in logs. Must be provided explicitly
    # by every consumer (see graftcode-protocol/docs/observability-contract.md);
    # a sentinel default is kept only so the dataclass ordering stays backward
    # compatible, but GCLoggerFactory.initialize() now rejects it.
    service_name: str = ""

    # Name of the specific application component.
    # Defaults to service_name when blank - matching WEBSITE_SITE_NAME
    # fallback behaviour in other stacks.
    app_service_name: str = ""

    # Default class name to use when source class information isn't available
    default_class_name: str = "UnknownClass"

    # Name of the environment variable containing the AppInsights connection
    app_insights_env_var: str = "APPLICATIONINSIGHTS_CONNECTION_STRING"

    # How many log items to collect before sending them to Application Insights
    # Larger values are more efficient but may delay logs appearing
    app_insights_buffer_size: int = 100

    # How often to send collected logs to Application Insights (in seconds)
    # Smaller values reduce delay but may increase overhead
    app_insights_export_interval: float = 15.0
