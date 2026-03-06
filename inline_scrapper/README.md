# Inline Scrapper
This is a set of tools for the CPL perceptron scrapper project.

## Tools
- `inline_extractor_wrapper.py` - Help script to wrap a compiler (inquier logs about the inlining opt).
- `inline_extractor.py` - Script for the inline information getting. To invoke, use the next command:
```bash
python inline_extractor.py --compiler gcc -O2 --output-json <path.json> --output-csv <path.csv> -- <build command, ex: make -B>
```
- `inline_final.py` - Use the produced from the `inline_extractor.py` information to generated inline cases. To invoke, use the next querry:
```bash
python inline_final.py \ 
    <inline_data.json> \ 
    <project_path> \ 
    <save_loc> \  
    <fake_libs> 
```
- `funcextractor.py` - Helper module. Don't use it as a separate script!
- `proceed.sh` - Full pipline run.

## How to scrap the data?
To scrap all essential information, you will need:
1. Copy the entire project (yes, the NeuralIR project) to the considering project. Just drop it as a directory on the top level, which means, only to the first (root) project directory.
2. Then you will need the 'fake libraries' for the proper parser work (it will say which libs and where you can download them). Put libs somewhere where you want and provide the path. </br>
*P.S.: The link is https://github.com/eliben/pycparser/tree/main/utils/fake_libc_include. Pull the repository and provide the path to the directory from the link*
3. Prepare the considering project. It **must** be compiled with one command (For instance, to compile the Linux kernel, you initially need to use the `make config` command before the main `make` command. The second 'main' `make` command must be provided to the script). </br>
*P.S.: The command should invoke some sort of script which uses the 'CC' variable!*
4. Invoke the `proceed.sh` script with the next querry:
```bash
./proceed.sh \      #
<project_path> \    # You already have this path
"<build_commd>" \   # "make", "make -j 6" or similar command 
<output_path> \     # Where you want save output information 
<fake_libs_path> \  # You already have this path
<compiler>          # Actually, this is an optional argument, but make sure that you're using the gcc compiler
``` 
5. The expected information will be stored in the output directory.

# P.S.
These tools for C/C++ languages only (And for gcc only). Other languages and compilers will require independent set of tools.
