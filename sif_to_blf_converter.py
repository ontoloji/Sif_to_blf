"""
SIF to BLF Converter
Converts Somat eDAQ SIF files to Vector BLF format
"""

import argparse
import sys
from pathlib import Path
from sif_parser import SIFParser
from blf_writer import BLFWriter
import struct


class SIFToBLFConverter:
    """Main converter class"""
    
    def __init__(self, sif_path: str, blf_path: str):
        self.sif_path = sif_path
        self.blf_path = blf_path
        
    def convert(self):
        """Perform the conversion"""
        print(f"🔍 Parsing SIF file: {self.sif_path}")
        
        # Parse SIF file
        parser = SIFParser(self.sif_path)
        sif_data = parser.parse()
        
        print(f"✅ SIF Version: {sif_data.version}")
        print(f"✅ Found {len(sif_data.can_interfaces)} CAN interfaces")
        print(f"✅ Found {len(sif_data.channels)} channels")
        
        # Print CAN interfaces
        for can in sif_data.can_interfaces:
            print(f"   📡 {can.name}: {can.baud_rate} bps, DBs: {', '.join(can.databases)}")
        
        # Print some channels
        print(f"\n📊 Channels (showing first 5):")
        for i, ch in enumerate(sif_data.channels[:5]):
            print(f"   {i+1}. {ch.name} ({ch.channel_type}) - {ch.units}, {ch.sample_rate} Hz")
        
        print(f"\n🔄 Converting to BLF format...")
        
        # Create BLF writer
        writer = BLFWriter(self.blf_path, application_id="SIF2BLF_v1.0")
        
        # Get binary data
        binary_data = parser.get_binary_data(sif_data)
        print(f"📦 Binary data size: {len(binary_data):,} bytes")
        
        # Convert data
        self._convert_data(sif_data, binary_data, writer)
        
        # Write BLF file
        print(f"💾 Writing BLF file: {self.blf_path}")
        writer.write()
        
        print(f"✅ Conversion completed!")
        print(f"📊 Generated {len(writer.objects):,} BLF objects")
    
    def _convert_data(self, sif_data, binary_data: bytes, writer: BLFWriter):
        """Convert binary data to BLF objects"""
        # This is a simplified conversion
        # Real implementation needs to understand the binary data structure
        
        # For demonstration, let's create some sample CAN messages
        # based on the channel data
        
        timestamp_ns = 0
        time_increment_ns = 1_000_000  # 1ms
        
        # Example: Create CAN messages for channels
        # In reality, you'd need to decode the actual binary data format
        
        # Group channels by sample rate
        channels_by_rate = {}
        for ch in sif_data.channels:
            if ch.sample_rate not in channels_by_rate:
                channels_by_rate[ch.sample_rate] = []
            channels_by_rate[ch.sample_rate].append(ch)
        
        # Try to extract some sample data
        # This is placeholder - real SIF binary format needs reverse engineering
        num_samples = min(1000, len(binary_data) // 100)  # Estimate
        
        print(f"⚙️  Generating {num_samples} sample messages...")
        
        for i in range(num_samples):
            # Create sample CAN messages for each interface
            for idx, can_if in enumerate(sif_data.can_interfaces):
                channel = idx + 1
                
                # Generate sample CAN message
                can_id = 0x100 + i % 256
                
                # Create sample data from binary (or synthetic)
                data_offset = (i * 8) % len(binary_data)
                data = binary_data[data_offset:data_offset+8]
                if len(data) < 8:
                    data = data.ljust(8, b'\x00')
                
                writer.add_can_message(
                    channel=channel,
                    can_id=can_id,
                    data=data,
                    timestamp_ns=timestamp_ns
                )
            
            timestamp_ns += time_increment_ns


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Convert Somat SIF files to Vector BLF format',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument('input', help='Input SIF file path')
    parser.add_argument('output', help='Output BLF file path')
    parser.add_argument('-v', '--verbose', action='store_true',
                       help='Enable verbose output')
    
    args = parser.parse_args()
    
    # Validate input file
    if not Path(args.input).exists():
        print(f"❌ Error: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)
    
    # Perform conversion
    try:
        converter = SIFToBLFConverter(args.input, args.output)
        converter.convert()
    except Exception as e:
        print(f"❌ Error during conversion: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()