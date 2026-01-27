import pandas as pd
import re
import itertools
import numpy as np
import os


# Define a helper that converts a numeric string (including scientific notation) into a float.
def _to_float(num_str: str) -> float:
    num_str = num_str.strip()
    return float(num_str)


# Define a helper that formats a float into scientific notation as a string.
def _to_sci_str(x: float) -> str:
    return f"{x:.6e}"


# Define a helper that removes common RTF/control-word noise and trailing slashes/braces from a line.
def _clean_line(raw_line: str) -> str:
    # Remove leading/trailing whitespace first.
    s = raw_line.strip()
    # Remove common RTF control-word prefixes like "\f0\fs24 \cf0 " if present.
    s = re.sub(r'^(\\[a-zA-Z]+\d*\s*)+', '', s)
    # Remove a trailing backslash sequence used in some RTF-exported “CSV” lines.
    s = s.rstrip("\\")
    # Remove trailing braces that can appear at the end of an RTF block.
    s = s.rstrip("}")
    # Remove any remaining surrounding whitespace after trimming.
    s = s.strip()
    # Return the cleaned line.
    return s


# Define a helper that extracts “CSV-like” lines from a file that might be plain CSV or RTF-wrapped CSV.
def _extract_csv_lines(file_path: str) -> list[str]:
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        raw_lines = f.read().splitlines()

    cleaned = []
    for line in raw_lines:
        s = _clean_line(line)
        if not s:
            continue
        if "," in s:
            cleaned.append(s)
    return cleaned


# Define a helper that parses a "start:end:step" token into a list of float values.
def _parse_colon_range(token: str) -> list[float]:
    parts = token.split(":")
    if len(parts) != 3:
        raise ValueError(f"Invalid loop token (expected start:end:step): {token}")

    start = _to_float(parts[0])
    end = _to_float(parts[1])
    step = _to_float(parts[2])

    if step == 0:
        raise ValueError(f"Step cannot be zero in loop token: {token}")

    n = int(np.floor((end - start) / step)) + 1 if step > 0 else int(np.floor((start - end) / (-step))) + 1
    vals = [start + i * step for i in range(max(n, 0))]

    if step > 0:
        vals = [v for v in vals if v <= end + 1e-12]
    else:
        vals = [v for v in vals if v >= end - 1e-12]
    return vals


# Define the main function that reads an input CSV path and writes an expanded output CSV.
def expand_colon_loops_csv(input_csv_path) -> str:
    
    lines = _extract_csv_lines(input_csv_path)

    if not lines:
        raise ValueError("No CSV-like lines found in the input file.")

    header_line = lines[0]
    columns = [c.strip() for c in header_line.split(",")]

    template_rows = []
    for line in lines[1:]:
        fields = [f.strip() for f in line.split(",")]
        
        if len(fields) < len(columns):
            fields = fields + [""] * (len(columns) - len(fields))

        template_rows.append(fields)

    loops = []
    for r_idx, row in enumerate(template_rows):
        for c_idx, field in enumerate(row):
            if ":" in field:
                values = _parse_colon_range(field)
                loops.append((r_idx, c_idx, values))

    if not loops:
        df = pd.DataFrame(template_rows, columns=columns[: len(template_rows[0])])

        if output_csv_path is None:
            output_csv_path = input_csv_path.rsplit(".", 1)[0] + "_expanded.csv"

        df.to_csv(output_csv_path, index=False)
        return output_csv_path

    loop_value_lists = [loop[2] for loop in loops]

    loop_position_to_loop_idx = {(r, c): i for i, (r, c, _) in enumerate(loops)}

    expanded_rows = []

    for combo in itertools.product(*loop_value_lists):
        for r_idx, row in enumerate(template_rows):
            new_row = list(row)
            for c_idx, field in enumerate(new_row):
                if (r_idx, c_idx) in loop_position_to_loop_idx:
                    loop_idx = loop_position_to_loop_idx[(r_idx, c_idx)]
                    new_row[c_idx] = _to_sci_str(combo[loop_idx])
            expanded_rows.append(new_row)

    df_out = pd.DataFrame(expanded_rows, columns=columns[: len(expanded_rows[0])])

    output_csv_path = input_csv_path.rsplit(".", 1)[0] + "_expanded.csv"

    df_out.to_csv(output_csv_path, index=False)

    return output_csv_path
