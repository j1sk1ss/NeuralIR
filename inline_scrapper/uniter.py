import json
import csv
import argparse


DEFAULT_INLINE_JSON = "dumped_inlines.json"
DEFAULT_OTHER_JSON = "dumped_other.json"
DEFAULT_OUTPUT_CSV = "dataset_flat.csv"


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_records(data, file_name):
    if not isinstance(data, list):
        raise ValueError(f"{file_name} must contain a JSON array")
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError(f"Item #{i} in {file_name} is not an object")


def flatten_json(obj, prefix=""):
    result = {}

    if isinstance(obj, dict):
        for key, value in obj.items():
            new_key = f"{prefix}.{key}" if prefix else str(key)
            result.update(flatten_json(value, new_key))

    elif isinstance(obj, list):
        if not obj:
            result[prefix] = ""
        else:
            for i, value in enumerate(obj):
                new_key = f"{prefix}.{i}" if prefix else str(i)
                result.update(flatten_json(value, new_key))

    else:
        result[prefix] = obj

    return result


def build_rows(path, is_inlined):
    data = load_json(path)
    validate_records(data, path)

    rows = []
    for item in data:
        row = flatten_json(item)
        row["is_inlined"] = is_inlined
        rows.append(row)

    return rows


def collect_columns(rows):
    columns = set()

    for row in rows:
        columns.update(row.keys())

    columns = {
        col for col in columns
        if not any(other.startswith(col + ".") for other in columns)
    }

    preferred_order = [
        "caller.owner",
        "caller.action",
        "caller.called_function",
        "caller.block_id",
        "caller.instruction_info.is_dom",
        "caller.instruction_info.near_break",
        "caller.instruction_info.same_inst_before",
        "caller.instruction_info.same_inst_after",
        "callee.name",
        "callee.info.bb_count",
        "callee.info.funccalls",
        "callee.info.ir_count",
        "callee.info.is_start",
        "callee.info.syscalls",
        "is_inlined",
    ]

    loop_columns = sorted(col for col in columns if col.startswith("caller.loop_info."))

    ordered = []
    used = set()

    for col in preferred_order:
        if col in columns:
            ordered.append(col)
            used.add(col)

    for col in loop_columns:
        if col not in used:
            ordered.append(col)
            used.add(col)

    for col in sorted(columns):
        if col not in used:
            ordered.append(col)

    return ordered


def write_csv(rows, output_path):
    columns = collect_columns(rows)

    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()

        for row in rows:
            normalized_row = {col: row.get(col, "") for col in columns}
            writer.writerow(normalized_row)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Convert two JSON files into one flattened CSV with is_inlined label"
    )
    parser.add_argument(
        "--inlines",
        default=DEFAULT_INLINE_JSON,
        help=f"Path to JSON file with inlined records (default: {DEFAULT_INLINE_JSON})",
    )
    parser.add_argument(
        "--other",
        default=DEFAULT_OTHER_JSON,
        help=f"Path to JSON file with non-inlined records (default: {DEFAULT_OTHER_JSON})",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=DEFAULT_OUTPUT_CSV,
        help=f"Path to output CSV file (default: {DEFAULT_OUTPUT_CSV})",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    print(f"Loading {args.inlines}")
    inline_rows = build_rows(args.inlines, 1)

    print(f"Loading {args.other}")
    other_rows = build_rows(args.other, 0)

    all_rows = inline_rows + other_rows

    print(f"Writing CSV to {args.output}")
    write_csv(all_rows, args.output)

    print("Done")
    print(f"Total rows: {len(all_rows)}")
    print(f"Inlined rows: {len(inline_rows)}")
    print(f"Other rows: {len(other_rows)}")


if __name__ == "__main__":
    main()