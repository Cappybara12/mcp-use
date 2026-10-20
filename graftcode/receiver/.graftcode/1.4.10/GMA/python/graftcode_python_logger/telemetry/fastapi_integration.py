"""
FastAPI integration module for graftcode_python_logger.

This module provides middleware and helpers for integrating graftcode_python_logger
with FastAPI applications, enabling hierarchical operation tracking.

It allows you to:
1. Automatically track all HTTP requests as REQUEST telemetry in Application Insights
2. Create parent-child relationships between operations
3. Measure request durations and capture request attributes
4. Track individual endpoint executions as child operations
"""

import contextvars
import time
from typing import Any, Callable, Dict, List, Optional

# Try importing FastAPI, but don't fail if it's not available
# This allows the module to be imported even if FastAPI isn't installed
try:
    from fastapi import FastAPI, Request

    _has_fastapi = True
except ImportError:
    _has_fastapi = False

    # Create stub types to avoid type errors
    class FastAPI:
        """Stub FastAPI class when real FastAPI is not available."""

        def middleware(self, middleware_type):
            def decorator(func):
                return func

            return decorator

    class Request:
        """Stub Request class when real FastAPI is not available."""

        pass


# Try importing OpenCensus for REQUEST tracking
try:
    _has_opencensus = True
except ImportError:
    _has_opencensus = False


