#!/usr/bin/env python3
"""Patch generated TTS WAV files with finite RIFF/data chunk sizes.

OpenAI's WAV responses can use 0xFFFFFFFF for RIFF and data chunk sizes, which
works for some streaming decoders but breaks Godot's WAV importer. This script
keeps the PCM payload unchanged and writes conventional RIFF sizes.
"""

from __future__ import annotations

import argparse
import struct
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DIR = ROOT / "audio" / "generated"


def patch_wav(path: Path, dry_run: bool = False) -> bool:
    data = bytearray(path.read_bytes())
    if len(data) < 44:
        raise ValueError(f"{path} is too small to be a WAV file")
    if data[0:4] != b"RIFF" or data[8:12] != b"WAVE":
        raise ValueError(f"{path} is not a RIFF/WAVE file")

    offset = 12
    data_offset = -1
    data_size_offset = -1
    while offset + 8 <= len(data):
        chunk_id = bytes(data[offset : offset + 4])
        chunk_size = struct.unpack_from("<I", data, offset + 4)[0]
        payload_offset = offset + 8
        if chunk_id == b"data":
            data_offset = payload_offset
            data_size_offset = offset + 4
            break
        if chunk_size == 0xFFFFFFFF:
            raise ValueError(f"{path} has unsupported unknown-size non-data chunk {chunk_id!r}")
        offset = payload_offset + chunk_size + (chunk_size % 2)

    if data_offset < 0:
        raise ValueError(f"{path} has no data chunk")

    riff_size = len(data) - 8
    data_size = len(data) - data_offset
    current_riff_size = struct.unpack_from("<I", data, 4)[0]
    current_data_size = struct.unpack_from("<I", data, data_size_offset)[0]
    changed = current_riff_size != riff_size or current_data_size != data_size
    if changed and not dry_run:
        struct.pack_into("<I", data, 4, riff_size)
        struct.pack_into("<I", data, data_size_offset, data_size)
        path.write_bytes(data)
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", type=Path, help="WAV files or directories. Defaults to audio/generated.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    targets = args.paths or [DEFAULT_DIR]
    wavs: list[Path] = []
    for target in targets:
        path = target if target.is_absolute() else ROOT / target
        if path.is_dir():
            wavs.extend(sorted(path.rglob("*.wav")))
        elif path.suffix.lower() == ".wav":
            wavs.append(path)

    changed_count = 0
    for wav in wavs:
        if patch_wav(wav, args.dry_run):
            changed_count += 1
            print(f"patched {wav.relative_to(ROOT)}")
    print(f"TTS_WAV_HEADER_FIX checked={len(wavs)} patched={changed_count} dry_run={args.dry_run}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
