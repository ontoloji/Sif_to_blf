"""
Vector BLF writer using python-can.
This produces BLF files readable by tools that rely on python-can.BLFReader.
"""

from enum import IntEnum
from typing import List
import time


class BLFObjectType(IntEnum):
    """Object type constants kept for backward compatibility."""

    UNKNOWN = 0
    CAN_MESSAGE = 1
    CAN_ERROR = 2
    OVERLOAD = 3
    CAN_STATISTIC = 4
    APP_TRIGGER = 5
    ENV_INTEGER = 6
    ENV_DOUBLE = 7
    ENV_STRING = 8
    ENV_DATA = 9
    LOG_CONTAINER = 10
    CAN_MESSAGE2 = 86
    CAN_FD_MESSAGE = 88
    CAN_FD_MESSAGE_64 = 89
    ETHERNET_FRAME = 71
    SYS_VARIABLE = 96


class BLFWriter:
    """Writer for Vector BLF format via python-can."""

    def __init__(self, filepath: str, application_id: str = "SIF2BLF"):
        self.filepath = filepath
        self.application_id = application_id
        self.objects: List[dict] = []

    def add_can_message(self, channel: int, can_id: int, data: bytes, timestamp_ns: int, flags: int = 0):
        """Queue a classic CAN message."""
        obj = {
            "type": BLFObjectType.CAN_MESSAGE2,
            "channel": channel,
            "flags": flags,
            "dlc": len(data),
            "can_id": can_id,
            "data": data,
            "timestamp": timestamp_ns,
        }
        self.objects.append(obj)

    def add_env_double(self, name: str, value: float, timestamp_ns: int):
        """Queue ENV_DOUBLE object.

        Note: python-can BLFWriter focuses on CAN frames. We keep this API for compatibility,
        but these objects are skipped during write for viewer compatibility.
        """
        obj = {
            "type": BLFObjectType.ENV_DOUBLE,
            "name": name,
            "value": value,
            "timestamp": timestamp_ns,
        }
        self.objects.append(obj)

    def add_can_fd_message(
        self,
        channel: int,
        can_id: int,
        data: bytes,
        timestamp_ns: int,
        flags: int = 0,
        fd_flags: int = 0,
    ):
        """Queue a CAN FD message."""
        obj = {
            "type": BLFObjectType.CAN_FD_MESSAGE_64,
            "channel": channel,
            "flags": flags,
            "fd_flags": fd_flags,
            "dlc": len(data),
            "can_id": can_id,
            "data": data,
            "timestamp": timestamp_ns,
        }
        self.objects.append(obj)

    def write(self):
        """Write BLF using python-can to ensure reader compatibility."""
        try:
            import can
        except Exception as exc:
            raise RuntimeError(
                "python-can is required to write viewer-compatible BLF files. "
                "Install with: pip install python-can"
            ) from exc

        skipped_non_can = 0
        epoch_base = time.time()

        with can.BLFWriter(self.filepath) as writer:
            for obj in self.objects:
                obj_type = obj.get("type")
                if obj_type not in (BLFObjectType.CAN_MESSAGE2, BLFObjectType.CAN_FD_MESSAGE_64):
                    skipped_non_can += 1
                    continue

                data = bytes(obj.get("data", b""))
                timestamp = epoch_base + (int(obj.get("timestamp", 0)) / 1_000_000_000.0)
                message = can.Message(
                    timestamp=timestamp,
                    arbitration_id=int(obj.get("can_id", 0)),
                    data=data,
                    is_extended_id=False,
                    is_fd=(obj_type == BLFObjectType.CAN_FD_MESSAGE_64),
                    channel=int(obj.get("channel", 1)),
                )
                writer.on_message_received(message)

        if skipped_non_can > 0:
            print(f"Warning: Skipped {skipped_non_can} non-CAN objects for BLF compatibility")