class LoggingMiddleware:
    """
    Middleware for tracking HTTP requests as parent operations.

    This middleware automatically captures each incoming HTTP request as a
    tracked operation, recording metrics like duration and status code.

    Each request becomes a parent operation that can have child operations
    created by endpoint handlers, allowing for a hierarchical view of
    request processing.
    """

    def __init__(
        self,
        app: "FastAPI",
        logger_name: Optional[str] = None,
        exclude_paths: Optional[List[str]] = None,
        include_paths: Optional[List[str]] = None,
    ):
        """
        Initialize the logging middleware.

        Args:
            app: The FastAPI application instance to attach middleware to
            logger_name: Optional logger name (defaults to module name)
                         Used to categorize logs from this middleware
            exclude_paths: Optional list of paths to exclude from logging
                          (ignored if include_paths is provided)
            include_paths: Optional list of paths to include in logging
                          (takes precedence over exclude_paths)
        """
        if not _has_fastapi:
            raise ImportError(
                "FastAPI is required for LoggingMiddleware. "
                "Please install it with 'pip install fastapi'."
            )

        self.app = app
        self.logger_name = logger_name or __name__
        self.exclude_paths = exclude_paths or []
        self.include_paths = include_paths

        # Import inside the method to avoid circular imports
        # (GCLoggerFactory might import from fastapi_integration)
        from ..logger_factory import GCLoggerFactory

        self.logger = GCLoggerFactory.get_logger(self.logger_name)
        self.logger_factory = GCLoggerFactory

    def _should_log_path(self, path: str) -> bool:
        """
        Determine if a path should be logged based on include/exclude rules.

        Args:
            path: The request path to check

        Returns:
            bool: True if the path should be logged, False otherwise
        """
        # If include_paths is specified, only log paths in that list
        if self.include_paths is not None:
            return path in self.include_paths

        # Otherwise, use exclude_paths logic (log all except excluded)
        return path not in self.exclude_paths

    def __call__(self):
        """
        Register the middleware with the FastAPI application.

        This method creates and attaches an HTTP middleware to the FastAPI app
        that will track each request as an operation.

        Returns:
            The FastAPI application with middleware attached
        """

        @self.app.middleware("http")
        async def logging_middleware(request: Request, call_next: Callable):
            """
            Track each HTTP request as a parent operation.

            This function is called for every request and:
            1. Creates a parent operation with the request details
            2. Logs the start of request processing
            3. Measures the request duration
            4. Logs the completion status and duration
            5. Captures any exceptions that occur during processing
            """
            # Check if this path should be excluded from logging
            path = request.url.path
            if not self._should_log_path(path):
                # Skip logging for excluded paths
                return await call_next(request)

            # Copy context to ensure proper isolation between requests
            ctx = contextvars.copy_context()

            async def process_request():
                method = request.method
                operation_name = f"{method} {path}"
                client_host = request.client.host if request.client else "unknown"

                # Create attributes dictionary with request details
                attributes = {
                    "path": path,
                    "method": method,
                    "client_host": client_host,
                    "request_type": "HTTP_REQUEST",
                }

                # If OpenCensus is available, use it for REQUEST tracking
                if _has_opencensus:
                    # Get connection string from logger options
                    connection_string = None
                    if (
                        hasattr(self.logger_factory, "_instance")
                        and self.logger_factory._instance
                    ):
                        app_insights = getattr(
                            self.logger_factory._instance, "_app_insights", None
                        )
                        if app_insights:
                            connection_string = app_insights.connection_string

                    if connection_string:
                        # Create OpenCensus tracer for REQUEST telemetry
                        from opencensus.ext.azure.trace_exporter import AzureExporter
                        from opencensus.trace.samplers import ProbabilitySampler
                        from opencensus.trace.tracer import Tracer

                        tracer = Tracer(
                            exporter=AzureExporter(
                                connection_string=connection_string,
                                storage_path=None,  # Disable file buffering for containerized environments
                            ),
                            sampler=ProbabilitySampler(1.0),
                        )

                        # Start REQUEST span - this will appear as REQUEST
                        # in App Insights
                        with tracer.span(name=operation_name) as span:
                            # Add request attributes to the span
                            span.add_attribute("http.method", method)
                            span.add_attribute("http.url", str(request.url))
                            span.add_attribute("http.scheme", request.url.scheme)
                            span.add_attribute(
                                "http.host", request.url.hostname or "unknown"
                            )
                            span.add_attribute("http.target", path)

                            # Start our internal operation for child operations
                            self.logger_factory.start_operation(
                                operation_name, attributes
                            )

                            try:
                                self.logger.info(
                                    f"Processing {method} request to {path}"
                                )

                                # Process the request and measure duration
                                start_time = time.time()
                                try:
                                    response = await call_next(request)
                                    duration = time.time() - start_time
                                    status_code = response.status_code

                                    # Add response attributes to span
                                    span.add_attribute("http.status_code", status_code)
                                    span.add_attribute(
                                        "http.response_size",
                                        response.headers.get("content-length", "0"),
                                    )

                                    # Log the successful completion
                                    self.logger.info(
                                        f"Request completed with status "
                                        f"{status_code} in {duration:.3f}s"
                                    )
                                    return response
                                except Exception as exc:
                                    duration = time.time() - start_time
                                    # Mark span as error
                                    span.add_attribute("error", True)
                                    span.add_attribute("error.message", str(exc))

                                    # Create error message with duration info
                                    error_msg = (
                                        f"Request failed after {duration:.3f}s: "
                                        f"{str(exc)}"
                                    )
                                    self.logger.error(error_msg, exception=exc)
                                    raise
                            finally:
                                # End our internal operation
                                self.logger_factory.end_operation(self.logger)
                    else:
                        # Fallback to our original approach if no
                        # connection string
                        return await self._process_request_fallback(request, call_next)
                else:
                    # Fallback to our original approach if OpenCensus
                    # not available
                    return await self._process_request_fallback(request, call_next)

            # Run the request processing in the copied context
            return await ctx.run(process_request)

        return self.app

    async def _process_request_fallback(self, request, call_next):
        """Fallback method when OpenCensus is not available."""
        method = request.method
        path = request.url.path

        # Check if this path should be excluded from logging
        if not self._should_log_path(path):
            # Skip logging for excluded paths
            return await call_next(request)

        operation_name = f"{method} {path}"
        client_host = request.client.host if request.client else "unknown"

        # Create attributes dictionary with request details
        attributes = {
            "path": path,
            "method": method,
            "client_host": client_host,
            "request_type": "HTTP_REQUEST",
        }

        # Start the main HTTP request operation (this will be the parent)
        self.logger_factory.start_operation(operation_name, attributes)

        try:
            self.logger.info(f"Processing {method} request to {path}")

            # Process the request and measure duration
            start_time = time.time()
            try:
                response = await call_next(request)
                duration = time.time() - start_time
                status_code = response.status_code

                # Log the successful completion of the request
                self.logger.info(
                    f"Request completed with status {status_code} "
                    f"in {duration:.3f}s"
                )
                return response
            except Exception as exc:
                duration = time.time() - start_time
                # Create error message with duration information
                error_msg = f"Request failed after {duration:.3f}s: {str(exc)}"
                self.logger.error(error_msg, exception=exc)
                raise
        finally:
            # End the main HTTP request operation
            self.logger_factory.end_operation(self.logger)


