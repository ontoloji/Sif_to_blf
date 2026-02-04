"""
Somat SIF File Parser
Parses SIF files from Somat eDAQ systems
"""

import struct
import re
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass
from datetime import datetime


@dataclass
class CANInterface:
    """CAN Interface configuration"""
    name: str
    baud_rate: int
    databases: List[str]
    node_name: str
    passive_mode: bool


@dataclass
class Channel:
    """Sensor/Signal Channel"""
    name: str
    channel_type: str  # Pressure, Temperature, Voltage, Position, Velocity
    units: str
    sample_rate: int
    fs_min: float
    fs_max: float
    cal_slope: float
    cal_intercept: float
    connector: str
    prefix: str


@dataclass
class SIFData:
    """Parsed SIF file data"""
    version: str
    file_version: str
    master_sample_rate: int
    can_interfaces: List[CANInterface]
    channels: List[Channel]
    data_offset: int
    metadata: Dict[str, Any]


class SIFParser:
    """Parser for Somat SIF files""" 
    
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.raw_data = None
        
    def parse(self) -> SIFData:
        """Parse the SIF file"""
        with open(self.filepath, 'rb') as f:
            self.raw_data = f.read()
        
        # Find where text metadata ends
        text_end = self._find_text_end()
        text_data = self.raw_data[:text_end].decode('utf-8', errors='ignore')
        
        # Parse metadata sections
        metadata = self._parse_metadata(text_data)
        can_interfaces = self._parse_can_interfaces(text_data)
        channels = self._parse_channels(text_data)
        
        return SIFData(
            version=metadata.get('TCEVersion', 'unknown'),
            file_version=metadata.get('FileVersion', 'unknown'),
            master_sample_rate=int(metadata.get('MasterSampleRate', 100000)),
            can_interfaces=can_interfaces,
            channels=channels,
            data_offset=text_end,
            metadata=metadata
        )
    
    def _find_text_end(self) -> int:
        """Find where text metadata ends and binary data begins"""
        # Look for continuous null bytes or high concentration of binary data
        window_size = 1024
        null_threshold = 0.5  # 50% nulls indicates binary section
        
        for i in range(0, len(self.raw_data) - window_size, 256):
            window = self.raw_data[i:i+window_size]
            null_count = window.count(0)
            
            if null_count / window_size > null_threshold:
                # Found binary section, back up to find actual boundary
                # Look backwards for last newline
                for j in range(i, max(0, i-4096), -1):
                    if self.raw_data[j:j+2] == b'\n\n':
                        return j + 2
                return i
        
        # If not found, assume 80% of file is metadata
        return int(len(self.raw_data) * 0.8)
    
    def _parse_metadata(self, text: str) -> Dict[str, Any]:
        """Parse general metadata"""
        metadata = {}
        
        patterns = {
            'TCEVersion': r'TCEVersion=(.+)',
            'FileVersion': r'FileVersion=(.+)',
            'MasterSampleRate': r'MasterSampleRate=(\d+)',
            'NumChanItems': r'NumChanItems=(\d+)',
            'NumHardItems': r'NumHardItems=(\d+)',
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, text)
            if match:
                metadata[key] = match.group(1).strip()
        
        return metadata
    
    def _parse_can_interfaces(self, text: str) -> List[CANInterface]:
        """Parse CAN interface configurations"""
        interfaces = []
        
        # Find all HardItem sections with CAN
        can_pattern = r'\[HardItem_\d+\].*?(?=\[HardItem_|\[ChanItem_|$)'
        
        for match in re.finditer(can_pattern, text, re.DOTALL):
            section = match.group(0)
            
            if 'VBM_HardInterface=CAN' in section or 'HardInterface_1=CAN' in section:
                # Extract CAN properties
                id_match = re.search(r'ID=(\w+)', section)
                baud_match = re.search(r'BaudRate_1=(\d+)', section)
                
                if id_match and baud_match:
                    # Extract databases
                    databases = []
                    db_matches = re.finditer(r'DataBase_\d+_\d+=(\w+)', section)
                    for db_match in db_matches:
                        databases.append(db_match.group(1))
                    
                    node_match = re.search(r'NodeName=([\d.]+)', section)
                    passive_match = re.search(r'PassiveMode_1=(\d)', section)
                    
                    interfaces.append(CANInterface(
                        name=id_match.group(1),
                        baud_rate=int(baud_match.group(1)),
                        databases=databases,
                        node_name=node_match.group(1) if node_match else 'unknown',
                        passive_mode=bool(int(passive_match.group(1))) if passive_match else True
                    ))
        
        return interfaces
    
    def _parse_channels(self, text: str) -> List[Channel]:
        """Parse sensor channel configurations"""
        channels = []
        
        # Find all ChanItem sections
        chan_pattern = r'\[ChanItem_\d+\](.*?)(?=\[ChanItem_|\[DataItem_|$)'
        
        for match in re.finditer(chan_pattern, text, re.DOTALL):
            section = match.group(1)
            
            try:
                # Extract channel properties
                id_match = re.search(r'ID_1=(\w+)', section)
                type_match = re.search(r'Type_1=(\w+)', section)
                units_match = re.search(r'Units_1=([^\n]+)', section)
                rate_match = re.search(r'SampleRate=(\d+)', section)
                min_match = re.search(r'FS_Min_1=([-+]?:\d*\.?\d+(?:[eE][-+]?:\d+)?)', section)
                max_match = re.search(r'FS_Max_1=([-+]?:\d*\.?\d+(?:[eE][-+]?:\d+)?)', section)
                slope_match = re.search(r'CalSlope=([-+]?:\d*\.?\d+(?:[eE][-+]?:\d+)?)', section)
                intercept_match = re.search(r'CalIntercept=([-+]?:\d*\.?\d+(?:[eE][-+]?:\d+)?)', section)
                connector_match = re.search(r'Connector=([^\n]+)', section)
                prefix_match = re.search(r'Prefix=([^\n]+)', section)
                
                if id_match:
                    channels.append(Channel(
                        name=id_match.group(1),
                        channel_type=type_match.group(1) if type_match else 'Unknown',
                        units=units_match.group(1).strip() if units_match else '',
                        sample_rate=int(rate_match.group(1)) if rate_match else 1,
                        fs_min=float(min_match.group(1)) if min_match else 0.0,
                        fs_max=float(max_match.group(1)) if max_match else 1.0,
                        cal_slope=float(slope_match.group(1)) if slope_match else 1.0,
                        cal_intercept=float(intercept_match.group(1)) if intercept_match else 0.0,
                        connector=connector_match.group(1).strip() if connector_match else '',
                        prefix=prefix_match.group(1).strip() if prefix_match else ''
                    ))
            except Exception as e:
                print(f"Warning: Could not parse channel: {e}")
                continue
        
        return channels
    
    def get_binary_data(self, sif_data: SIFData) -> bytes:
        """Get the binary measurement data section"""
        return self.raw_data[sif_data.data_offset:]