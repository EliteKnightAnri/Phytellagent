from sympy.parsing.sympy_parser import parse_expr, standard_transformations
import sympy as sp
func_str = 'A * exp(-((x - x0)**2 + (y - y0)**2) / (2 * omega**2))'
func_str = func_str.replace('np.', '').replace('numpy.', '').replace('math.', '')
transformations = standard_transformations
local_dict = {'exp': sp.exp}
expr = parse_expr(func_str, local_dict=local_dict, transformations=transformations)
print('Parsed expr:', expr)
print('Free symbols:', expr.free_symbols)
print('Atoms of Function:', expr.atoms(sp.Function))
for a in expr.atoms():
    print(type(a), a)
