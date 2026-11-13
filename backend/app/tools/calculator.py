"""Safe AST-based mathematical calculator tool.

Evaluates mathematical expressions safely using Python's AST module without arbitrary code execution.
"""
import ast
import math
import operator
from typing import Any, Dict
from pydantic import BaseModel, Field
from app.tools.base import BaseTool

# Supported binary operators
_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

# Supported unary operators
_UNARY_OPS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}

# Whitelisted mathematical functions
_SAFE_FUNCTIONS = {
    "abs": abs,
    "round": round,
    "sqrt": math.sqrt,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "ceil": math.ceil,
    "floor": math.floor,
    "min": min,
    "max": max,
}

# Whitelisted constants
_SAFE_CONSTANTS = {
    "pi": math.pi,
    "e": math.e,
}


def _safe_eval_node(node: ast.AST) -> Any:
    """Recursively evaluates an AST node strictly restricted to arithmetic."""
    if isinstance(node, ast.Expression):
        return _safe_eval_node(node.body)

    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError(f"Unsupported constant type: {type(node.value).__name__}")

    if isinstance(node, ast.Name):
        if node.id in _SAFE_CONSTANTS:
            return _SAFE_CONSTANTS[node.id]
        raise ValueError(f"Undefined variable or constant: '{node.id}'")

    if isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type in _UNARY_OPS:
            operand = _safe_eval_node(node.operand)
            return _UNARY_OPS[op_type](operand)
        raise ValueError(f"Unsupported unary operator: {op_type.__name__}")

    if isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type in _BIN_OPS:
            left = _safe_eval_node(node.left)
            right = _safe_eval_node(node.right)
            if op_type in (ast.Div, ast.FloorDiv, ast.Mod) and right == 0:
                raise ZeroDivisionError("Division by zero is undefined")
            if op_type == ast.Pow and (left > 10000 or right > 1000):
                raise ValueError("Exponentiation base or power too large")
            return _BIN_OPS[op_type](left, right)
        raise ValueError(f"Unsupported binary operator: {op_type.__name__}")

    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name):
            raise ValueError("Dynamic or nested function calls are forbidden")
        func_name = node.func.id
        if func_name not in _SAFE_FUNCTIONS:
            raise ValueError(f"Forbidden function '{func_name}'. Only arithmetic functions are allowed.")
        args = [_safe_eval_node(arg) for arg in node.args]
        return _SAFE_FUNCTIONS[func_name](*args)

    raise ValueError(f"Forbidden expression node: {type(node).__name__}")


def evaluate_expression(expr: str) -> float:
    """Parse and evaluate an arithmetic expression safely."""
    clean_expr = expr.strip()
    if not clean_expr:
        raise ValueError("Expression cannot be empty")
    if len(clean_expr) > 200:
        raise ValueError("Expression exceeds maximum allowed length of 200 characters")

    try:
        parsed = ast.parse(clean_expr, mode="eval")
    except SyntaxError as e:
        raise ValueError(f"Syntax error in mathematical expression: {e.msg}") from e

    return _safe_eval_node(parsed)


class CalculatorInput(BaseModel):
    expression: str = Field(
        ...,
        description="The mathematical expression to evaluate (e.g. '24 * 1.05 + sqrt(144)')"
    )


class CalculatorTool(BaseTool):
    name = "calculator"
    description = (
        "Perform exact mathematical calculations and arithmetic operations. "
        "Supports addition (+), subtraction (-), multiplication (*), division (/), powers (**), and functions like sqrt, abs, round, min, max."
    )
    args_schema = CalculatorInput
    timeout_seconds = 3.0

    async def execute(self, expression: str) -> Dict[str, Any]:
        """Safely compute the mathematical expression."""
        result = evaluate_expression(expression)
        return {
            "expression": expression,
            "result": result
        }
