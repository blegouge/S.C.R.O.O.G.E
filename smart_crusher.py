#!/usr/bin/env python3
"""
Local SmartCrusher engine: compresses JSON and raw logs.
Keeps first N elements/lines, last M elements/lines, and any containing anomalies.
"""

import json
from typing import Any


def _is_anomaly(item: Any) -> bool:
    if item is None:
        return False

    # If dictionary, perform structural checks
    if isinstance(item, dict):
        for ok_key in ("ok", "success"):
            if ok_key in item:
                val = item[ok_key]
                if isinstance(val, bool) and not val:
                    return True
                if isinstance(val, str) and val.lower() in ("false", "0", "fail", "no"):
                    return True

        for status_key in ("status", "status_code", "statusCode", "code"):
            if status_key in item:
                val = item[status_key]
                if isinstance(val, (int, float)):
                    if 400 <= val < 600:
                        return True
                elif isinstance(val, str):
                    if val.isdigit():
                        code = int(val)
                        if 400 <= code < 600:
                            return True
                    elif any(word in val.lower() for word in ("err", "fail", "warn", "excep")):
                        return True

    # Check serialized representation or string
    if isinstance(item, (dict, list)):
        try:
            val_str = json.dumps(item)
        except Exception:
            val_str = str(item)
    else:
        val_str = str(item)

    val_lower = val_str.lower()
    keywords = ("error", "exception", "fail", "warning", "traceback")
    for kw in keywords:
        if kw in val_lower:
            return True

    return False


def _compress_json_data(data: Any, n: int, m: int) -> tuple[Any, bool]:
    if isinstance(data, list):
        if len(data) <= n + m:
            modified = False
            new_list = []
            for item in data:
                compressed_item, item_modified = _compress_json_data(item, n, m)
                new_list.append(compressed_item)
                if item_modified:
                    modified = True
            return new_list, modified

        # Prune middle elements
        first_part = data[:n]
        middle_part = data[n:-m]
        last_part = data[-m:]

        new_first = []
        for item in first_part:
            compressed_item, _ = _compress_json_data(item, n, m)
            new_first.append(compressed_item)

        new_last = []
        for item in last_part:
            compressed_item, _ = _compress_json_data(item, n, m)
            new_last.append(compressed_item)

        new_middle = []
        pruned_count = 0
        for item in middle_part:
            if _is_anomaly(item):
                compressed_item, _ = _compress_json_data(item, n, m)
                if pruned_count > 0:
                    new_middle.append({"_pruned_count": pruned_count})
                    pruned_count = 0
                new_middle.append(compressed_item)
            else:
                pruned_count += 1

        if pruned_count > 0:
            new_middle.append({"_pruned_count": pruned_count})

        return new_first + new_middle + new_last, True

    elif isinstance(data, dict):
        modified = False
        new_dict = {}
        for k, v in data.items():
            compressed_val, val_modified = _compress_json_data(v, n, m)
            new_dict[k] = compressed_val
            if val_modified:
                modified = True
        return new_dict, modified

    return data, False


def _compress_text_lines(text: str, n: int, m: int) -> str:
    lines = text.splitlines()
    if len(lines) <= n + m:
        return text

    first_part = lines[:n]
    middle_part = lines[n:-m]
    last_part = lines[-m:]

    new_middle = []
    pruned_count = 0
    for line in middle_part:
        if _is_anomaly(line):
            if pruned_count > 0:
                new_middle.append(f"... [PRUNED {pruned_count} LINES] ...")
                pruned_count = 0
            new_middle.append(line)
        else:
            pruned_count += 1

    if pruned_count > 0:
        new_middle.append(f"... [PRUNED {pruned_count} LINES] ...")

    all_lines = first_part + new_middle + last_part
    suffix = "\n" if text.endswith("\n") else ""
    return "\n".join(all_lines) + suffix


class SmartCrusherConfig:
    def __init__(self, n: int | None = None, m: int | None = None):
        from telemetry_config import config

        self.n = n if n is not None else config.smart_crusher_n
        self.m = m if m is not None else config.smart_crusher_m


class SmartCrusher:
    def __init__(self, config: SmartCrusherConfig | None = None):
        self.config = config or SmartCrusherConfig()

    def compress(self, text: str) -> str:
        if not text:
            return text

        trimmed = text.strip()
        # 1. Try single JSON object or array
        if (trimmed.startswith("{") and trimmed.endswith("}")) or (
            trimmed.startswith("[") and trimmed.endswith("]")
        ):
            try:
                data = json.loads(trimmed)
                compressed_data, modified = _compress_json_data(data, self.config.n, self.config.m)
                if modified:
                    return json.dumps(compressed_data, ensure_ascii=False, indent=2)
            except ValueError:
                pass

        # 2. Try JSON lines
        lines = text.splitlines()
        if lines:
            try:
                parsed_lines = []
                is_json_lines = True
                for line in lines:
                    line_trimmed = line.strip()
                    if not line_trimmed:
                        continue
                    if not (
                        (line_trimmed.startswith("{") and line_trimmed.endswith("}"))
                        or (line_trimmed.startswith("[") and line_trimmed.endswith("]"))
                    ):
                        is_json_lines = False
                        break
                    parsed_lines.append(json.loads(line_trimmed))

                if is_json_lines and parsed_lines:
                    compressed_list, modified = _compress_json_data(
                        parsed_lines, self.config.n, self.config.m
                    )
                    if modified:
                        out_lines = []
                        for item in compressed_list:
                            out_lines.append(json.dumps(item, ensure_ascii=False))
                        suffix = "\n" if text.endswith("\n") else ""
                        return "\n".join(out_lines) + suffix
            except ValueError:
                pass

        # 3. Fallback to raw text line-by-line compression
        return _compress_text_lines(text, self.config.n, self.config.m)
