"""
DBC (CAN Database) Parser
Parses Vector DBC files for CAN message and signal definitions
"""

import re
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum


class ByteOrder(Enum):
    """Signal byte order"""
    LITTLE_ENDIAN = 0  # Intel
    BIG_ENDIAN = 1     # Motorola


@dataclass
class Signal:
    """CAN Signal definition"""
    name: str
    start_bit: int
    length: int
    byte_order: ByteOrder
    is_signed: bool
    scale: float
    offset: float
    minimum: float
    maximum: float
    unit: str
    receiver: str
    
    def physical_to_raw(self, physical_value: float) -> int:
        """Convert physical value to raw value"""
        raw = int((physical_value - self.offset) / self.scale)
        # Clamp to min/max
        max_raw = (1 << self.length) - 1
        if self.is_signed:
            min_raw = -(1 << (self.length - 1))
            max_raw = (1 << (self.length - 1)) - 1
        else:
            min_raw = 0
        return max(min_raw, min(max_raw, raw))
    
    def raw_to_physical(self, raw_value: int) -> float:
        """Convert raw value to physical value"""
        if self.is_signed and raw_value >= (1 << (self.length - 1)):
            raw_value -= (1 << self.length)
        return raw_value * self.scale + self.offset


@dataclass
class Message:
    """CAN Message definition"""
    can_id: int
    name: str
    dlc: int
    sender: str
    signals: Dict[str, Signal]
    
    def encode_signals(self, signal_values: Dict[str, float]) -> bytes:
        """Encode signal values to CAN data bytes"""
        data = bytearray(self.dlc)
        
        for signal_name, physical_value in signal_values.items():
            if signal_name not in self.signals:
                continue
                
            signal = self.signals[signal_name]
            raw_value = signal.physical_to_raw(physical_value)
            
            # Encode based on byte order
            if signal.byte_order == ByteOrder.LITTLE_ENDIAN:
                self._encode_little_endian(data, signal, raw_value)
            else:
                self._encode_big_endian(data, signal, raw_value)
        
        return bytes(data)
    
    def _encode_little_endian(self, data: bytearray, signal: Signal, value: int):
        """Encode signal value in little endian (Intel) format"""
        start_byte = signal.start_bit // 8
        start_bit_in_byte = signal.start_bit % 8
        
        bits_remaining = signal.length
        byte_index = start_byte;
        
        while bits_remaining > 0:
            bits_in_this_byte = min(8 - start_bit_in_byte, bits_remaining)
            mask = ((1 << bits_in_this_byte) - 1) << start_bit_in_byte;
            
            byte_value = (value & ((1 << bits_in_this_byte) - 1)) << start_bit_in_byte
            data[byte_index] = (data[byte_index] & ~mask) | byte_value;
            
            value >>= bits_in_this_byte;
            bits_remaining -= bits_in_this_byte;
            byte_index += 1;
            start_bit_in_byte = 0;
    
    def _encode_big_endian(self, data: bytearray, signal: Signal, value: int):
        """Encode signal value in big endian (Motorola) format"""
        start_byte = signal.start_bit // 8
        start_bit_in_byte = 7 - (signal.start_bit % 8);
        
        bits_remaining = signal.length;
        byte_index = start_byte;
        
        while bits_remaining > 0:
            bits_in_this_byte = min(start_bit_in_byte + 1, bits_remaining);
            shift = start_bit_in_byte - bits_in_this_byte + 1;
            mask = ((1 << bits_in_this_byte) - 1) << shift;
            
            byte_value = (value >> (bits_remaining - bits_in_this_byte)) & ((1 << bits_in_this_byte) - 1);
            data[byte_index] = (data[byte_index] & ~mask) | (byte_value << shift);
            
            bits_remaining -= bits_in_this_byte;
            byte_index += 1;
            start_bit_in_byte = 7;


