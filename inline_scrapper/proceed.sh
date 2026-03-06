#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  ./proceed.sh <project_path> <build_command> <output_dir> <fake_libs> [compiler] [opt_level]

Arguments:
  project_path   Path to the target project
  build_command  Full build command in quotes
                 Example: "make -B" or "cmake --build build -j8"
  output_dir     Directory where all generated data will be stored
  fake_libs      Path to fake libraries required by the parser
  compiler       Compiler name for inline_extractor.py (default: gcc)
  opt_level      Optimization level (default: -O2)

Examples:
  ./proceed.sh /path/to/project "make -B" /tmp/out /path/to/fake_libs
  ./proceed.sh /path/to/project "cmake --build build -j8" /tmp/out /path/to/fake_libs gcc -O3
EOF
}

if [[ $# -lt 4 ]]; then
  usage
  exit 1
fi

PROJECT_PATH="$(realpath "$1")"
BUILD_COMMAND="$2"
OUTPUT_DIR="$(realpath -m "$3")"
FAKE_LIBS="$(realpath "$4")"
COMPILER="${5:-gcc}"
OPT_LEVEL="${6:--O2}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

INLINE_EXTRACTOR="${SCRIPT_DIR}/inline_extractor.py"
INLINE_FINAL="${SCRIPT_DIR}/inline_final.py"

if [[ ! -d "$PROJECT_PATH" ]]; then
  echo "Error: project directory not found: $PROJECT_PATH" >&2
  exit 1
fi

if [[ ! -d "$FAKE_LIBS" ]]; then
  echo "Error: fake libraries directory not found: $FAKE_LIBS" >&2
  exit 1
fi

if [[ ! -f "$INLINE_EXTRACTOR" ]]; then
  echo "Error: inline_extractor.py not found next to the script: $INLINE_EXTRACTOR" >&2
  exit 1
fi

if [[ ! -f "$INLINE_FINAL" ]]; then
  echo "Error: inline_final.py not found next to the script: $INLINE_FINAL" >&2
  exit 1
fi

mkdir -p "$OUTPUT_DIR"

INLINE_JSON="${OUTPUT_DIR}/inline_data.json"
INLINE_CSV="${OUTPUT_DIR}/inline_data.csv"
FINAL_DIR="${OUTPUT_DIR}/inline_cases"
LOG_FILE="${OUTPUT_DIR}/pipeline.log"

mkdir -p "$FINAL_DIR"

{
  echo "== Inline pipeline started =="
  echo "Project      : $PROJECT_PATH"
  echo "Build command: $BUILD_COMMAND"
  echo "Output dir   : $OUTPUT_DIR"
  echo "Fake libs    : $FAKE_LIBS"
  echo "Compiler     : $COMPILER"
  echo "Opt level    : $OPT_LEVEL"
  echo
} | tee "$LOG_FILE"

echo "== Step 1: running inline_extractor.py ==" | tee -a "$LOG_FILE"
(
  cd "$PROJECT_PATH"
  python3 "$INLINE_EXTRACTOR" \
    --compiler "$COMPILER" \
    "$OPT_LEVEL" \
    --output-json "$INLINE_JSON" \
    --output-csv "$INLINE_CSV" \
    -- bash -lc "$BUILD_COMMAND"
) 2>&1 | tee -a "$LOG_FILE"

if [[ ! -f "$INLINE_JSON" ]]; then
  echo "Error: inline JSON was not generated: $INLINE_JSON" >&2
  exit 1
fi

echo | tee -a "$LOG_FILE"
echo "== Step 2: running inline_final.py ==" | tee -a "$LOG_FILE"
python3 "$INLINE_FINAL" \
  "$INLINE_JSON" \
  "$PROJECT_PATH" \
  "$FINAL_DIR" \
  "$FAKE_LIBS" 2>&1 | tee -a "$LOG_FILE"

echo | tee -a "$LOG_FILE"
echo "== Done ==" | tee -a "$LOG_FILE"
echo "JSON      : $INLINE_JSON" | tee -a "$LOG_FILE"
echo "CSV       : $INLINE_CSV" | tee -a "$LOG_FILE"
echo "Final dir : $FINAL_DIR" | tee -a "$LOG_FILE"
echo "Log       : $LOG_FILE" | tee -a "$LOG_FILE"