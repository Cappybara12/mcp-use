import os
import platform
import threading
from ctypes import *
from hypertube.core.callback.callbackFunc import callbackFunc

CMPFUNC = CFUNCTYPE(py_object, POINTER(c_ubyte), c_int)
callbackFunction = CMPFUNC(callbackFunc)


class TransmitterWrapper:
    _python_lib = None
    _load_lock = threading.Lock()

    @staticmethod
    def get_native_lib():
        if TransmitterWrapper._python_lib is not None:
            return TransmitterWrapper._python_lib

        with TransmitterWrapper._load_lock:
            if TransmitterWrapper._python_lib is not None:
                return TransmitterWrapper._python_lib

            machine = platform.machine().lower()
            if 'arm' in machine or 'aarch' in machine:
                arch = 'ARM64' if '64' in machine else 'ARM'
            elif '64' in machine:
                arch = 'X64'
            elif '32' in machine or 'i386' in machine:
                arch = 'X86'
            else:
                raise RuntimeError("Unsupported architecture: " + machine)

            if platform.system() == 'Windows':
                os_name = 'Windows'
                lib_name = 'HypertubePythonRuntimeNative.dll'
            elif platform.system() == 'Linux':
                os_name = 'Linux'
                lib_name = 'libHypertubePythonRuntimeNative.so'
            elif platform.system() == 'Darwin':
                os_name = 'MacOs'
                lib_name = 'libHypertubePythonRuntimeNative.dylib'
            else:
                raise RuntimeError("Unsupported operating system: " + platform.system())

            relative_path = f'Binaries/Native/{os_name}/{arch}/{lib_name}'
            native_lib_path = os.path.join(os.path.curdir, relative_path)

            if not os.path.exists(native_lib_path):
                this_file_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
                native_lib_path = os.path.join(this_file_path, relative_path)


            lib = cdll.LoadLibrary(native_lib_path)
            lib.SetCallback(callbackFunction)
            TransmitterWrapper._python_lib = lib
        return TransmitterWrapper._python_lib

    @staticmethod
    def send_command(message, config_source):
        lib = TransmitterWrapper.get_native_lib()
        message_array = bytearray(message)
        message_ubyte_array = c_ubyte * len(message_array)
        config_source_value = str(config_source).encode('utf-8')
        config_source_ptr = c_char_p(config_source_value)
        response_array_len = lib.SendCommand(message_ubyte_array.from_buffer(message_array), len(message_array), config_source_ptr)

        if response_array_len > 0:
            response = bytearray(response_array_len)
            response[0] = message_array[0]  
            response_ubyte_array = c_ubyte * response_array_len
            lib.ReadResponse(response_ubyte_array.from_buffer(response), response_array_len)
            return response
        elif response_array_len == 0:
            error_message = "Response is empty"
            raise RuntimeError(error_message)
        else:
            get_native_error = lib.GetNativeError
            get_native_error.restype = c_char_p
            get_native_error.argtypes = []
            error_message = get_native_error()
            raise RuntimeError("Hypertube native error code: " + str(response_array_len) + ". " + str(error_message))

    @staticmethod
    def activate(license_key):
        lib = TransmitterWrapper.get_native_lib()
        activate = lib.Activate
        activate.restype = c_int
        activate.argtypes = [c_char_p]
        activation_result = activate(license_key.encode('ascii'))
        if activation_result < 0:
            get_native_error = lib.GetNativeError
            get_native_error.restype = c_char_p
            get_native_error.argtypes = []
            error_message = get_native_error()
            raise RuntimeError(
                "Hypertube activation result: " + str(activation_result) + ". Native error message: " + str(
                    error_message))
        else:
            return activation_result

    @staticmethod
    def set_config_source(source_path):
        lib = TransmitterWrapper.get_native_lib()
        set_config_source = lib.SetConfigSource
        set_config_source.restype = c_int
        set_config_source.argtypes = [c_char_p]
        set_config_result = set_config_source(source_path.encode('utf-8'))
        if set_config_result < 0:
            get_native_error = lib.GetNativeError
            get_native_error.restype = c_char_p
            get_native_error.argtypes = []
            error_message = get_native_error()
            raise RuntimeError(
                "Hypertube set config source result: " + str(set_config_result) + ". Native error message: " + str(
                    error_message))
        else:
            return set_config_result

    @staticmethod
    def set_working_directory(path):
        lib = TransmitterWrapper.get_native_lib()
        set_working_directory = lib.SetWorkingDirectory
        set_working_directory.restype = c_int
        set_working_directory.argtypes = [c_char_p]
        set_working_directory_result = set_working_directory(path.encode('utf-8'))
        if set_working_directory_result < 0:
            get_native_error = lib.GetNativeError
            get_native_error.restype = c_char_p
            get_native_error.argtypes = []
            error_message = get_native_error()
            raise RuntimeError("Hypertube set working directory result: " + str(
                set_working_directory_result) + ". Native error message: " + str(error_message))
        else:
            return set_working_directory_result