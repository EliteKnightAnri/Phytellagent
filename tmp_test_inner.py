from sympy.parsing.sympy_parser import parse_expr, standard_transformations
import sympy as sp
inner = '-((x - x0)**2 + (y - y0)**2) / (2 * omega**2)'
transformations = standard_transformations
local_dict = {'exp': sp.exp}
expr = parse_expr(inner, local_dict=local_dict, transformations=transformations)
print('inner parsed:', expr)
print('free_symbols:', expr.free_symbols)
for a in expr.atoms():
    print(type(a), a)
