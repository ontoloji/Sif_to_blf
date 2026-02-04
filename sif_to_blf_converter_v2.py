"""
SIF to BLF Converter v2.0
Converts Somat eDAQ SIF files to Vector BLF format with DBC support
"""

import argparse
import sys
from pathlib import Path
from sif_parser import SIFParser, Channel
from blf_writer import BLFWriter
from dbc_parser import DBCParser, Message
from typing import Dict, List
import glob


class SIFToBLFConverterV2:
    """Main converter class with DBC support"""
    
    def __init__(self, sif_path: str, blf_path: str, dbc_paths: List[str]):
        self.sif_path = sif_path
        self.blf_path = blf_path
        self.dbc_paths = dbc_paths
        self.dbc_databases: Dict[str, DBCParser] = {}
        
    def convert(self):
        """Perform the conversion"""
        print(f"🔍 Parsing SIF file: {self.sif_path}")
        
        # Parse SIF file
        parser = SIFParser(self.sif_path)
        sif_data = parser.parse()
        
        print(f"✅ SIF Version: {sif_data.version}")
        print(f"✅ Found {len(sif_data.can_interfaces)} CAN interfaces")
        print(f"✅ Found {len(sif_data.channels)} channels")
        
        # Parse DBC files
        print(f"\n📚 Loading DBC files...")
        for dbc_path in self.dbc_paths:
            db_name = Path(dbc_path).stem
            print(f"   📖 Loading: {db_name}.dbc")
            dbc = DBCParser(dbc_path)
            dbc.parse()
            self.dbc_databases[db_name] = dbc
            print(f"      ✅ {len(dbc.messages)} messages, {len(dbc.get_all_signals())} signals")
        
        # Print CAN interfaces
        print(f"\n📡 CAN Interfaces:")
        for can in sif_data.can_interfaces:
            print(f"   {can.name}: {can.baud_rate} bps")
            print(f"      DBs: {', '.join(can.databases)}")
        
        # Print channels
        print(f"\n📊 Channels (first 10):")
        for i, ch in enumerate(sif_data.channels[:10]):
            print(f"   {i+1}. {ch.name} ({ch.channel_type}) - {ch.units}, {ch.sample_rate} Hz")
        
        print(f"\n🔄 Converting to BLF format...")
        
        # Create BLF writer
        writer = BLFWriter(self.blf_path, application_id="SIF2BLF_v2.0_DBC")
        
        # Get binary data
        binary_data = parser.get_binary_data(sif_data)
        print(f"📦 Binary data size: {len(binary_data):,} bytes")
        
        # Convert data
        self._convert_data(sif_data, binary_data, writer)
        
        # Write BLF file
        print(f"💾 Writing BLF file: {self.blf_path}")
        writer.write()
        
        print(f"\n✅ Conversion completed!")
        print(f"📊 Generated {len(writer.objects):,} BLF objects")
        print(f"\n📈 CANalyzer'da görüntüleme:")
        print(f"   A) Signal grafikler: Data Window → Channels")
        print(f"   B) Raw CAN mesajları: Trace Window → CAN messages")
    
