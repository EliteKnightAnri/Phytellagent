from sympy.parsing.sympy_parser import parse_expr, standard_transformations
import sympy as sp
func_str = 'h0 + A * exp(-((x - x0)**2 + (y - y0)**2) / (2 * omega**2)) + alpha * x + beta * y'
transformations = standard_transformations
func_name_map = {'exp': sp.exp, 'log': sp.log, 'ln': sp.log, 'sin': sp.sin, 'cos': sp.cos,
    'tan': sp.tan, 'sqrt': sp.sqrt, 'pi': sp.pi, 'E': sp.E, 'abs': sp.Abs,
    'asin': sp.asin, 'acos': sp.acos, 'atan': sp.atan, 'sinh': sp.sinh,
    'cosh': sp.cosh, 'tanh': sp.tanh, 'floor': sp.floor, 'ceiling': sp.ceiling}
import re
idents = re.findall(r"\b[a-zA-Z_]\w*\b", func_str)
local_dict = dict(func_name_map)
for ident in set(idents):
    if ident in local_dict or ident in ['x','y']:
        continue
    local_dict[ident] = sp.symbols(ident)
expr = parse_expr(func_str, local_dict=local_dict, transformations=transformations)
print('Parsed expr:', expr)
print('Free symbols:', expr.free_symbols)
print('Atoms of Function:', expr.atoms(sp.Function))
for a in expr.atoms():
    print(type(a), a)
