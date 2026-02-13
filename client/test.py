import sympy as sp
from sympy.printing.pycode import pycode
from sympy.parsing.sympy_parser import parse_expr

def str_to_function_2d(func_str: str = "x ** 2", var_name: str = "x"):
    """
    Convert a string representation of a mathematical function into a callable function.

    Args:
        func_str (str): The mathematical expression as a string (e.g., "sin(x) + cos(x)").
        var_name (str, optional): The variable name to use as the function argument. Defaults to "x".
        str: The source code of a Python function that computes the given expression.

    Returns:
        callable: A function that takes a numpy array as input and returns the computed values.
    """
    expr = parse_expr(func_str)
    var = sp.symbols(var_name)
    return sp.lambdify(var, expr, modules=["numpy"])

func_str = input("Enter a mathematical function of x (e.g., 'sin(x) + cos(x)'): ")
new_function = str_to_function_2d(func_str)
y = new_function(2.0)
print(f"Function output for x=2.0: {y}")