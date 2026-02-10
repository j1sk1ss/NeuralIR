from parser.parser import Parser, ParserConfig, Language
from analysis.analyzer import ProgramAnalysis

if __name__ == "__main__":
  code = r"""
void foo() {}
void main() {
  while (1) {
    while (1) {
      foo();
    }
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
  
  main = analyzer.get_function("main")
  for call in main.calls():
      if call.called_function == 'foo':
        print(call)
