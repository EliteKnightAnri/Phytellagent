from sympy.parsing.sympy_parser import parse_expr, standard_transformations
import sympy as sp
func_str = 'A*exp(x)'
transformations = standard_transformations
local_dict = {'exp': sp.exp}
expr = parse_expr(func_str, local_dict=local_dict, transformations=transformations)
print(type(expr), expr)
print('free_symbols', expr.free_symbols)
print('atoms Function', expr.atoms(sp.Function))
