from sympy.parsing.sympy_parser import parse_expr, standard_transformations
import sympy as sp
func_str = 'h0 + A * exp(-((x - x0)**2 + (y - y0)**2) / (2 * omega**2)) + alpha * x + beta * y'
transformations = standard_transformations
local_dict = {'exp': sp.exp}
# predefine symbols
for name in ['h0','A','x0','y0','omega','alpha','beta','x','y']:
    local_dict[name] = sp.symbols(name)
expr = parse_expr(func_str, local_dict=local_dict, transformations=transformations)
print('Parsed expr:', expr)
print('Free symbols:', expr.free_symbols)
print('Atoms of Function:', expr.atoms(sp.Function))
for a in expr.atoms():
    print(type(a), a)
