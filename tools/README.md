# Tools
- `inline_extractor_wrapper.py` - Help script to wrap a compiler (inquier logs about the inlining opt).
- `inline_extractor.py` - Script for the inline information getting. To invoke, use the next command:
```bash
python inline_extractor.py --compiler gcc -O2 --output-json <path.json> --output-csv <path.csv> -- <build command, ex: make -B>
```
- `project_data_gen.py` - Use the produced from the `inline_extractor.py` information to generated inline cases. To invoke, use the next querry:
```bash
python project_data_gen.py \
    <inline_data.json> \
    <project_path> \
    <save_loc>
```