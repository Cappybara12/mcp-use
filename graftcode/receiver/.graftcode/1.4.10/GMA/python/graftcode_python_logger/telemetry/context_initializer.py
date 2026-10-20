"""
Operation Context Initializer for Log Records.

This module provides functionality to enrich log records with operation context
information. It's a key part of the operation tracking system that allows logs
to be associated with specific operations (like HTTP requests or database queries)
and maintains parent-child relationships between operations.

When a log message is created during an operation, this module adds important
tracking information to the log record such as:
1. Operation ID - unique identifier for the current operation
2. Operation name - descriptive name of what's being done
3. Parent operation ID - for establishing hierarchical relationships
4. Custom properties - additional context about the operation

This enables features like:
- Tracing all logs from a specific operation
- Visualizing parent-child operation relationships
- Adding structured context to console and Application Insights logs
"""

import logging
from typing import Optional

from ..operation_context import OperationContext


def add_operation_context(
    record: logging.LogRecord, operation: Optional[OperationContext]
) -> None:
    """
    Add operation context information to the log record.

    This function enriches standard log records with operation tracking data,
    which helps correlate logs with specific operations in your application.
    If no operation is active, the function returns without modifying the record.

    How it works:
    1. Adds the entire operation_context object to the record
    2. Adds individual operation fields (ID, name, parent ID) for easy access
    3. Creates a formatted context string for console output

    Args:
        record: Log record to enhance with operation context
               This is a standard Python LogRecord object
        operation: Operation context to add, or None if no active operation
                  Contains tracking IDs and metadata about the current operation

    Example:
        When this function processes a log record during an API request operation:
        - record.operation_id might become "1621478354-abc123def456"
        - record.operation_name might become "GET /users"
        - record.context might become "op=GET /users, client_ip=192.168.1.1"

    Note:
        This function is typically called automatically by the logging system
        and not directly by application code.
    """
    if not operation:
        return

    # Add the entire operation_context to the record
    # This allows access to all operation details in log handlers
    record.operation_context = operation

    # Add operation information to the record as individual fields
    # This makes it easier for log handlers to access specific properties
    record.operation_id = operation.operation_id
    record.operation_name = operation.operation_name
    record.parent_operation_id = operation.parent_operation_id
    record.span_id = operation.span_id

    # Create context string for console output
    # This formats the operation context for human-readable display
    context_parts = [f"op={operation.operation_name}"]
    if operation.parent_operation_id:
        context_parts.append("child=True")

    # Add all custom properties from the operation
    # (except duration which may not be final yet)
    for key, value in operation.properties.items():
        if key != "duration_ms":  # Skip duration for active operations
            context_parts.append(f"{key}={value}")

    # Join all parts with commas for a clean display in logs
    record.context = ", ".join(context_parts)
