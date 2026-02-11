from parser.parser import Parser, ParserConfig, Language
from analysis.analyzer import ProgramAnalysis

if __name__ == "__main__":
  code = r"""
int foo(int a) {
    for (int i = 0; i < 10; i++) {
        a += 1;
    }
    return a;
}
void main(int* a) {
  while (1) {
    while (1) {
      int** b = &a;
      *b = foo(1);
    }
    *a = foo(2);
  }
}
  """

  analyzer: ProgramAnalysis = ProgramAnalysis(
    parser=Parser(
      conf=ParserConfig(
        code=code, lang=Language.C
      )
    )
  )
  
  analyzer.print_ir()                   # Print the IR presentation of a code
  analyzer.all_calls()                  # Get all function calls in list (from up to down)
  analyzer.get_function("main")         # Get information about a function (FunctionAnalysis)
  analyzer.functions                    # Get a dict with [str:FunctionAnalysis] (str - function name)
  analyzer.get_function("main").calls() # Get function calls from the function (InstructionAnalysis)
  