from hypertube.utils.CommandType import CommandType


class Command:

    def __init__(self, runtime_name, command_type, payload=None):
        """
        Initialize a Command.
        Matches C# constructor: Command(RuntimeName runtimeName, CommandType commandType, params object[] payload)
        and: Command(RuntimeName runtimeName, CommandType commandType, Array payload)

        Args:
            runtime_name: The runtime name.
            command_type: The command type.
            payload: The payload. Can be None, a list/tuple (array-like), or a single item.
                    If None, defaults to empty list.
        """
        self.runtime_name = runtime_name
        self.command_type = command_type

        if payload is None:
            self.payload = [None]
        elif isinstance(payload, (list, tuple)):
            # If it's a list or tuple, convert to list (matching C# Array handling)
            # For list, reuse directly for efficiency (matching C# object[] case)
            if isinstance(payload, list):
                self.payload = payload
            else:
                # For tuple or other sequence, convert to list
                self.payload = list(payload)
        else:
            # Single item - wrap in list
            self.payload = [payload]

    @property
    def RuntimeName(self):
        """Get the runtime name (property accessor matching C# style)."""
        return self.runtime_name

    @property
    def CommandType(self):
        """Get the command type (property accessor matching C# style)."""
        return self.command_type

    @property
    def Payload(self):
        """Get the payload (property accessor matching C# style)."""
        return self.payload

    def get_payload(self):
        """Get the payload (legacy method for backward compatibility)."""
        return self.payload

    @staticmethod
    def create_response(response, runtime_name):
        return Command(runtime_name, CommandType.Value, response)

    @staticmethod
    def create_reference(guid, runtime_name):
        return Command(runtime_name, CommandType.Reference, guid)

    def drop_first_payload_argument(self):
        """Legacy method name for backward compatibility."""
        return self.drop_first_payload_arg()

    def drop_first_payload_arg(self):
        if len(self.payload) <= 1:
            return Command(self.runtime_name, self.command_type, [])

        return Command(self.runtime_name, self.command_type, self.payload[1:])

    def add_arg_to_payload(self, arg):
        return Command(self.runtime_name, self.command_type, [*self.payload, arg])

    def prepend_arg_to_payload(self, arg_command):
        if arg_command is None:
            return self

        return Command(self.runtime_name, self.command_type, [arg_command, *self.payload])

    def __str__(self):
        try:
            sb = ["  { ", f"RuntimeName: {self.runtime_name}, ", f"CommandType: {self.command_type}, ", "Payload: \n",
                  "    ["]

            payload = self.payload
            length = len(payload)

            if length > 0:
                sb.append("\n")
                for i in range(length):
                    item = payload[i]
                    if item is None:
                        item_str = "null"
                    elif isinstance(item, str):
                        item_str = f'  "{item}"'
                    elif isinstance(item, Command):
                        item_str = item.__str__().replace("\n", "\n    ")
                    else:
                        item_str = f"  {item}"

                    sb.append(f"    {item_str}")
                    if i < length - 1:
                        sb.append(",\n")
                    else:
                        sb.append("\n")
                sb.append("    ]\n")
            else:
                sb.append("  ]\n")

            sb.append("  }")
            return "".join(sb)
        except Exception as ex:
            return f"Error while converting command to string:{str(ex)}"

    def __eq__(self, element):
        if self is element:
            return True
        if element is None or self.__class__ != element.__class__:
            return False
        if self.command_type != element.command_type or self.runtime_name != element.runtime_name:
            return False
        if len(self.payload) != len(element.payload):
            return False

        for i, payload_item in enumerate(self.payload):
            if payload_item != element.payload[i]:
                return False

        return True