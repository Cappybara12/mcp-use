# File: hypertube/utils/messageHelper/MessageHelper.py
import datetime
import importlib.metadata
import os
import platform
import socket
import threading
import urllib.request
import urllib.error
import json

from hypertube.utils.UtilsConst import UtilsConst


def __get_host_name():
    try:
        return socket.gethostname()
    except socket.error:
        return "Unknown Host"


def __get_package_version():
    try:
        return importlib.metadata.version("hypertube-python-sdk")
    except importlib.metadata.PackageNotFoundError:
        return "Unknown"


APP_INSIGHTS_TRACK_URL = "https://polandcentral-0.in.applicationinsights.azure.com/v2/track"
REQUEST_TIMEOUT_SECONDS = 3
APPINSIGHTS_CONNECTION_STRING_ENV_NAME = "HYPERTUBE_APPLICATIONINSIGHTS_CONNECTION_STRING"
DEFAULT_INSTRUMENTATION_KEY = "87e949af-cf27-489c-8518-591b3b55b667"
CALLING_RUNTIME_NAME = "Python"
VERSION = __get_package_version()
NODE_NAME = __get_host_name()
OS_NAME = platform.system()


def _parse_connection_string(connection_string):
    values = {}
    for raw_segment in connection_string.split(";"):
        segment = raw_segment.strip()
        if not segment:
            continue

        separator_index = segment.find("=")
        if separator_index <= 0 or separator_index >= len(segment) - 1:
            continue

        key = segment[:separator_index].strip().lower()
        value = segment[separator_index + 1:].strip()
        if key and value:
            values[key] = value
    return values


def _resolve_telemetry_target():
    connection_string = os.environ.get(APPINSIGHTS_CONNECTION_STRING_ENV_NAME, "")
    if not connection_string.strip():
        return APP_INSIGHTS_TRACK_URL, DEFAULT_INSTRUMENTATION_KEY

    values = _parse_connection_string(connection_string)
    ingestion_endpoint = values.get("ingestionendpoint", "")
    instrumentation_key = values.get("instrumentationkey", "")
    address = APP_INSIGHTS_TRACK_URL
    if ingestion_endpoint:
        address = ingestion_endpoint.rstrip("/") + "/v2/track"

    return address, instrumentation_key or DEFAULT_INSTRUMENTATION_KEY


class MessageHelper:

    @staticmethod
    def send_message_to_app_insights(operation_name, message):
        try:
            thread = threading.Thread(
                target=MessageHelper.send_message_to_app_insights_sync,
                args=(operation_name, message),
                daemon=True,
            )
            thread.start()
        except Exception:
            pass

    @staticmethod
    def send_message_to_app_insights_sync(operation_name, message):
        try:
            license_key = UtilsConst.get_license_key()
            if (license_key == "functional-tests-key"):
                return 0
            app_insights_track_url, instrumentation_key = _resolve_telemetry_target()

            json_payload = {
                "name": "AppEvents",
                "time": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "iKey": instrumentation_key,
                "tags": {
                    "ai.application.ver": VERSION,
                    "ai.cloud.roleInstance": NODE_NAME,
                    "ai.operation.id": "0",
                    "ai.operation.parentId": "0",
                    "ai.operation.name": operation_name,
                    "ai.internal.sdkVersion": "hypertube",
                    "ai.internal.nodeName": NODE_NAME
                },
                "data": {
                    "baseType": "EventData",
                    "baseData": {
                        "ver": 2,
                        "name": message,
                        "properties": {
                            "OperatingSystem": OS_NAME,
                            "LicenseKey": license_key,
                            "CallingTechnology": CALLING_RUNTIME_NAME
                        }
                    }
                }
            }

            data = json.dumps(json_payload).encode("utf-8")
            req = urllib.request.Request(
                app_insights_track_url,
                data=data,
                headers={'Content-Type': 'application/json'}
            )
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_SECONDS) as response:
                status_code = response.getcode()
            return status_code
        except urllib.error.HTTPError as e:
            return e.code
        except Exception:
            return -1
