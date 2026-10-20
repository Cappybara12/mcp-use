from ctypes import *

def callbackFunc(message_byte_array, message_byte_array_len):
    message_byte_array_py = bytearray((c_ubyte * message_byte_array_len).from_address(
        addressof(message_byte_array.contents)))
    from hypertube.core.receiver.Receiver import Receiver
    # Initialize exception handler if not already done
    Receiver.initialize_exception_handler()
    if message_byte_array[10] == 11:
        return Receiver.heart_beat(message_byte_array_py)
    else:
        return Receiver.send_command(message_byte_array_py)
