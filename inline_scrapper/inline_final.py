import sys
import json

from pathlib import Path
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.append(str(PROJECT_ROOT))

from analysis.analyzer import ProgramAnalysis
from parser.parser import Parser, ParserConfig, Language
from inline_scrapper.funcextractor import extract_inlined_pair, set_fake_libc_path

def _load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def _main() -> None:
    """ The script uses the inline dump from compilation. This dump has an essential data
    where and which function was inlined.
    Additionally, this script uses the analyzer with NeiralIR for general information
    generation.
    
    Note here: This scrapper is based on the pycparser, which means it won't work on other
               supported languages. To fix this, you will need to implement another project
               scrapper.
    """
    
    if len(sys.argv) != 5:
        print(f"Usage: python {sys.argv[0]} <json> <project_root> <output_dir> <fakelibs>")
        sys.exit(1)

    json_path: Path = Path(sys.argv[1])
    project_root: Path = Path(sys.argv[2]).resolve()
    output_dir: Path = Path(sys.argv[3])

    fakelibs: str | None = None
    if len(sys.argv) > 4:
        fakelibs = sys.argv[4]
    
    output_dir.mkdir(parents=True, exist_ok=True)

    if not json_path.is_file():
        print(f"Error: JSON file not found: {json_path}")
        sys.exit(1)
    if not project_root.is_dir():
        print(f"Error: Project root not found: {project_root}")
        sys.exit(1)

    data: dict = _load_json(json_path)
    events: list[dict] = data.get("inlining_events", [])
    if not events:
        print("No inlining events found.")
        return

    found_count: int = 0
    total: int = len(events)

    offsets: dict[str:int] = {}
    dumped_events: list[dict] = []
    for event in events:
        set_fake_libc_path(path=fakelibs)
        code: str = extract_inlined_pair(event=event, project_root=project_root)
        if not code:
            continue

        try:
            analyzer: ProgramAnalysis = ProgramAnalysis(
                parser=Parser(
                    conf=ParserConfig(
                        code=code, lang=Language.C
                    )
                )
            )
        except Exception as ex:
            print(f"Parser error on code:\n{code}")
            raise Exception("Parser error!") from ex

        funccall_index: int = 0
        offset: int = offsets.get(event.get("caller") + event.get("callee"), 0)
        caller_function = analyzer.get_function(event.get("caller"))
        for fcall in caller_function.calls():
            if fcall.called_function == event.get("callee"):
                if funccall_index != offset:
                    funccall_index += 1
                    continue

                dumped_events.append({
                    "callee": analyzer.get_function(event.get("callee")).dump_to_json(),
                    "caller": fcall.dump_to_json()
                })

                break

        offsets[event.get("caller") + event.get("callee")] = offset + 1

        found_count += 1
        if found_count % 10 == 0:
            print(f"Processed {found_count}/{total} pairs...")

    with open(f"{output_dir}/dumped.json", "w") as f:
        json.dump(dumped_events, f)

    print(f"Done. Extracted {found_count} inlining pairs.")

if __name__ == "__main__":
    _main()
    