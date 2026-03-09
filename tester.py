#!/usr/bin/env python3
from __future__ import annotations

import argparse
import difflib
import io
import sys
from contextlib import redirect_stdout
from dataclasses import dataclass
from pathlib import Path

from parser.parser import Parser, ParserConfig, Language
from analysis.analyzer import ProgramAnalysis

SUPPORTED_EXTENSIONS = {".cpl", ".c", ".cpp"}

@dataclass
class TestCase:
    path: Path
    lang: Language
    code: str
    expected: str

def detect_language(path: Path) -> Language:
    return Language.C if path.suffix.lower() in {".c", ".cpp"} else Language.CPL

def normalize_text(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n").strip()

def extract_cpl_sections(text: str) -> tuple[str, str]:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")

    start_idx = None
    for i, line in enumerate(lines):
        if line.strip() in {": OUTPUT", ": OUPUT"}:
            start_idx = i
            break

    if start_idx is None:
        raise ValueError("': OUTPUT' not found!")

    end_idx = None
    for i in range(start_idx + 1, len(lines)):
        if lines[i].strip() == ":":
            end_idx = i
            break

    if end_idx is None:
        raise ValueError("Expected ':' at the end!")

    code = "\n".join(lines[:start_idx]).rstrip()
    expected = "\n".join(lines[start_idx + 1:end_idx]).rstrip()
    return code, expected

def extract_c_like_sections(text: str) -> tuple[str, str]:
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    start = text.find("/*")
    while start != -1:
        end = text.find("*/", start + 2)
        if end == -1:
            raise ValueError("Comment isn't closed /* ... */")

        block = text[start + 2:end]
        stripped = block.lstrip()

        if stripped.startswith("OUTPUT") or stripped.startswith("OUPUT"):
            header = "OUTPUT" if stripped.startswith("OUTPUT") else "OUPUT"
            rest = stripped[len(header):]
            if rest.startswith("\n"):
                rest = rest[1:]

            code = text[:start].rstrip()
            expected = rest.rstrip()
            return code, expected

        start = text.find("/*", end + 2)

    raise ValueError("'/* OUTPUT ... */' not found!")

def extract_test_case(path: Path) -> TestCase:
    raw = path.read_text(encoding="utf-8")
    lang = detect_language(path)

    if lang == Language.CPL:
        code, expected = extract_cpl_sections(raw)
    else:
        code, expected = extract_c_like_sections(raw)

    return TestCase(
        path=path,
        lang=lang,
        code=normalize_text(code),
        expected=normalize_text(expected),
    )

def build_analysis_output(code: str, lang: Language) -> str:
    analyzer = ProgramAnalysis(
        parser=Parser(
            conf=ParserConfig(
                code=code,
                lang=lang,
            )
        )
    )

    buf = io.StringIO()
    with redirect_stdout(buf):
        analyzer.print_ir()
        for call in analyzer.all_calls():
            print(call.dump_to_json())
        for name, data in analyzer.functions.items():
            print(f"function={name}, info={data.dump_to_json()}")

    return normalize_text(buf.getvalue())

def make_diff(expected: str, actual: str, filename: str) -> str:
    diff = difflib.unified_diff(
        expected.splitlines(),
        actual.splitlines(),
        fromfile=f"{filename} (expected)",
        tofile=f"{filename} (actual)",
        lineterm="",
    )
    return "\n".join(diff)

def iter_source_files(root: Path) -> list[Path]:
    return sorted(
        p for p in root.rglob("*")
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
    )

def run_test(path: Path) -> bool:
    try:
        case = extract_test_case(path)
        actual = build_analysis_output(case.code, case.lang)
    except Exception as e:
        print(f"[ERROR] {path}: {e}")
        return False

    if case.expected == actual:
        print(f"[OK]   {path}")
        return True

    print(f"[FAIL] {path}")
    print(make_diff(case.expected, actual, str(path)))
    print()
    return False

def main() -> int:
    argp = argparse.ArgumentParser()
    argp.add_argument("folder", type=Path)
    args = argp.parse_args()

    if not args.folder.exists():
        print(f"Path wasn't found: {args.folder}", file=sys.stderr)
        return 2
    if not args.folder.is_dir():
        print(f"This is not a directory: {args.folder}", file=sys.stderr)
        return 2

    files = iter_source_files(args.folder)
    if not files:
        print("There is no .cpl/.c/.cpp files")
        return 0

    passed = 0
    for path in files:
        if run_test(path):
            passed += 1

    total = len(files)
    failed = total - passed

    print("-" * 60)
    print(f"TOTAL: {total}, PASSED: {passed}, FAILED: {failed}")

    return 0 if failed == 0 else 1

if __name__ == "__main__":
    raise SystemExit(main())
