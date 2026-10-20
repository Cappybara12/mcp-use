import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional


@dataclass
class OperationContext:
    """
    Information about a logging operation that you want to track.

    This class helps you track a specific operation in your application
    (like "ProcessOrder" or "ValidateUser"). It maintains timing information
    and supports parent-child relationships between operations, which is
    essential for distributed tracing and understanding application flow.

    Key features:
    - Each operation has a unique ID
    - Operations can be nested (parent-child relationships)
    - Operations track their timing information automatically
    - You can add custom properties to provide more context

    Attributes:
        operation_name: A descriptive name for the operation
        operation_id: Automatically generated unique ID for this operation
        start_time: When the operation started (auto-set when created)
        end_time: When the operation completed (set when you call end())
        duration_ms: How long the operation took in milliseconds
        parent_operation_id: ID of the parent operation if this is nested
        properties: Dictionary of additional information for this operation
    """

    # A descriptive name that identifies what this operation does
    operation_name: str

    # W3C 32
    operation_id: str = field(default_factory=lambda: uuid.uuid4().hex)

    # W3C 16
    span_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])

    # When the operation started (auto-set to current time)
    start_time: datetime = field(default_factory=datetime.utcnow)

    # When the operation ended (initially None, set by end())
    end_time: Optional[datetime] = None

    # How long the operation took in milliseconds (set by end())
    duration_ms: Optional[float] = None

    # If this is a child operation, this stores the parent's ID
    # This allows reconstructing the full operation hierarchy
    parent_operation_id: Optional[str] = None

    # Additional information about this operation (key-value pairs)
    # Examples: {"user_id": "123", "order_id": "ABC-456"}
    properties: Dict[str, str] = field(default_factory=dict)

    # Upon Exception -> Telemetry needs to know, as we handle exceptions ourselves
    failed: bool = False

    response_code: str = "200"

    def mark_failed(self, response_code: str = "500") -> None:
        self.failed = True
        self.response_code = response_code

    def end(self) -> None:
        """
        Complete this operation and calculate how long it took.

        This method:
        1. Records the current time as the end time
        2. Calculates how long the operation took (in milliseconds)
        3. Adds the duration as a property for easy access in logs

        Example:
            op = OperationContext("ProcessOrder")
            # ... do some work ...
            op.end()  # Marks completion and calculates duration
            print(f"Operation took {op.duration_ms} milliseconds")
        """
        # Record when the operation finished
        self.end_time = datetime.utcnow()

        # Calculate how long it took (in milliseconds)
        delta = self.end_time - self.start_time
        self.duration_ms = delta.total_seconds() * 1000

        # Add the duration as a property so it appears in logs
        self.properties["duration_ms"] = f"{self.duration_ms:.2f}"