def setup_request_logging(
    app: "FastAPI",
    logger_name: Optional[str] = None,
    exclude_paths: Optional[List[str]] = None,
    include_paths: Optional[List[str]] = None,
) -> "FastAPI":
    """
    Setup request logging for a FastAPI application.

    This is a convenience function that creates and configures the
    LoggingMiddleware for your FastAPI application.

    Example:
        ```python
        from fastapi import FastAPI
        from graftcode_python_logger import setup_request_logging

        app = FastAPI()
        # Log only specific endpoints
        setup_request_logging(app, include_paths=["/api/v1/users", "/api/v1/orders"])

        # Or exclude specific endpoints (old behavior)
        setup_request_logging(app, exclude_paths=["/status", "/health"])

        @app.get("/")
        async def root():
            return {"message": "Hello World"}
        ```

    Args:
        app: The FastAPI application instance
        logger_name: Optional logger name (defaults to module name)
        exclude_paths: Optional list of paths to exclude from logging
                      (ignored if include_paths is provided)
        include_paths: Optional list of paths to include in logging
                      (takes precedence over exclude_paths)

    Returns:
        FastAPI: The configured FastAPI application
    """
    if not _has_fastapi:
        raise ImportError(
            "FastAPI is required for setup_request_logging. "
            "Please install it with 'pip install fastapi'."
        )

    middleware = LoggingMiddleware(app, logger_name, exclude_paths, include_paths)
    middleware()
    return app


def track_endpoint_operation(
    logger, operation_name: str, attributes: Optional[Dict[str, Any]] = None
):
    """
    Decorator for FastAPI endpoint functions to track them as child operations.

    Use this decorator on FastAPI endpoint methods to create child operations
    that will be nested under the parent HTTP request operation.

    This helps you track the hierarchical flow of operations through your
    application, from HTTP request to specific endpoint handlers.

    Example:
        ```python
        from fastapi import FastAPI, Depends
        from graftcode_python_logger import (
            GCLoggerFactory,
            setup_request_logging,
            track_endpoint_operation
        )

        app = FastAPI()
        setup_request_logging(app)
        logger = GCLoggerFactory.get_logger("my_api")

        @app.get("/items/{item_id}")
        @track_endpoint_operation(
            logger,
            "get_item",
            {"component": "items"}
        )
        async def get_item(item_id: int):
            # This will be tracked as a child operation
            # of the HTTP request
            return {"item_id": item_id}
        ```

    Args:
        logger: Logger instance to use for logging the operation
        operation_name: Name of the operation to track
        attributes: Optional attributes to add to the operation

    Returns:
        Callable: Decorator function that can be applied to FastAPI endpoints
    """
    # Import inside the function to avoid circular imports
    # This ensures that fastapi_integration can be imported from logger_factory
    # without causing import cycles
    from ..logger_factory import GCLoggerFactory

    def decorator(func):
        async def wrapper(*args, **kwargs):
            with GCLoggerFactory.track_child_operation(
                logger, operation_name, attributes
            ):
                logger.debug(f"Executing {operation_name}")
                return await func(*args, **kwargs)

        return wrapper

    return decorator
