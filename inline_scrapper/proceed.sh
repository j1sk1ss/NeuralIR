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
CALL_EXTRACTOR="${SCRIPT_DIR}/call_extractor.py"
EXTRACTOR_FINAL="${SCRIPT_DIR}/extractor_final.py"
UNITER_FINAL="${SCRIPT_DIR}/uniter.py"

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

if [[ ! -f "$CALL_EXTRACTOR" ]]; then
  echo "Error: call_extractor.py not found next to the script: $CALL_EXTRACTOR" >&2
  exit 1
fi

if [[ ! -f "$EXTRACTOR_FINAL" ]]; then
  echo "Error: extractor_final.py not found next to the script: $EXTRACTOR_FINAL" >&2
  exit 1
fi

mkdir -p "$OUTPUT_DIR"

INLINE_JSON="${OUTPUT_DIR}/inline_data.json"
INLINE_CSV="${OUTPUT_DIR}/inline_data.csv"

OTHER_EVENTS_JSON="${OUTPUT_DIR}/other_events.json"

DUMPED_INLINES_JSON="${OUTPUT_DIR}/dumped_inlines.json"
DUMPED_OTHER_JSON="${OUTPUT_DIR}/dumped_other.json"
FINAL_RESULT="${OUTPUT_DIR}/result.csv"

LOG_FILE="${OUTPUT_DIR}/pipeline.log"

{
  echo "== Pipeline started =="
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
echo "== Step 2: running call_extractor.py ==" | tee -a "$LOG_FILE"
python3 "$CALL_EXTRACTOR" \
  --project-root "$PROJECT_PATH" \
  --fake-libc "$FAKE_LIBS" \
  --inline-json "$INLINE_JSON" \
  --output-json "$OTHER_EVENTS_JSON" \
  2>&1 | tee -a "$LOG_FILE"

if [[ ! -f "$OTHER_EVENTS_JSON" ]]; then
  echo "Error: non-inline events JSON was not generated: $OTHER_EVENTS_JSON" >&2
  exit 1
fi

echo | tee -a "$LOG_FILE"
echo "== Step 3: running extractor_final.py for inline events ==" | tee -a "$LOG_FILE"
python3 "$EXTRACTOR_FINAL" \
  "$INLINE_JSON" \
  "$PROJECT_PATH" \
  "$DUMPED_INLINES_JSON" \
  "$FAKE_LIBS" \
  2>&1 | tee -a "$LOG_FILE"

if [[ ! -f "$DUMPED_INLINES_JSON" ]]; then
  echo "Error: dumped inline JSON was not generated: $DUMPED_INLINES_JSON" >&2
  exit 1
fi

echo | tee -a "$LOG_FILE"
echo "== Step 4: running extractor_final.py for non-inline events ==" | tee -a "$LOG_FILE"
python3 "$EXTRACTOR_FINAL" \
  "$OTHER_EVENTS_JSON" \
  "$PROJECT_PATH" \
  "$DUMPED_OTHER_JSON" \
  "$FAKE_LIBS" \
  2>&1 | tee -a "$LOG_FILE"

if [[ ! -f "$DUMPED_OTHER_JSON" ]]; then
  echo "Error: dumped other JSON was not generated: $DUMPED_OTHER_JSON" >&2
  exit 1
fi

echo | tee -a "$LOG_FILE"
echo "== Step 5: Result merging ==" | tee -a "$LOG_FILE"
python3 "$UNITER_FINAL" \
  --other "$DUMPED_OTHER_JSON" \
  --inlines "$DUMPED_INLINES_JSON" \
  -o "$FINAL_RESULT" \
  2>&1 | tee -a "$LOG_FILE"

if [[ ! -f "$FINAL_RESULT" ]]; then
  echo "Error: final CSV was not generated: $FINAL_RESULT" >&2
  exit 1
fi

echo | tee -a "$LOG_FILE"
echo "== Done ==" | tee -a "$LOG_FILE"
echo "Inline events   : $INLINE_JSON" | tee -a "$LOG_FILE"
echo "Inline csv      : $INLINE_CSV" | tee -a "$LOG_FILE"
echo "Other events    : $OTHER_EVENTS_JSON" | tee -a "$LOG_FILE"
echo "Dumped inlines  : $DUMPED_INLINES_JSON" | tee -a "$LOG_FILE"
echo "Dumped other    : $DUMPED_OTHER_JSON" | tee -a "$LOG_FILE"
echo "Log             : $LOG_FILE" | tee -a "$LOG_FILE"
