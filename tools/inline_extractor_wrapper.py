#!/usr/bin/env python3
import os
import sys
import subprocess
import hashlib
from pathlib import Path

def debug(msg):
    print(f"[wrapper] {msg}", file=sys.stderr)

def has_source_file(args):
    for arg in args:
        if arg.startswith('-'):
            continue
        if any(arg.endswith(ext) for ext in ['.c', '.cpp', '.cc', '.cxx', '.C']):
            return True
    return False

def find_source_files(args):
    sources = []
    for arg in args:
        if arg.startswith('-'):
            continue
        if any(arg.endswith(ext) for ext in ['.c', '.cpp', '.cc', '.cxx', '.C']):
            sources.append(arg)
    return sources

def find_output_file(args):
    try:
        o_index = args.index('-o')
        if o_index + 1 < len(args):
            return args[o_index + 1]
    except ValueError:
        pass
    return None

def generate_report_filename(src_paths, output_file):
    if src_paths:
        base = Path(src_paths[0]).stem
    else:
        base = 'unknown'
    hash_input = ''.join(src_paths) + (output_file or '')
    src_hash = hashlib.md5(hash_input.encode()).hexdigest()[:8]
    return f"{base}_{src_hash}.inline.txt"

def main():
    real_gcc = os.environ.get('REAL_GCC')
    report_dir = os.environ.get('INLINE_REPORT_DIR')
    opt_flags = os.environ.get('GCC_OPT_FLAGS', '-O2')

    if not real_gcc or not report_dir:
        debug("ERROR: missing REAL_GCC or INLINE_REPORT_DIR")
        sys.exit(1)

    args = sys.argv[1:]
    debug(f"args: {args}")

    if not has_source_file(args):
        debug("No source files found, passing through")
        return subprocess.call([real_gcc] + args)

    src_files = find_source_files(args)
    output_file = find_output_file(args)
    debug(f"src_files: {src_files}, output_file: {output_file}")

    cmd = [real_gcc] + args

    has_opt = any(arg.startswith('-O') for arg in args)
    if not has_opt:
        if not opt_flags.startswith('-O'):
            opt_flags = f'-O{opt_flags}'
        cmd.append(opt_flags)
        debug(f"Added optimization: {opt_flags}")

    cmd.append('-fopt-info-inline')

    debug(f"Running: {' '.join(cmd)}")
    proc = subprocess.run(cmd, stderr=subprocess.PIPE, text=True)

    report_lines = []
    for line in proc.stderr.splitlines():
        if 'optimized:' in line and 'inlining' in line.lower():
            report_lines.append(line.strip())
            debug(f"Found inline: {line.strip()}")

    if report_lines:
        report_file = os.path.join(report_dir, generate_report_filename(src_files, output_file))
        with open(report_file, 'w') as f:
            f.write('\n'.join(report_lines))
        debug(f"Report written to {report_file} with {len(report_lines)} entries")
    else:
        debug("No inlining messages found in stderr")

    return proc.returncode

if __name__ == '__main__':
    sys.exit(main())