def _convert_data(self, sif_data, binary_data: bytes, writer: BLFWriter):
        """Convert binary data to BLF objects"""
        timestamp_ns = 0
        
        # Calculate time increment based on highest sample rate
        max_rate = max([ch.sample_rate for ch in sif_data.channels])
        time_increment_ns = int(1_000_000_000 / max_rate)
        
        # Estimate number of samples
        num_samples = min(1000, len(binary_data) // 100)
        
        print(f"⚙️  Processing {num_samples} sample points...")
        print(f"   Sample rate: {max_rate} Hz ({time_increment_ns/1000:.1f} μs interval)")
        
        # Map channels to DBC signals
        channel_to_signal = self._map_channels_to_signals(sif_data.channels)
        
        matched = sum(1 for v in channel_to_signal.values() if v is not None)
        print(f"   Matched {matched}/{len(sif_data.channels)} channels to DBC signals")
        
        for i in range(num_samples):
            # Extract sample data from binary (placeholder - needs real decoding)
            sample_data = self._extract_sample_data(binary_data, i, sif_data.channels)
            
            # Group signals by CAN message
            messages_to_send: Dict[int, Dict[str, float]] = {}
            
            for channel, value in sample_data.items():
                # A) Write as signal (ENV_DOUBLE) - for graphs
                signal_name = f"{channel.prefix}.{channel.name}" if channel.prefix else channel.name
                writer.add_env_double(signal_name, value, timestamp_ns)
                
                # B) Encode to CAN message if mapped
                mapping = channel_to_signal.get(channel.name)
                if mapping:
                    db_name, msg_id, signal_name_in_dbc = mapping
                    if db_name in self.dbc_databases:
                        if msg_id not in messages_to_send:
                            messages_to_send[msg_id] = {}
                        messages_to_send[msg_id][signal_name_in_dbc] = value
            
            # Encode and write CAN messages
            for msg_id, signal_values in messages_to_send.items():
                self._write_can_message(writer, msg_id, signal_values, timestamp_ns)
            
            timestamp_ns += time_increment_ns
            
            if (i + 1) % 100 == 0:
                print(f"   Progress: {i+1}/{num_samples}")
    
def _map_channels_to_signals(self, channels: List[Channel]) -> Dict[str, tuple]:
        """Map SIF channels to DBC signals"""
        mapping = {}
        
        for channel in channels:
            found = False
            # Try to find matching signal in DBC databases
            for db_name, dbc in self.dbc_databases.items():
                # Try exact match
                if channel.name in dbc.signal_to_message:
                    msg_id = dbc.signal_to_message[channel.name]
                    mapping[channel.name] = (db_name, msg_id, channel.name)
                    found = True
                    break
                
                # Try fuzzy match (without prefix)
                name_variants = [
                    channel.name,
                    channel.name.replace('_', ''),
                    channel.name.upper(),
                    channel.name.lower()
                ]
                
                for variant in name_variants:
                    if variant in dbc.signal_to_message:
                        msg_id = dbc.signal_to_message[variant]
                        mapping[channel.name] = (db_name, msg_id, variant)
                        found = True
                        break
                
                if found:
                    break
            
            if not found:
                mapping[channel.name] = None
        
        return mapping
    
def _write_can_message(self, writer: BLFWriter, msg_id: int, 
                          signal_values: Dict[str, float], timestamp_ns: int):
        """Encode signals and write CAN message"""
        # Find which DBC contains this message
        for db_name, dbc in self.dbc_databases.items():
            if msg_id in dbc.messages:
                message = dbc.messages[msg_id]
                
                # Encode signals to CAN data
                can_data = message.encode_signals(signal_values)
                
                # Determine channel based on CAN interface
                channel = 1  # Default to channel 1
                
                # Write to BLF
                writer.add_can_message(
                    channel=channel,
                    can_id=msg_id,
                    data=can_data,
                    timestamp_ns=timestamp_ns
                )
                break
    
def _extract_sample_data(self, binary_data: bytes, sample_index: int,
                            channels: List[Channel]) -> Dict[Channel, float]:
        """Extract sample data from binary (placeholder - needs real decoding)"""
        sample_data = {}
        
        # This is still placeholder - real SIF binary format needs analysis
        # For now, use synthetic data based on channel properties
        for i, channel in enumerate(channels):
            # Use binary data with some variation
            offset = (sample_index * len(channels) + i) % len(binary_data)
            raw_byte = binary_data[offset] if offset < len(binary_data) else 0
            
            # Scale to channel range
            normalized = raw_byte / 255.0
            value = channel.fs_min + (channel.fs_max - channel.fs_min) * normalized
            
            # Apply calibration
            value = value * channel.cal_slope + channel.cal_intercept
            
            sample_data[channel] = value
        
        return sample_data

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Convert Somat SIF files to Vector BLF format with DBC support',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument('input', help='Input SIF file path')
    parser.add_argument('output', help='Output BLF file path')
    parser.add_argument('-d', '--dbc', nargs='+', required=True,
                       help='DBC file path(s). Can use wildcards: -d *.dbc')
    parser.add_argument('-v', '--verbose', action='store_true',
                       help='Enable verbose output')
    
    args = parser.parse_args()
    
    # Validate input file
    if not Path(args.input).exists():
        print(f"❌ Error: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)
    
    # Expand wildcards in DBC paths
    dbc_files = []
    for pattern in args.dbc:
        matched = glob.glob(pattern)
        if matched:
            dbc_files.extend(matched)
        else:
            dbc_files.append(pattern)
    
    # Validate DBC files
    for dbc_file in dbc_files:
        if not Path(dbc_file).exists():
            print(f"❌ Error: DBC file not found: {dbc_file}", file=sys.stderr)
            sys.exit(1)
    
    print(f"🎯 SIF to BLF Converter v2.0 with DBC Support\n")
    
    # Perform conversion
    try:
        converter = SIFToBLFConverterV2(args.input, args.output, dbc_files)
        converter.convert()
    except Exception as e:
        print(f"\n❌ Error during conversion: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()