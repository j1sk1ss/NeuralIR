#!/usr/bin/env python3
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import csv
from pathlib import Path
from typing import Dict, List

def parse_inline_report(file_path: str) -> List[Dict]:
    results = []
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                m = re.search(r'^(\S+?):(\d+):(\d+):.*?inlining\s+(\w+)/\d+\s+into\s+(\w+)/\d+', line, re.IGNORECASE)
                if m:
                    results.append({
                        'file': m.group(1),
                        'line': int(m.group(2)),
                        'column': int(m.group(3)),
                        'callee': m.group(4),
                        'caller': m.group(5),
                        'raw': line
                    })
    except Exception:
        pass
    return results

def collect_reports(report_dir: str) -> List[Dict]:
    all_events = []
    for txt_file in Path(report_dir).glob("*.inline.txt"):
        all_events.extend(parse_inline_report(str(txt_file)))
    return all_events

def export_to_csv(events: List[Dict], filename: str):
    if not events:
        return
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['file', 'line', 'column', 'callee', 'caller', 'raw'])
        writer.writeheader()
        for ev in events:
            writer.writerow({
                'file': ev['file'],
                'line': ev['line'],
                'column': ev['column'],
                'callee': ev['callee'],
                'caller': ev['caller'],
                'raw': ev.get('raw', '')
            })

def print_summary(events: List[Dict]) -> None:
    if not events:
        print("No inlining events found.")
        return
    print("\n=== GCC INLINING DECISIONS ===\n")
    by_caller = {}
    for ev in events:
        caller = ev.get('caller', ev.get('file', 'unknown'))
        by_caller.setdefault(caller, []).append(ev)
    for caller, evlist in sorted(by_caller.items()):
        print(f"Caller: {caller}")
        print("-" * 60)
        for ev in evlist:
            fname = ev['file'][-40:] if len(ev['file']) > 40 else ev['file']
            print(f"  {fname}:{ev['line']:<6} -> {ev['callee']:<20}")
        print()
    print(f"\nTotal inlining events: {len(events)}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--compiler', '-c', required=True)
    parser.add_argument('--opt', '-O', default='-O2')
    parser.add_argument('--output-json', help='Save full report as JSON')
    parser.add_argument('--output-csv', help='Save inlining events as CSV')
    parser.add_argument('--keep-reports', action='store_true')
    parser.add_argument('build_command', nargs=argparse.REMAINDER)
    args = parser.parse_args()

    build_cmd = args.build_command
    if build_cmd and build_cmd[0] == '--':
        build_cmd = build_cmd[1:]
    if not build_cmd:
        print("Error: no build command provided.", file=sys.stderr)
        sys.exit(1)

    wrapper_path = Path(__file__).parent / 'inline_wrapper.py'
    if not wrapper_path.exists():
        print(f"ERROR: wrapper script not found at {wrapper_path}", file=sys.stderr)
        sys.exit(1)

    report_dir = tempfile.mkdtemp(prefix="inline_reports_")
    print(f"Reports will be stored in: {report_dir}", file=sys.stderr)

    wrapper_script = os.path.join(report_dir, 'gcc-wrapper.sh')
    with open(wrapper_script, 'w') as f:
        f.write(f"""#!/bin/sh
exec python3 "{wrapper_path}" "$@"
""")
    os.chmod(wrapper_script, 0o755)

    env = os.environ.copy()
    env['REAL_GCC'] = args.compiler
    env['INLINE_REPORT_DIR'] = report_dir
    env['GCC_OPT_FLAGS'] = args.opt

    COMPILER_NAMES = {'gcc', 'g++', 'cc', 'c++', 'clang', 'clang++'}
    cmd_prog = os.path.basename(build_cmd[0])

    if cmd_prog in COMPILER_NAMES:
        print(f"Direct compiler call detected, replacing '{build_cmd[0]}' with wrapper", file=sys.stderr)
        build_cmd[0] = wrapper_script
    elif cmd_prog == 'make':
        print(f"Make detected, overriding CC/CXX in command line", file=sys.stderr)
        build_cmd.insert(1, f'CC={wrapper_script}')
        build_cmd.insert(2, f'CXX={wrapper_script}')
    else:
        env['CC'] = wrapper_script
        env['CXX'] = wrapper_script

    print(f"Starting build: {' '.join(build_cmd)}", file=sys.stderr)
    print(f"Using compiler wrapper: {wrapper_script}", file=sys.stderr)

    proc = subprocess.run(build_cmd, env=env, shell=False)

    events = collect_reports(report_dir)

    if events:
        print_summary(events)
        if args.output_json:
            with open(args.output_json, 'w') as f:
                json.dump({
                    'compiler': args.compiler,
                    'opt_flags': args.opt,
                    'inlining_events': events,
                }, f, indent=2)
            print(f"\nJSON report saved to {args.output_json}", file=sys.stderr)
        if args.output_csv:
            export_to_csv(events, args.output_csv)
            print(f"CSV report saved to {args.output_csv}", file=sys.stderr)
    else:
        print("No inlining events were captured.")
        print("Possible reasons:")
        print("  - Build system does not respect CC/CXX variables")
        print("  - No source files were compiled (no .c/.cpp files in command)")
        print("  - No inlining happened (try -O2 or -O3)")
        print("  - Wrapper script failed (check env vars)")

    if not args.keep_reports and not args.output_json and not args.output_csv:
        shutil.rmtree(report_dir, ignore_errors=True)
        print("Temporary directory removed.", file=sys.stderr)
    else:
        print(f"Reports kept in: {report_dir}", file=sys.stderr)

    sys.exit(proc.returncode)

if __name__ == '__main__':
    main()
