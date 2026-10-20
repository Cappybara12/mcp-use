import logging
import os
import re
from typing import Any, Dict, Optional, TYPE_CHECKING

# Import required dependencies, but handle the case when they are not available
try:
    from opencensus.ext.azure.log_exporter import AzureLogHandler
    from opencensus.ext.azure.trace_exporter import AzureExporter
    from opencensus.trace.samplers import AlwaysOnSampler
    from opencensus.trace.span_context import SpanContext
    from opencensus.trace.tracer import Tracer

    OPENCENSUS_AVAILABLE = True
except ImportError:
    # Define mock classes that will be used when opencensus is not available
    AzureLogHandler = type("AzureLogHandler", (), {})
    AzureExporter = type("AzureExporter", (), {})
    SpanContext = type("SpanContext", (), {})
    OPENCENSUS_AVAILABLE = False

try:
    from applicationinsights.channel import (
        AsynchronousQueue as _AIAsyncQueue,
        AsynchronousSender as _AIAsyncSender,
        TelemetryChannel as _AITelemetryChannel,
    )
    from applicationinsights.channel.contracts import (
        Data as _AIData,
        Envelope as _AIEnvelope,
        RequestData as _AIRequestData,
    )

    APPLICATIONINSIGHTS_AVAILABLE = True
except ImportError:
    APPLICATIONINSIGHTS_AVAILABLE = False

from ..logger_options import GCLoggerOptions

if TYPE_CHECKING:
    from ..operation_context import OperationContext

# Setup a local logger for this module
_logger = logging.getLogger(__name__)

# Storage path for OpenCensus telemetry buffer.
# Uses a dedicated directory to avoid conflicts when /tmp is cleaned up by applications.
OPENCENSUS_STORAGE_PATH = os.environ.get(
    "OPENCENSUS_STORAGE_PATH", "/var/tmp/opencensus"
)


def _extract_instrumentation_key(connection_string: Optional[str]) -> Optional[str]:
    if not connection_string:
        return None
    s = connection_string.strip()
    m = re.search(r"InstrumentationKey\s*=\s*([0-9a-fA-F-]{8,})", s)
    if m:
        return m.group(1)
    if re.match(r"^[0-9a-fA-F-]{36}$", s):
        return s
    return None

