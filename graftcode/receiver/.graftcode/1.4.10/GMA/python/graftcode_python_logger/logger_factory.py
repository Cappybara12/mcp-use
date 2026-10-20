import asyncio
import contextvars
import logging
import os
import sys
import uuid
from contextlib import contextmanager
from functools import wraps
from typing import Any, Callable, Dict, Generator, Optional, TypeVar, cast

from .logger_options import GCLoggerOptions, LogLevel
from .operation_context import OperationContext
from .session_scope import DEFAULT_DRAIN_TIMEOUT_SECONDS, SessionScope
from .telemetry.app_insights_handler import AppInsightsHandler
from .telemetry.context_initializer import add_operation_context
from .telemetry.source_context import add_source_context

# Context variable to store operation context stack
# This works correctly with both sync and async code
# We use a list to maintain a stack of operations for proper nesting
_operation_context_stack_var = contextvars.ContextVar(
    "operation_context_stack", default=[]
)

# Definition of generic variable T before it is used
T = TypeVar("T", bound=Callable[..., Any])


class GCLoggerFactory:
    """
    Main factory for creating and configuring loggers in your application.

    This class is the central entry point for all logging activities.
    It helps you:
    1. Configure logging settings in a consistent way
    2. Create loggers for different parts of your application
    3. Track operations and their relationships (parent-child)
    4. Integrate with Application Insights for centralized log analysis

    Basic usage:
    - Initialize once at application startup
    - Get loggers from it to use throughout your application
    - Use the provided context managers to track operations

    This class follows the Singleton pattern, so you'll always get the same
    instance no matter where you create it in your code.
    """

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(GCLoggerFactory, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, options: Optional[GCLoggerOptions] = None):
        if self._initialized:
            return

        if options is None or not options.service_name:
            raise ValueError(
                "GCLoggerFactory requires GCLoggerOptions with a non-empty "
                "service_name. Call GCLoggerFactory.initialize(...) or "
                ".initialize_simple(service_name=...) from your Bootstrap "
                "type; see graftcode-protocol/docs/observability-contract.md."
            )

        if not options.app_service_name:
            options.app_service_name = (
                os.environ.get("WEBSITE_SITE_NAME") or options.service_name
            )

        self.options = options
        self._app_insights = AppInsightsHandler(self.options)
        self._global_trace_id = uuid.uuid4().hex
        self._initialize_logger()
        self._initialized = True

    def _initialize_logger(self) -> None:
        """Initialize the Python logging system."""
        # Create a root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(self.options.minimum_log_level)

        # Remove existing handlers
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        # Add console handler
        if self.options.enable_structured_console_logging:
            # New format: "{Timestamp} - {Level} - {ServiceName} -
            # {ClassName} -
            # {MethodName} - Message: {Message}"
            console_format = (
                "%(asctime)s - %(levelname)s - %(service_name)s - "
                "%(class_name)s - %(method_name)s - Message: %(message)s"
            )

            if self.options.include_scopes:
                console_format += " || Context: %(context)s"

            # Create a custom formatter class that adds required properties
            class CustomFormatter(logging.Formatter):
                def __init__(self, fmt=None, *args, **kwargs):
                    super().__init__(fmt, *args, **kwargs)
                    self.service_name = self.default_service_name = None
                    self.app_service_name = self.default_class_name = None

                def set_defaults(self, options):
                    self.default_service_name = options.service_name
                    self.default_app_service_name = options.app_service_name
                    self.default_class_name = options.default_class_name

                def format(self, record):
                    # Set service_name if not present
                    if not hasattr(record, "service_name"):
                        record.service_name = self.default_service_name

                    # Set app_service_name if not present
                    if not hasattr(record, "app_service_name"):
                        record.app_service_name = self.default_app_service_name

                    # Map source context to the new format fields
                    if hasattr(record, "source_class"):
                        record.class_name = record.source_class
                    else:
                        record.class_name = self.default_class_name

                    if hasattr(record, "source_function"):
                        record.method_name = record.source_function
                    else:
                        record.method_name = "unknown"

                    if not hasattr(record, "context"):
                        record.context = "no-context"

                    # Standard ISO format for timestamp - compatible
                    # with
                    # time.strftime
                    self.datefmt = "%Y-%m-%dT%H:%M:%SZ"

                    return super().format(record)

            formatter = CustomFormatter(console_format)
            formatter.set_defaults(self.options)

            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            root_logger.addHandler(console_handler)

        # Add AppInsights handler if connection string is available
        app_insights_handler = self._app_insights.create_handler()
        if app_insights_handler:
            root_logger.addHandler(app_insights_handler)

        # Apply category filters
        for category, level in self.options.category_filters.items():
            category_logger = logging.getLogger(category)
            category_logger.setLevel(level)

    @classmethod
    def initialize(cls, options: GCLoggerOptions) -> "GCLoggerFactory":
        """Initialize the logger factory with custom options.

        Semantics (aligned with observability-contract.md):

        - ``options.service_name`` is REQUIRED; an empty value raises
          ``ValueError``. This mirrors the strict ``Init(serviceName)``
          contract used by the .NET/JVM/Node loggers.
        - A subsequent ``initialize`` with a DIFFERENT ``service_name``
          is last-write-wins and logs a ``WARNING`` on ``stderr`` so the
          offending caller can be tracked down (this is the root cause
          trap for the cross-assembly ServiceName hijack bug).
        - Calling again with the SAME ``service_name`` is a no-op warm-up
          that simply refreshes dependent options.
        - ``app_service_name`` falls back to ``WEBSITE_SITE_NAME`` (Azure)
          and then to ``service_name`` when left blank.
        """
        if not options.service_name:
            raise ValueError(
                "GCLoggerOptions.service_name is required; "
                "see graftcode-protocol/docs/observability-contract.md."
            )

        if not options.app_service_name:
            options.app_service_name = (
                os.environ.get("WEBSITE_SITE_NAME") or options.service_name
            )

        if cls._instance is None:
            return cls(options)

        previous = getattr(cls._instance, "options", None)
        if previous is not None and previous.service_name != options.service_name:
            sys.stderr.write(
                "[GraftCodeLogger][WARN] ServiceName overwritten: "
                f"'{previous.service_name}' -> '{options.service_name}'. "
                "Last-write-wins. Only Bootstrap types should call Init; "
                "see observability-contract.md.\n"
            )

        cls._instance.options = options
        cls._instance._app_insights = AppInsightsHandler(options)
        cls._instance._initialize_logger()

        return cls._instance

    @classmethod
    def ensure_initialized(cls, service_name: str) -> "GCLoggerFactory":
        """Strict variant of :meth:`initialize` for defensive bootstraps.

        Returns the existing instance if ``service_name`` matches; raises
        :class:`RuntimeError` on mismatch. Use this from Bootstrap types
        that only want to warm up the singleton without silently
        clobbering an earlier correct initialization.
        """
        if cls._instance is None:
            return cls.initialize(GCLoggerOptions(service_name=service_name))

        current = cls._instance.options.service_name
        if current != service_name:
            raise RuntimeError(
                "GCLoggerFactory already initialized with "
                f"ServiceName='{current}', refused to overwrite with "
                f"'{service_name}'."
            )
        return cls._instance

    @classmethod
    def start_session(
        cls,
        service_name: Optional[str] = None,
        drain_timeout: float = DEFAULT_DRAIN_TIMEOUT_SECONDS,
        options: Optional[GCLoggerOptions] = None,
    ) -> SessionScope:
        if options is not None:
            cls.initialize(options)
        elif service_name:
            cls.initialize_simple(service_name)
        elif cls._instance is None:
            raise RuntimeError(
                "start_session requires a service_name (or pre-built options) "
                "when the logger factory has not been initialized yet."
            )

        return SessionScope(cls._instance, drain_timeout=drain_timeout)

    @classmethod
    def flush(cls) -> None:
        instance = cls._instance
        if instance is None:
            return
        try:
            instance._app_insights.flush()
        except Exception:
            pass

    @classmethod
    def shutdown(cls) -> None:
        instance = cls._instance
        if instance is None:
            return
        try:
            instance._app_insights.shutdown()
        except Exception:
            pass

    @classmethod
    def initialize_simple(
        cls, service_name: str, min_log_level: LogLevel = LogLevel.INFO
    ) -> "GCLoggerFactory":
        """
        Initialize with simplified options.

        Args:
            service_name: Name of the service for logs
            min_log_level: Minimum log level to capture

        Returns:
            Initialized GCLoggerFactory instance
        """
        if not service_name:
            raise ValueError("service_name is required.")

        options = GCLoggerOptions(
            service_name=service_name, minimum_log_level=min_log_level
        )
        return cls.initialize(options)

    @classmethod
    def get_logger(cls, name: Optional[str] = None) -> logging.Logger:
        """Get a logger instance.

        Requires :meth:`initialize` (or :meth:`ensure_initialized`) to
        have been called already - mirroring the contract that every
        stack enforces. Calling ``get_logger`` before ``initialize`` is
        a programming error.
        """
        if cls._instance is None:
            raise RuntimeError(
                "GCLoggerFactory.get_logger called before initialize(); "
                "initialize the factory with a ServiceName first."
            )

        logger = logging.getLogger(name)

        # Add filter to enhance log records
        for handler in logger.handlers + logging.getLogger().handlers:
            handler.addFilter(cls._enhance_log_record)

        return logger

    @staticmethod
    def _enhance_log_record(record: logging.LogRecord) -> bool:
        """Enhance log record with operation and source context."""
        # Add operation context
        operation = GCLoggerFactory.get_current_operation()
        add_operation_context(record, operation)

        # Add source context
        add_source_context(record)

        # Make sure the context attribute exists even if there is no operation
        if not hasattr(record, "context"):
            record.context = "no-context"

        return True

    @staticmethod
    def start_operation(
        operation_name: str,
        properties: Optional[Dict[str, str]] = None,
        operation_id: Optional[str] = None,
        parent_span_id: Optional[str] = None,
    ) -> OperationContext:
        """
        Begin tracking a new operation in your application.

        This creates a new operation with a unique ID and stores it in the
        current context. If there's already an active operation, this new
        operation will be linked to it as a child operation.

        Parameters:
            operation_name: A descriptive name for what this operation does
                           (e.g., "ProcessPayment")
            properties: Optional dictionary of additional information about
                       this operation (e.g., {"orderId": "12345"})
            operation_id: Optional external trace/operation ID to use instead
                         of auto-generating one. Useful for correlating logs
                         across services that share a single trace.
            parent_span_id: Optional 16-hex span ID of the caller's span,
                         typically propagated from an upstream service. When
                         supplied, the RequestTelemetry emitted for this
                         operation hangs off that span, so Application Insights
                         renders it as a sub-span in the end-to-end timeline.
                         Mirrors the .NET ``StartOperation(traceId,
                         parentSpanId, methodName)`` overload.

        Returns:
            A new OperationContext object that represents this operation

        Example:
            # Start tracking a new operation
            operation = GCLoggerFactory.start_operation(
                "ProcessOrder", {"order_id": "12345"}
            )

            # Do some work...

            # End the operation
            GCLoggerFactory.end_operation(logger)
        """
        # Get parent operation if exists
        current_op = GCLoggerFactory.get_current_operation()

        # Create new operation context
        operation = OperationContext(
            operation_name=operation_name,
            properties=properties or {},
        )

        incoming_parent = GCLoggerFactory._normalize_span_id(parent_span_id)

        if current_op:
            # Child operation: inherit the root operation_id
            operation.operation_id = current_op.operation_id
            operation.parent_operation_id = incoming_parent or current_op.span_id
        elif operation_id:
            # Root operation with externally supplied trace ID
            operation.operation_id = operation_id
            operation.parent_operation_id = incoming_parent
        else:
            instance = GCLoggerFactory._instance
            if instance is not None:
                operation.operation_id = instance._global_trace_id
            operation.parent_operation_id = incoming_parent

        stack = _operation_context_stack_var.get().copy()
        stack.append(operation)
        _operation_context_stack_var.set(stack)

        return operation

    @staticmethod
    def _normalize_span_id(span_id: Optional[str]) -> Optional[str]:
        if not span_id:
            return None
        candidate = span_id.strip().lower()
        if len(candidate) != 16 or candidate == "0000000000000000":
            return None
        if any(c not in "0123456789abcdef" for c in candidate):
            return None
        return candidate

    @staticmethod
    def get_current_operation() -> Optional[OperationContext]:
        """Get the current operation context."""
        stack = _operation_context_stack_var.get()
        return stack[-1] if stack else None

    @classmethod
    def get_trace_id(cls) -> str:
        if cls._instance is None:
            raise RuntimeError(
                "GCLoggerFactory.get_trace_id called before initialize(); "
                "initialize the factory with a ServiceName first."
            )

        op = cls.get_current_operation()
        if op is not None and op.operation_id:
            return op.operation_id
        return cls._instance._global_trace_id

    @classmethod
    def get_span_id(cls) -> Optional[str]:
        op = cls.get_current_operation()
        return op.span_id if op is not None else None

    @staticmethod
    def end_operation(
        logger: Optional[logging.Logger] = None, log_completion: bool = True
    ) -> Optional[OperationContext]:
        operation = GCLoggerFactory.get_current_operation()
        if not operation:
            return None

        # End the operation
        operation.end()

        instance = GCLoggerFactory._instance
        if instance is not None:
            try:
                instance._app_insights.track_request_telemetry(operation)
            except Exception:
                pass

        # Log completion if requested
        if log_completion and logger:
            logger.info(
                f"Operation {operation.operation_name} completed in "
                f"{operation.duration_ms:.2f}ms",
                extra={"operation_context": operation},
            )

        # Remove current operation from stack and restore parent
        stack = _operation_context_stack_var.get().copy()
        if stack and stack[-1] == operation:
            stack.pop()
        _operation_context_stack_var.set(stack)

        return operation

    @staticmethod
    @contextmanager
    def track_operation(
        logger: logging.Logger,
        operation_name: str,
        properties: Optional[Dict[str, str]] = None,
        operation_id: Optional[str] = None,
        parent_span_id: Optional[str] = None,
    ) -> Generator[OperationContext, None, None]:
        """
        Track an operation using a context manager (with statement).

        This is the easiest way to track operations. It automatically:
        1. Starts a new operation when entering the with block
        2. Ends the operation when exiting the with block
        3. Calculates and logs the duration

        Parameters:
            logger: The logger to use for operation completion messages
            operation_name: A descriptive name for this operation
            properties: Optional dictionary of additional information
            operation_id: Optional external trace/operation ID to use instead
                         of auto-generating one. Useful for correlating logs
                         across services that share a single trace.
            parent_span_id: Optional 16-hex span ID of the caller's span,
                         propagated from an upstream service so this operation
                         renders as a sub-span in the Application Insights
                         timeline.

        Example:
            # Get a logger for your module
            logger = GCLoggerFactory.get_logger(__name__)

            # Track an operation with an external trace ID
            with GCLoggerFactory.track_operation(
                logger, "ProcessOrder", {"order_id": "12345"},
                operation_id="abc-123"
            ) as op:
                # The operation is now being tracked
                logger.info("Starting to process the order")

                # Do some work...

                logger.info("Order processed successfully")
                # When the with block ends, the operation is automatically
                # completed and its duration is logged
        """
        operation = GCLoggerFactory.start_operation(
            operation_name,
            properties,
            operation_id=operation_id,
            parent_span_id=parent_span_id,
        )
        try:
            yield operation
        except Exception:
            operation.mark_failed()
            raise
        finally:
            GCLoggerFactory.end_operation(logger)

    @staticmethod
    @contextmanager
    def track_child_operation(
        logger: logging.Logger,
        child_operation_name: str,
        properties: Optional[Dict[str, str]] = None,
        operation_id: Optional[str] = None,
        parent_span_id: Optional[str] = None,
    ) -> Generator[OperationContext, None, None]:
        """
        Track a nested operation that's part of a larger operation.

        Use this when you need to track a subtask or component of a larger
        operation. This creates a parent-child relationship in your logs,
        which helps understand the hierarchy and flow of operations.

        Parameters:
            logger: The logger to use for operation completion messages
            child_operation_name: A descriptive name for this child operation
            properties: Optional dictionary of additional information
            operation_id: Optional external trace/operation ID to use instead
                         of auto-generating one. Useful for correlating logs
                         across services that share a single trace.

        Example:
            # Parent operation
            with GCLoggerFactory.track_operation(logger, "ProcessOrder") as op:
                logger.info("Starting to process the order")

                # Child operation
                with GCLoggerFactory.track_child_operation(
                    logger, "ValidatePayment", {"payment_type": "credit_card"}
                ):
                    logger.info("Validating payment details")
                    # Do payment validation...

                # Another child operation
                with GCLoggerFactory.track_child_operation(
                    logger, "UpdateInventory"
                ):
                    # Do inventory updates...
        """
        child = GCLoggerFactory.start_operation(
            child_operation_name,
            properties,
            operation_id=operation_id,
            parent_span_id=parent_span_id,
        )
        try:
            yield child
        except Exception:
            child.mark_failed()
            raise
        finally:
            GCLoggerFactory.end_operation(logger)
            # Parent operation should already be restored by end_operation
            # since we maintain a proper stack now

    # Decorator versions
    @staticmethod
    def operation(
        operation_name: str, properties: Optional[Dict[str, str]] = None
    ) -> Callable[[T], T]:
        """
        Decorator to automatically track an operation around a function.

        This decorator wraps your function to start an operation when the
        function is called and end it when the function completes.
        Works with both regular functions and async functions.

        Parameters:
            operation_name: A descriptive name for this operation
            properties: Optional dictionary of additional information

        Example:
            # Track an operation for a regular function
            @GCLoggerFactory.operation("ProcessOrder")
            def process_order(order_id):
                # This function is automatically wrapped in an operation
                # Do work...
                return result

            # Track an operation for an async function
            @GCLoggerFactory.operation("FetchUserData")
            async def fetch_user_data(user_id):
                # This async function is automatically wrapped in an operation
                # Do async work...
                return user_data
        """

        def decorator(func: T) -> T:
            @wraps(func)
            def wrapper(*args, **kwargs):
                logger_name = func.__module__
                logger = GCLoggerFactory().get_logger(logger_name)

                with GCLoggerFactory.track_operation(
                    logger, operation_name, properties
                ):
                    return func(*args, **kwargs)

            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                logger_name = func.__module__
                logger = GCLoggerFactory().get_logger(logger_name)

                with GCLoggerFactory.track_operation(
                    logger, operation_name, properties
                ):
                    return await func(*args, **kwargs)

            if asyncio.iscoroutinefunction(func):
                return cast(T, async_wrapper)
            else:
                return cast(T, wrapper)

        return decorator
