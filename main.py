from pycparser import CParser
from parser.c.pyc_to_uast import c_code_to_uast
from parser.cpl.cpl_to_uast import cpl_code_to_uast

ccode = r"""
int main() {
  int* a;
  int b = *a;
}
"""

cplcode = r"""{
  function main() {
    ptr i32 a;
    i32 b = dref a;
  }
}
"""

uast = c_code_to_uast(ccode)
uast.print_uast()

uast = cpl_code_to_uast(cplcode)
uast.print_uast()
