import os
import sys
import hashlib
import subprocess

from pathlib import Path

def _fire_debug_message(msg) -> None:
    print(f"[wrapper] {msg}", file=sys.stderr)

def _has_source_file(args: list[str]) -> bool:
    for arg in args:
        if arg.startswith('-'):
            continue
        if any(arg.endswith(ext) for ext in ['.c', '.cpp', '.cc', '.cxx', '.C']):
            return True
        
    return False

def _find_source_files(args: list[str]) -> list:
    sources = []
    for arg in args:
        if arg.startswith('-'):
            continue
        if any(arg.endswith(ext) for ext in ['.c', '.cpp', '.cc', '.cxx', '.C']):
            sources.append(arg)
            
    return sources

def _find_output_file(args: list[str]) -> str | None:
    try:
        o_index = args.index('-o')
        if o_index + 1 < len(args):
            return args[o_index + 1]
    except ValueError:
        pass
    return None

def _generate_report_filename(src_paths: list[str], output_file: str) -> str:
    if src_paths:
        base = Path(src_paths[0]).stem
    else:
        base = 'unknown'
    hash_input = ''.join(src_paths) + (output_file or '')
    src_hash = hashlib.md5(hash_input.encode()).hexdigest()[:8]
    return f"{base}_{src_hash}.inline.txt"

def _main() -> None:
    """ Wrapper for a build command. It will take all input compile arguments,
    then compiler the related project with logging capture, and then save the
    obtained result (inline logs).
    """
    real_gcc = os.environ.get('REAL_GCC')
    report_dir = os.environ.get('INLINE_REPORT_DIR')
    opt_flags = os.environ.get('GCC_OPT_FLAGS', '-O2')

    if not real_gcc or not report_dir:
        _fire_debug_message("ERROR: missing REAL_GCC or INLINE_REPORT_DIR")
        sys.exit(1)

    args = sys.argv[1:]
    _fire_debug_message(f"args: {args}")

    if not _has_source_file(args):
        _fire_debug_message("No source files found, passing through")
        return subprocess.call([real_gcc] + args)

    src_files = _find_source_files(args)
    output_file = _find_output_file(args)
    _fire_debug_message(f"src_files: {src_files}, output_file: {output_file}")

    cmd = [real_gcc] + args

    has_opt = any(arg.startswith('-O') for arg in args)
    if not has_opt:
        if not opt_flags.startswith('-O'):
            opt_flags = f'-O{opt_flags}'
        cmd.append(opt_flags)
        _fire_debug_message(f"Added optimization: {opt_flags}")

    cmd.append('-fopt-info-inline')

    _fire_debug_message(f"Running: {' '.join(cmd)}")
    proc = subprocess.run(cmd, stderr=subprocess.PIPE, text=True)

    report_lines = []
    for line in proc.stderr.splitlines():
        if 'optimized:' in line and 'inlining' in line.lower():
            report_lines.append(line.strip())
            _fire_debug_message(f"Found inline: {line.strip()}")

    if report_lines:
        report_file = os.path.join(report_dir, _generate_report_filename(src_files, output_file))
        with open(report_file, 'w') as f:
            f.write('\n'.join(report_lines))
        _fire_debug_message(f"Report written to {report_file} with {len(report_lines)} entries")
    else:
        _fire_debug_message("No inlining messages found in stderr")

if __name__ == '__main__':
    sys.exit(_main())
