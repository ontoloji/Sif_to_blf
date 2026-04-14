"""
SIF to BLF Converter v2.0
Converts Somat eDAQ SIF files to Vector BLF format with DBC support
"""

import argparse
import glob
import struct
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from blf_writer import BLFWriter
from dbc_parser import DBCParser
from sif_parser import Channel, SIFParser


class SIFToBLFConverterV2:
    """Main converter class with DBC support"""

    def __init__(
        self,
        sif_path: str,
        blf_path: str,
        dbc_paths: List[str],
        auto_align: bool = True,
        align_search_bytes: int = 128,
    ):
        self.sif_path = sif_path
        self.blf_path = blf_path
        self.dbc_paths = dbc_paths
        self.auto_align = auto_align
        self.align_search_bytes = max(1, align_search_bytes)
        self.dbc_databases: Dict[str, DBCParser] = {}

    def convert(self):
        """Perform the conversion"""
        print(f"Parsing SIF file: {self.sif_path}")

        parser = SIFParser(self.sif_path)
        sif_data = parser.parse()

        print(f"SIF Version: {sif_data.version}")
        print(f"Found {len(sif_data.can_interfaces)} CAN interfaces")
        print(f"Found {len(sif_data.channels)} channels")

        print("\nLoading DBC files...")
        for dbc_path in self.dbc_paths:
            db_name = Path(dbc_path).stem
            print(f"  Loading: {db_name}.dbc")
            dbc = DBCParser(dbc_path)
            dbc.parse()
            self.dbc_databases[db_name] = dbc
            print(f"    {len(dbc.messages)} messages, {len(dbc.get_all_signals())} signals")

        print("\nCAN Interfaces:")
        for can in sif_data.can_interfaces:
            print(f"  {can.name}: {can.baud_rate} bps")
            print(f"    DBs: {', '.join(can.databases)}")

        print("\nChannels (first 10):")
        for i, ch in enumerate(sif_data.channels[:10]):
            print(f"  {i + 1}. {ch.name} ({ch.channel_type}) - {ch.units}, {ch.sample_rate} Hz")

        print("\nConverting to BLF format...")

        writer = BLFWriter(self.blf_path, application_id="SIF2BLF_v2.0_DBC")
        binary_data = parser.get_binary_data(sif_data)
        print(f"Binary data size: {len(binary_data):,} bytes")

        self._convert_data(sif_data.channels, binary_data, writer)

        print(f"Writing BLF file: {self.blf_path}")
        writer.write()

        print("\nConversion completed")
        print(f"Generated {len(writer.objects):,} BLF objects")

    def _convert_data(self, channels: List[Channel], binary_data: bytes, writer: BLFWriter):
        """Convert binary data to BLF objects"""
        if not channels:
            print("No channels found, nothing to convert")
            return

        if not binary_data:
            print("No binary data found, nothing to convert")
            return

        timestamp_ns = 0
        max_rate = max(ch.sample_rate for ch in channels if ch.sample_rate > 0)
        time_increment_ns = int(1_000_000_000 / max_rate)

        sample_stride = self._sample_stride_bytes(channels)
        num_samples = max(1, min(1000, len(binary_data) // sample_stride))

        base_offset = 0
        if self.auto_align:
            base_offset = self._find_best_base_offset(binary_data, channels, num_samples, sample_stride)
            print(f"  Auto align selected base offset: {base_offset} bytes")

        print(f"Processing {num_samples} sample points...")
        print(f"  Sample rate: {max_rate} Hz ({time_increment_ns / 1000:.1f} us interval)")

        channel_to_signal = self._map_channels_to_signals(channels)
        matched = sum(1 for v in channel_to_signal.values() if v is not None)
        print(f"  Matched {matched}/{len(channels)} channels to DBC signals")

        for i in range(num_samples):
            sample_data = self._extract_sample_data(binary_data, i, channels, base_offset=base_offset)
            messages_to_send: Dict[int, Dict[str, float]] = {}

            for channel, value in sample_data:
                signal_name = f"{channel.prefix}.{channel.name}" if channel.prefix else channel.name
                writer.add_env_double(signal_name, value, timestamp_ns)

                mapping = channel_to_signal.get(channel.name)
                if mapping:
                    db_name, msg_id, signal_name_in_dbc = mapping
                    if db_name in self.dbc_databases:
                        if msg_id not in messages_to_send:
                            messages_to_send[msg_id] = {}
                        messages_to_send[msg_id][signal_name_in_dbc] = value

            for msg_id, signal_values in messages_to_send.items():
                self._write_can_message(writer, msg_id, signal_values, timestamp_ns)

            if not messages_to_send:
                fallback_data = self._build_fallback_can_payload(binary_data, i, sample_stride, base_offset)
                writer.add_can_message(
                    channel=1,
                    can_id=0x700,
                    data=fallback_data,
                    timestamp_ns=timestamp_ns,
                )

            timestamp_ns += time_increment_ns

            if (i + 1) % 100 == 0:
                print(f"  Progress: {i + 1}/{num_samples}")

    def _map_channels_to_signals(
        self, channels: List[Channel]
    ) -> Dict[str, Optional[Tuple[str, int, str]]]:
        """Map SIF channels to DBC signals"""
        mapping: Dict[str, Optional[Tuple[str, int, str]]] = {}

        for channel in channels:
            found = False

            for db_name, dbc in self.dbc_databases.items():
                if channel.name in dbc.signal_to_message:
                    msg_id = dbc.signal_to_message[channel.name]
                    mapping[channel.name] = (db_name, msg_id, channel.name)
                    found = True
                    break

                name_variants = [
                    channel.name,
                    channel.name.replace("_", ""),
                    channel.name.upper(),
                    channel.name.lower(),
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

    def _write_can_message(
        self,
        writer: BLFWriter,
        msg_id: int,
        signal_values: Dict[str, float],
        timestamp_ns: int,
    ):
        """Encode signals and write CAN message"""
        for dbc in self.dbc_databases.values():
            if msg_id in dbc.messages:
                message = dbc.messages[msg_id]
                can_data = message.encode_signals(signal_values)
                writer.add_can_message(
                    channel=1,
                    can_id=msg_id,
                    data=can_data,
                    timestamp_ns=timestamp_ns,
                )
                break

    def _extract_sample_data(
        self,
        binary_data: bytes,
        sample_index: int,
        channels: List[Channel],
        base_offset: int = 0,
    ) -> List[Tuple[Channel, float]]:
        """Extract sample data with a channel-interleaved 16-bit heuristic."""
        sample_data: List[Tuple[Channel, float]] = []

        if not binary_data or not channels:
            return sample_data

        sample_stride = self._sample_stride_bytes(channels)
        sample_base_offset = base_offset + (sample_index * sample_stride)

        channel_offset = 0

        for channel in channels:
            width = self._channel_byte_width(channel)
            offset = sample_base_offset + channel_offset
            channel_offset += width

            raw_chunk = self._read_chunk_with_wrap(binary_data, offset, width)

            normalized = self._normalize_channel_raw(raw_chunk, channel)

            # Prefer engineering full-scale range when present; otherwise fallback to calibration.
            if channel.fs_min == 0.0 and channel.fs_max == 1.0:
                value = normalized * channel.cal_slope + channel.cal_intercept
            else:
                value = channel.fs_min + (channel.fs_max - channel.fs_min) * normalized

            sample_data.append((channel, value))

        return sample_data

    def _find_best_base_offset(
        self,
        binary_data: bytes,
        channels: List[Channel],
        num_samples: int,
        sample_stride: int,
    ) -> int:
        """Probe multiple base offsets and select the one with the healthiest signal dynamics."""
        if not channels or not binary_data or num_samples <= 2:
            return 0

        search_space = min(sample_stride, self.align_search_bytes)
        probe_samples = min(200, num_samples)
        probe_step = max(1, num_samples // probe_samples)

        # Use a small subset of channels so probing stays fast.
        probe_channels = channels[: min(8, len(channels))]

        best_offset = 0
        best_score = float("-inf")

        for candidate in range(search_space):
            score = self._score_offset_candidate(
                binary_data,
                channels,
                probe_channels,
                candidate,
                probe_step,
                num_samples,
            )

            if score > best_score:
                best_score = score
                best_offset = candidate

        return best_offset

    def _score_offset_candidate(
        self,
        binary_data: bytes,
        all_channels: List[Channel],
        probe_channels: List[Channel],
        candidate_offset: int,
        probe_step: int,
        num_samples: int,
    ) -> float:
        """Higher score means richer dynamics and fewer saturated values."""
        if not probe_channels:
            return 0.0

        prev_values: Optional[List[float]] = None
        transitions = 0
        clipped = 0
        total = 0

        # Map probe channel names to values quickly from full sample extraction.
        probe_names = {channel.name for channel in probe_channels}

        for sample_index in range(0, num_samples, probe_step):
            sample = self._extract_sample_data(
                binary_data,
                sample_index,
                all_channels,
                base_offset=candidate_offset,
            )

            current_values: List[float] = []
            for channel, value in sample:
                if channel.name in probe_names:
                    current_values.append(value)

                    eps = max(1e-9, abs(channel.fs_max - channel.fs_min) * 1e-3)
                    if value <= channel.fs_min + eps or value >= channel.fs_max - eps:
                        clipped += 1
                    total += 1

            if prev_values is not None and current_values and len(current_values) == len(prev_values):
                transitions += sum(1 for old, new in zip(prev_values, current_values) if abs(new - old) > 1e-9)

            prev_values = current_values

        if total == 0:
            return float("-inf")

        clip_ratio = clipped / total
        # Encourage changing signals, penalize offsets that often pin to min/max.
        return transitions - (clip_ratio * 200.0)

    def _sample_stride_bytes(self, channels: List[Channel]) -> int:
        """Total bytes consumed by one interleaved sample across all channels."""
        return max(1, sum(self._channel_byte_width(channel) for channel in channels))

    def _channel_byte_width(self, channel: Channel) -> int:
        """Infer byte-width from VB/CHAN type metadata."""
        if channel.vb_sig_data_type == 800:
            return 8
        if channel.vb_sig_data_type in (288,):
            return 4
        if channel.vb_sig_data_type in (272,):
            return 2
        if channel.vb_sig_data_type in (264,):
            return 1

        if channel.chan_data_type == 784:
            return 2
        if channel.chan_data_type == 32:
            return 4

        return 2

    def _read_chunk_with_wrap(self, binary_data: bytes, offset: int, width: int) -> bytes:
        if offset + width <= len(binary_data):
            return binary_data[offset : offset + width]

        wrapped = offset % max(1, len(binary_data) - 1)
        return binary_data[wrapped : wrapped + width].ljust(width, b"\x00")

    def _normalize_channel_raw(self, raw_chunk: bytes, channel: Channel) -> float:
        """Decode raw bytes and convert to normalized 0..1 range."""
        if channel.vb_sig_data_type == 800:
            try:
                raw_float = struct.unpack("<d", raw_chunk)[0]
                return self._normalize_by_fs(raw_float, channel)
            except struct.error:
                return 0.0

        if channel.chan_data_type == 32 and channel.vb_sig_data_type == 0:
            try:
                raw_float32 = struct.unpack("<f", raw_chunk)[0]
                return self._normalize_by_fs(raw_float32, channel)
            except struct.error:
                return 0.0

        raw_int = int.from_bytes(raw_chunk, "little", signed=False)
        max_raw = (1 << (8 * len(raw_chunk))) - 1
        if max_raw <= 0:
            return 0.0
        return max(0.0, min(1.0, raw_int / max_raw))

    def _normalize_by_fs(self, value: float, channel: Channel) -> float:
        span = channel.fs_max - channel.fs_min
        if span <= 0:
            return 0.0

        normalized = (value - channel.fs_min) / span
        return max(0.0, min(1.0, normalized))

    def _build_fallback_can_payload(
        self,
        binary_data: bytes,
        sample_index: int,
        sample_stride: int,
        base_offset: int,
    ) -> bytes:
        """Create deterministic 8-byte payload when no DBC mapping is available."""
        offset = base_offset + (sample_index * sample_stride)
        if offset + 8 <= len(binary_data):
            return binary_data[offset : offset + 8]

        wrapped = offset % max(1, len(binary_data) - 1)
        return binary_data[wrapped : wrapped + 8].ljust(8, b"\x00")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Convert Somat SIF files to Vector BLF format with DBC support",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("input", help="Input SIF file path")
    parser.add_argument("output", help="Output BLF file path")
    parser.add_argument(
        "-d",
        "--dbc",
        nargs="+",
        required=True,
        help="DBC file path(s). Can use wildcards: -d *.dbc",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument(
        "--no-auto-align",
        action="store_true",
        help="Disable automatic base-offset alignment for binary samples",
    )
    parser.add_argument(
        "--align-search-bytes",
        type=int,
        default=128,
        help="How many initial byte offsets to probe during auto-alignment",
    )

    args = parser.parse_args()

    if not Path(args.input).exists():
        print(f"Error: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    dbc_files = []
    for pattern in args.dbc:
        matched = glob.glob(pattern)
        if matched:
            dbc_files.extend(matched)
        else:
            dbc_files.append(pattern)

    for dbc_file in dbc_files:
        if not Path(dbc_file).exists():
            print(f"Error: DBC file not found: {dbc_file}", file=sys.stderr)
            sys.exit(1)

    print("SIF to BLF Converter v2.0 with DBC Support\n")

    try:
        converter = SIFToBLFConverterV2(
            args.input,
            args.output,
            dbc_files,
            auto_align=not args.no_auto_align,
            align_search_bytes=args.align_search_bytes,
        )
        converter.convert()
    except Exception as e:
        print(f"\nError during conversion: {e}", file=sys.stderr)
        if args.verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
