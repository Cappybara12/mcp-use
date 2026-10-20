import asyncio
import concurrent.futures
import inspect
import threading

from hypertube.core.handler.HandlerDictionary import handler_dict
from hypertube.utils.Command import Command
from hypertube.utils.CommandType import CommandType


class AbstractHandler:
    _required_parameters_count = 0

    def process(self, command):
        raise NotImplementedError('subclasses must override process()!')

    def handle_command(self, command):
        if command.command_type != CommandType.Optimize:
            self._iterate(command)

        return self.process(command)

    @staticmethod
    def get_handler(command_type):
        handler = handler_dict.get(command_type)
        if handler is None:
            raise ValueError("Unsupported command type: {}".format(command_type))
        return handler

    @staticmethod
    def validate(command, required_parameters_count, caller_type_name):
        if command.payload is None:
            raise ValueError(f"{caller_type_name} parameters mismatch")

        has_too_few_parameters = len(command.payload) < required_parameters_count
        if has_too_few_parameters:
            raise ValueError(f"{caller_type_name} parameters mismatch")

    @staticmethod
    def _iterate(command):
        for index, payload_item in enumerate(command.payload):
            if isinstance(payload_item, Command):
                handler = AbstractHandler.get_handler(payload_item.command_type)
                command.payload[index] = handler.handle_command(payload_item)

    @staticmethod
    def _split_arguments_and_kwargs(payload, arguments_start_index):
        arguments = payload[arguments_start_index:]
        kwargs = {}
        if not arguments:
            return arguments, kwargs

        kwargs_marker = arguments[-1]
        if not isinstance(kwargs_marker, tuple) or not kwargs_marker:
            return arguments, kwargs
        if kwargs_marker[0] != CommandType.AsKwargs:
            return arguments, kwargs
        if len(kwargs_marker) != 2 or not isinstance(kwargs_marker[1], dict):
            raise ValueError("Kwargs marker must contain exactly one dictionary")

        return arguments[:-1], kwargs_marker[1]

    @staticmethod
    def resolve_async_result(result):
        if isinstance(result, threading.Thread):
            if result is threading.current_thread():
                raise RuntimeError("Cannot wait for the current thread")
            result.join()
            return None

        if isinstance(result, concurrent.futures.Future):
            return result.result()

        if isinstance(result, asyncio.Future):
            if result.done():
                return result.result()

            result_loop = result.get_loop() if hasattr(result, "get_loop") else result._loop
            running_loop = AbstractHandler._get_running_loop()

            if running_loop is result_loop:
                raise RuntimeError(
                    "Cannot synchronously resolve an asyncio.Future on its running event-loop thread"
                )

            if not result_loop.is_running():
                return result_loop.run_until_complete(result)

            return asyncio.run_coroutine_threadsafe(
                AbstractHandler._await_result(result), result_loop
            ).result()

        if inspect.isawaitable(result):
            if AbstractHandler._get_running_loop() is None:
                return AbstractHandler._run_awaitable(result)

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                return executor.submit(AbstractHandler._run_awaitable, result).result()

        return result

    @staticmethod
    async def _await_result(awaitable):
        return await awaitable

    @staticmethod
    def _get_running_loop():
        get_running_loop = getattr(asyncio, "get_running_loop", None)
        if get_running_loop is not None:
            try:
                return get_running_loop()
            except RuntimeError:
                return None

        loop = asyncio.get_event_loop()
        return loop if loop.is_running() else None

    @staticmethod
    def _run_awaitable(awaitable):
        run = getattr(asyncio, "run", None)
        if run is not None:
            return run(awaitable)

        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(awaitable)
        finally:
            loop.close()
            asyncio.set_event_loop(None)
