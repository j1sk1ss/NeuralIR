from pycparser import CParser
from parser.c.pyc_to_uast import c_code_to_uast
from parser.cpl.cpl_to_uast import cpl_code_to_uast

ccode = r"""
int foo(int x) {
  while (x) {
      x += 10;
  }
  return x;
}
"""

cplcode = r"""{
  function foo(i32 x) => i32 {
    while x; {
      x += 10;
    }
    return x;
  }
}
"""

uast = c_code_to_uast(ccode)
uast.print_uast()

uast = cpl_code_to_uast(cplcode)
uast.print_uast()
