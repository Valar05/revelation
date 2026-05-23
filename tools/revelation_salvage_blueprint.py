#!/usr/bin/env python3
"""Salvage common Claude JSON blueprint response mistakes."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def remove_first_object_close_before_anchors(text: str) -> str:
    decoder = json.JSONDecoder()
    try:
        _, end = decoder.raw_decode(text)
    except json.JSONDecodeError:
        return text
    if text[end:].lstrip().startswith(',"anchors"'):
        return text[: end - 1] + text[end:]
    return text


def remove_extra_plan_closers(text: str) -> str:
    # The compact blueprint contract uses flat plan fields, not nested plan
    # objects. Claude sometimes closes an imagined nested outcome object before
    # the next plan or before the plans array closes.
    return text.replace('"}},{"label":', '"},{"label":').replace('"}}]},"resolution"', '"}]},"resolution"').replace(
        '"}}]},"cooldown"', '"}]},"cooldown"'
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("raw")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    raw = Path(args.raw)
    out = Path(args.out)
    text = raw.read_text(encoding="utf-8").strip()
    candidates = [
        text,
        remove_first_object_close_before_anchors(text),
        remove_extra_plan_closers(remove_first_object_close_before_anchors(text)),
    ]
    decoder = json.JSONDecoder()
    last_error: Exception | None = None
    for candidate in candidates:
        try:
            obj, end = decoder.raw_decode(candidate)
            remainder = candidate[end:].strip()
            if remainder:
                continue
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            print(f"salvaged {raw} -> {out}")
            return 0
        except json.JSONDecodeError as exc:
            last_error = exc
    if last_error:
        print(last_error)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