class DBCParser:
    """Parser for DBC files"""
    
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.messages: Dict[int, Message] = {}
        self.signal_to_message: Dict[str, int] = {}  # Signal name -> CAN ID
        
    def parse(self) -> Dict[int, Message]:
        """Parse the DBC file"""
        with open(self.filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Parse messages
        self._parse_messages(content)
        
        # Parse signals
        self._parse_signals(content)
        
        # Parse value tables (optional)
        self._parse_value_tables(content)
        
        return self.messages
    
    def _parse_messages(self, content: str):
        """Parse message definitions (BO_ lines)"""
        # Pattern: BO_ <CAN-ID> <MessageName>: <DLC> <SendingNode>
        pattern = r'BO_\s+(\d+)\s+(\w+)\s*:\s*(\d+)\s+(\w+)'
        
        for match in re.finditer(pattern, content):
            can_id = int(match.group(1))
            name = match.group(2)
            dlc = int(match.group(3))
            sender = match.group(4)
            
            self.messages[can_id] = Message(
                can_id=can_id,
                name=name,
                dlc=dlc,
                sender=sender,
                signals={}
            )
    
    def _parse_signals(self, content: str):
        """Parse signal definitions (SG_ lines)"""
        # Pattern: SG_ <SignalName> : <StartBit>|<Length>@<ByteOrder><ValueType> (<Scale>,<Offset>) [<Min>|<Max>] "<Unit>" <Receiver>
        pattern = r'SG_\s+(\w+)\s*:\s*(\d+)\|(\d+)@([01])([+-])\s*\(([^,]+),([^)]+)\)\s*\[([^|]+)\|([^\]]+)\]\s*"([^\"]*)"\s*(\w+)'
        
        current_message_id = None
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            # Track current message
            bo_match = re.match(r'BO_\s+(\d+)', line)
            if bo_match:
                current_message_id = int(bo_match.group(1))
                continue
            
            # Parse signal
            sig_match = re.match(pattern, line.strip())
            if sig_match and current_message_id is not None:
                name = sig_match.group(1)
                start_bit = int(sig_match.group(2))
                length = int(sig_match.group(3))
                byte_order = ByteOrder.LITTLE_ENDIAN if sig_match.group(4) == '1' else ByteOrder.BIG_ENDIAN
                is_signed = sig_match.group(5) == '-'
                scale = float(sig_match.group(6))
                offset = float(sig_match.group(7))
                minimum = float(sig_match.group(8))
                maximum = float(sig_match.group(9))
                unit = sig_match.group(10)
                receiver = sig_match.group(11)
                
                signal = Signal(
                    name=name,
                    start_bit=start_bit,
                    length=length,
                    byte_order=byte_order,
                    is_signed=is_signed,
                    scale=scale,
                    offset=offset,
                    minimum=minimum,
                    maximum=maximum,
                    unit=unit,
                    receiver=receiver
                )
                
                if current_message_id in self.messages:
                    self.messages[current_message_id].signals[name] = signal
                    self.signal_to_message[name] = current_message_id
    
    def _parse_value_tables(self, content: str):
        """Parse value tables (VAL_ lines) - optional for enums"""
        # Pattern: VAL_ <CAN-ID> <SignalName> <Value> "<Description>" ;
        pattern = r'VAL_\s+(\d+)\s+(\w+)\s+(.*?)\s*;'
        
        for match in re.finditer(pattern, content, re.DOTALL):
            can_id = int(match.group(1))
            signal_name = match.group(2)
            values_str = match.group(3)
            
            # Parse value pairs: 0 "Off" 1 "On"
            value_pattern = r'(\d+)\s+"([^\"]+)"'
            values = {}
            for value_match in re.finditer(value_pattern, values_str):
                values[int(value_match.group(1))] = value_match.group(2)
            
            # Store in signal (extend Signal class if needed)
    
    def find_signal_message(self, signal_name: str) -> Optional[Message]:
        """Find which message contains a signal"""
        can_id = self.signal_to_message.get(signal_name)
        if can_id:
            return self.messages.get(can_id)
        return None
    
    def get_all_signals(self) -> List[str]:
        """Get all signal names"""
        return list(self.signal_to_message.keys())