def _format_duration_string(duration_ms: float) -> str:
    if duration_ms is None or duration_ms < 0:
        duration_ms = 0
    total_ms = int(round(duration_ms))
    millis = total_ms % 1000
    total_seconds = total_ms // 1000
    seconds = total_seconds % 60
    minutes = (total_seconds // 60) % 60
    hours = (total_seconds // 3600) % 24
    days = total_seconds // 86400
    if days > 0:
        return "%d.%02d:%02d:%02d.%03d" % (days, hours, minutes, seconds, millis)
    return "%02d:%02d:%02d.%03d" % (hours, minutes, seconds, millis)


def _utc_iso(dt) -> str:
    iso = dt.isoformat()
    if not iso.endswith("Z") and "+" not in iso[10:] and "-" not in iso[10:]:
        iso = iso + "Z"
    return iso


class AppInsightsHandler:
    """Handles integration with Azure Application Insights."""

    def __init__(self, options: GCLoggerOptions):
        """
        Initialize AppInsights handler with given options.

        Args:
            options: Configuration options for the logger
        """
        self.options = options
        self.connection_string = self._get_connection_string()
        self.tracer = None

        self._instrumentation_key: Optional[str] = None
        self._telemetry_channel = None
        if self.connection_string and APPLICATIONINSIGHTS_AVAILABLE:
            self._instrumentation_key = _extract_instrumentation_key(
                self.connection_string
            )
            if self._instrumentation_key:
                try:
                    self._telemetry_channel = _AITelemetryChannel(
                        queue=_AIAsyncQueue(_AIAsyncSender())
                    )
                except Exception as e:
                    _logger.warning(
                        f"Failed to set up applicationinsights TelemetryChannel: {str(e)}"
                    )
                    self._telemetry_channel = None

        if self.connection_string and OPENCENSUS_AVAILABLE:
            # Initialize tracer
            try:
                self.tracer = Tracer(
                    exporter=AzureExporter(
                        connection_string=self.connection_string,
                        export_interval=self.options.app_insights_export_interval,
                        max_batch_size=self.options.app_insights_buffer_size,
                        storage_path=OPENCENSUS_STORAGE_PATH,
                    ),
                    sampler=AlwaysOnSampler(),
                )
            except Exception as e:
                _logger.error(f"Failed to initialize Azure Tracer: {str(e)}")

    def _get_connection_string(self) -> Optional[str]:
        """
        Get AppInsights connection string from options or environment.

        Returns:
            Connection string or None if not available
        """
        if self.options.use_app_insights_from_env:
            conn_str = os.environ.get(self.options.app_insights_env_var)
        else:
            conn_str = self.options.app_insights_connection_string
            
        # Python SDK seems to hate trailing semicolons :)
        # So we need to patch it
        if conn_str:
            conn_str = conn_str.strip().strip('"').strip("'")
            while conn_str.endswith(';'):
                conn_str = conn_str[:-1]
                
            os.environ["APPLICATIONINSIGHTS_CONNECTION_STRING"] = conn_str
                
        return conn_str

    def create_handler(self) -> Optional[logging.Handler]:
        """
        Create Azure Log Handler for the Python logging system.

        Returns:
            Configured logging handler or None if AppInsights is unavailable
        """
        if not self.connection_string or not OPENCENSUS_AVAILABLE:
            # Fallback to a console handler when AppInsights not available
            return None

        try:
            # Create handler with configured buffer size and export interval
            handler = AzureLogHandler(
                connection_string=self.connection_string,
                export_interval=self.options.app_insights_export_interval,
                max_batch_size=self.options.app_insights_buffer_size,
                storage_path=OPENCENSUS_STORAGE_PATH,
            )

            # Try to add custom properties processor if supported
            try:
                handler.add_processor(self._add_custom_properties)
            except AttributeError:
                # If add_processor is not available, we'll use a different approach
                # Wrap the handler with a filter that adds properties
                handler.addFilter(self._filter_add_properties)

            return handler
        except Exception as e:
            _logger.error(f"Failed to create AzureLogHandler: {str(e)}")
            return None

    def _filter_add_properties(self, record: logging.LogRecord) -> bool:
        """
        Filter that adds custom properties to the log record.

        Args:
            record: Log record to enhance

        Returns:
            True to continue processing the log record
        """
        # Create custom properties dict if not exists
        if not hasattr(record, "custom_properties"):
            record.custom_properties = {}

        # Ensure custom_dimensions exists for direct AppInsights mapping
        if not hasattr(record, "custom_dimensions"):
            record.custom_dimensions = {}

        # Add standard custom dimensions
        self._add_custom_properties_to_dict(record, record.custom_properties)

        # Add same properties to custom_dimensions for AppInsights
        self._add_custom_properties_to_dict(record, record.custom_dimensions)

        # Set OpenCensus telemetry correlation fields for Application Insights
        if hasattr(record, "operation_id") and record.operation_id:
            # Set the trace ID that OpenCensus/Application Insights recognizes
            # All logs in hierarchy should have the same traceId
            record.traceId = record.operation_id
            record.spanId = getattr(record, "span_id", "0000000000000000")

            # Set operation context for Application Insights
            if not hasattr(record, "operation"):
                record.operation = {}
            record.operation["id"] = record.operation_id
            record.operation["name"] = getattr(record, "operation_name", "Unknown")

            # Set parent operation ID if available
            # This should be the span_id of the parent operation
            if hasattr(record, "parent_operation_id") and record.parent_operation_id:
                record.operation["parentId"] = record.parent_operation_id

        return True

    def _add_custom_properties(
        self, record: logging.LogRecord, properties: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Add custom properties to the log record.

        Args:
            record: Log record to enhance
            properties: Dictionary to add properties to

        Returns:
            The enhanced properties dictionary
        """
        self._add_custom_properties_to_dict(record, properties)

        # Ensure we have custom_dimensions for direct AppInsights mapping
        if not hasattr(record, "custom_dimensions"):
            record.custom_dimensions = {}

        # Copy properties to custom_dimensions
        for key, value in properties.items():
            record.custom_dimensions[key] = value

        # Set OpenCensus telemetry correlation fields for Application Insights
        if hasattr(record, "operation_id") and record.operation_id:
            # Set the trace ID that OpenCensus/Application Insights recognizes
            # All logs in hierarchy should have the same traceId
            record.traceId = record.operation_id
            record.spanId = getattr(record, "span_id", "0000000000000000")

            # Set operation context for Application Insights
            if not hasattr(record, "operation"):
                record.operation = {}
            record.operation["id"] = record.operation_id
            record.operation["name"] = getattr(record, "operation_name", "Unknown")

            # Set parent operation ID if available
            # This should be the span_id of the parent operation
            if hasattr(record, "parent_operation_id") and record.parent_operation_id:
                record.operation["parentId"] = record.parent_operation_id

        return properties

    def _add_custom_properties_to_dict(
        self, record: logging.LogRecord, properties: Dict[str, Any]
    ) -> None:
        """
        Helper method to add properties to any dict.

        Args:
            record: Log record containing context information
            properties: Dictionary to add properties to
        """
        # Add standard custom dimensions
        for key, value in self.options.custom_dimensions.items():
            properties[key] = value

        # Add environment
        properties["environment"] = self.options.environment

        # Add service identifiers - new format properties
        properties["ServiceName"] = self.options.service_name
        properties["AppServiceName"] = self.options.app_service_name

        # Add method info
        if hasattr(record, "source_class"):
            properties["ClassName"] = record.source_class
        else:
            properties["ClassName"] = self.options.default_class_name

        if hasattr(record, "source_function"):
            properties["MethodName"] = record.source_function
        else:
            properties["MethodName"] = "unknown"

        # Add operation context if available. Canonical key per
        # observability-contract.md is 'TraceId' (PascalCase); legacy
        # snake_case aliases are emitted alongside it for one release so
        # that existing dashboards keep working during the migration.
        if hasattr(record, "operation_id"):
            properties["TraceId"] = record.operation_id
            properties["operation_id"] = record.operation_id
            properties["operation_name"] = record.operation_name

            if hasattr(record, "parent_operation_id") and record.parent_operation_id:
                properties["parent_operation_id"] = record.parent_operation_id

        # Add properties from operation_context if available
        if hasattr(record, "operation_context") and record.operation_context:
            for key, value in record.operation_context.properties.items():
                properties[key] = value

        # Add source context if enabled
        if self.options.include_source_context and hasattr(record, "source_module"):
            properties["source_module"] = record.source_module
            properties["source_function"] = record.source_function
            if hasattr(record, "source_file"):
                properties["source_file"] = record.source_file
                properties["source_line"] = record.source_line

    def start_operation_span(
        self, operation_name: str, operation_id: str, parent_id: Optional[str] = None
    ) -> Any:
        """
        Start a new trace span for an operation.

        Args:
            operation_name: Name of the operation to trace
            operation_id: Unique identifier for the operation
            parent_id: Optional parent operation ID for nested operations

        Returns:
            Span object or None if tracing is unavailable
        """
        if not self.tracer:
            return None

        # Create a span context if we have a parent
        span_context = None
        if parent_id:
            span_context = SpanContext(trace_id=parent_id)

        # Start a span for this operation
        try:
            return self.tracer.span(name=operation_name, span_context=span_context)
        except Exception as e:
            _logger.error(f"Failed to start operation span: {str(e)}")
            return None


    def track_request_telemetry(self, operation: "OperationContext") -> None:
        if not self._telemetry_channel or not self._instrumentation_key:
            return
        if operation is None:
            return

        try:
            request_data = _AIRequestData()
            request_data.id = operation.span_id
            request_data.name = operation.operation_name
            request_data.duration = _format_duration_string(operation.duration_ms or 0)
            request_data.response_code = str(
                operation.response_code or ("500" if operation.failed else "200")
            )
            request_data.success = not operation.failed
            request_data.url = ""

            properties: Dict[str, str] = {
                "ServiceName": self.options.service_name,
                "AppServiceName": self.options.app_service_name,
                "TraceId": operation.operation_id,
            }
            if operation.properties:
                for k, v in operation.properties.items():
                    properties[str(k)] = str(v)
            request_data.properties = properties

            envelope = _AIEnvelope()
            envelope.name = _AIRequestData.ENVELOPE_TYPE_NAME
            envelope.time = _utc_iso(operation.start_time)
            envelope.ikey = self._instrumentation_key

            tags: Dict[str, str] = {
                "ai.operation.id": operation.operation_id,
                "ai.operation.name": operation.operation_name,
                "ai.cloud.role": self.options.service_name,
                "ai.cloud.roleInstance": self.options.app_service_name,
            }
            if operation.parent_operation_id:
                tags["ai.operation.parentId"] = operation.parent_operation_id
            envelope.tags = tags

            data = _AIData()
            data.base_type = _AIRequestData.DATA_TYPE_NAME
            data.base_data = request_data
            envelope.data = data

            self._telemetry_channel.queue.put(envelope)
        except Exception as e:
            _logger.warning(f"Failed to emit RequestTelemetry: {str(e)}")

    def flush(self) -> None:
        try:
            if self._telemetry_channel is not None:
                self._telemetry_channel.flush()
        except Exception as e:
            _logger.debug(f"flush(): TelemetryChannel.flush failed: {e}")

    def shutdown(self) -> None:
        try:
            if self._telemetry_channel is not None:
                self._telemetry_channel.flush()
                stopper = getattr(self._telemetry_channel.queue.sender, "stop", None) \
                    or getattr(self._telemetry_channel.queue.sender, "close", None)
                if callable(stopper):
                    stopper()
        except Exception as e:
            _logger.debug(f"shutdown(): TelemetryChannel teardown failed: {e}")
        finally:
            self._telemetry_channel = None
