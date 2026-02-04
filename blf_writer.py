"""
Vector BLF (Binary Logging Format) Writer
Writes BLF v2.x format files compatible with Vector CANalyzer/CANoe
"""

import struct
import datetime
from typing import List, Optional
from enum import IntEnum


class BLFObjectType(IntEnum):
    """BLF Object Types"""
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
    """Writer for Vector BLF format"""
    
    # BLF File signature
    BLF_SIGNATURE = b'LOGG'
    BLF_HEADER_SIZE = 144
    
    def __init__(self, filepath: str, application_id: str = "SIF2BLF"):
        self.filepath = filepath
        self.application_id = application_id
        self.objects = []
        self.start_time = datetime.datetime.now()
        
    def add_can_message(self, channel: int, can_id: int, data: bytes, 
                       timestamp_ns: int, flags: int = 0):
        """Add a CAN message"""
        obj = {
            'type': BLFObjectType.CAN_MESSAGE2,
            'channel': channel,
            'flags': flags,
            'dlc': len(data),
            'can_id': can_id,
            'data': data,
            'timestamp': timestamp_ns
        }
        self.objects.append(obj)
    
    def add_can_fd_message(self, channel: int, can_id: int, data: bytes,
                          timestamp_ns: int, flags: int = 0, fd_flags: int = 0):
        """Add a CAN FD message"""
        obj = {
            'type': BLFObjectType.CAN_FD_MESSAGE_64,
            'channel': channel,
            'flags': flags,
            'fd_flags': fd_flags,
            'dlc': len(data),
            'can_id': can_id,
            'data': data,
            'timestamp': timestamp_ns
        }
        self.objects.append(obj)
    
    def write(self):
        """Write the BLF file"""
        with open(self.filepath, 'wb') as f:
            # Write file header
            self._write_header(f)
            
            # Write all objects
            for obj in self.objects:
                self._write_object(f, obj)
            
            # Update header with final statistics
            file_size = f.tell()
            f.seek(0)
            self._write_header(f, file_size=file_size, object_count=len(self.objects))
    
    def _write_header(self, f, file_size: int = 0, object_count: int = 0):
        """Write BLF file header"""
        # Signature
        f.write(self.BLF_SIGNATURE)
        
        # Header size
        f.write(struct.pack('<I', self.BLF_HEADER_SIZE))
        
        # Header version
        f.write(struct.pack('<I', 2))  # BLF version 2
        
        # Object count
        f.write(struct.pack('<I', object_count))
        
        # Objects size
        f.write(struct.pack('<Q', file_size - self.BLF_HEADER_SIZE if file_size > 0 else 0))
        
        # Application ID (32 bytes)
        app_id = self.application_id.encode('utf-8')[:32].ljust(32, b'\x00')
        f.write(app_id)
        
        # Application version (4 x uint8)
        f.write(struct.pack('<BBBB', 1, 0, 0, 0))
        
        # Measurement start time
        now = self.start_time
        # SystemTime structure: year, month, dayOfWeek, day, hour, minute, second, milliseconds
        f.write(struct.pack('<HHHHHHHH', 
                          now.year, now.month, now.weekday(), now.day,
                          now.hour, now.minute, now.second, now.microsecond // 1000))
        
        # Measurement end time (same for now)
        f.write(struct.pack('<HHHHHHHH', 
                          now.year, now.month, now.weekday(), now.day,
                          now.hour, now.minute, now.second, now.microsecond // 1000))
        
        # Padding to 144 bytes
        current_pos = f.tell()
        padding = self.BLF_HEADER_SIZE - current_pos
        if padding > 0:
            f.write(b'\x00' * padding)
    
    def _write_object(self, f, obj: dict):
        """Write a single BLF object"""
        obj_type = obj['type']
        
        if obj_type == BLFObjectType.CAN_MESSAGE2:
            self._write_can_message2(f, obj)
        elif obj_type == BLFObjectType.CAN_FD_MESSAGE_64:
            self._write_can_fd_message64(f, obj)
    
    def _write_can_message2(self, f, obj: dict):
        """Write CAN_MESSAGE2 object"""
        data = obj['data']
        dlc = obj['dlc']
        
        # Calculate object size (must be multiple of 4)
        base_size = 48  # Base structure size
        data_size = ((dlc + 3) // 4) * 4  # Round up to multiple of 4
        obj_size = base_size + data_size
        
        # Object header (16 bytes)
        f.write(struct.pack('<I', obj_size))  # Object size
        f.write(struct.pack('<I', 0))  # Header size
        f.write(struct.pack('<H', obj_type))  # Object type
        f.write(struct.pack('<H', obj['flags']))  # Object flags
        f.write(struct.pack('<H', 0))  # Reserved
        f.write(struct.pack('<H', 1))  # Object version
        f.write(struct.pack('<Q', obj['timestamp']))  # Timestamp in nanoseconds
        
        # CAN_MESSAGE2 specific (32 bytes + data)
        f.write(struct.pack('<H', obj['channel']))  # Channel
        f.write(struct.pack('<B', dlc))  # DLC
        f.write(struct.pack('<B', 0))  # Valid data bytes
        f.write(struct.pack('<I', obj['can_id']))  # CAN ID
        f.write(struct.pack('<I', 0))  # Frame length in ns
        f.write(struct.pack('<I', 0))  # Bit count
        f.write(struct.pack('<I', 0))  # Reserved
        f.write(struct.pack('<I', 0))  # Reserved
        f.write(struct.pack('<I', 0))  # Reserved
        f.write(struct.pack('<I', 0))  # Reserved
        
        # Data bytes (padded to multiple of 4)
        f.write(data.ljust(data_size, b'\x00'))
    
    def _write_can_fd_message64(self, f, obj: dict):
        """Write CAN_FD_MESSAGE_64 object"""
        data = obj['data']
        dlc = obj['dlc']
        
        # Calculate object size
        base_size = 80
        data_size = ((dlc + 3) // 4) * 4
        obj_size = base_size + data_size
        
        # Object header
        f.write(struct.pack('<I', obj_size))
        f.write(struct.pack('<I', 0))
        f.write(struct.pack('<H', obj_type))
        f.write(struct.pack('<H', obj['flags']))
        f.write(struct.pack('<H', 0))
        f.write(struct.pack('<H', 1))
        f.write(struct.pack('<Q', obj['timestamp']))
        
        # CAN FD specific
        f.write(struct.pack('<H', obj['channel']))
        f.write(struct.pack('<B', dlc))
        f.write(struct.pack('<B', 0))
        f.write(struct.pack('<I', obj['can_id']))
        f.write(struct.pack('<I', 0))  # Frame length
        f.write(struct.pack('<I', 0))  # Bit count
        f.write(struct.pack('<I', obj.get('fd_flags', 0)))  # FD flags
        f.write(struct.pack('<I', 0))  # Valid data bytes
        f.write(b'\x00' * 40)  # Reserved
        
        # Data
        f.write(data.ljust(data_size, b'\x00'))