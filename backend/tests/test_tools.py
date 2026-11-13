"""Unit tests for Calculator, DateTimeTool, and ToolRegistry."""
import pytest
from app.tools.calculator import CalculatorTool, evaluate_expression
from app.tools.datetime_tool import DateTimeTool
from app.tools.registry import tool_registry


def test_calculator_basic_arithmetic():
    """Verify standard arithmetic evaluation."""
    assert evaluate_expression("2 + 2") == 4
    assert evaluate_expression("10 - 4 * 2") == 2
    assert evaluate_expression("(10 + 5) / 3") == 5.0
    assert evaluate_expression("2 ** 8") == 256
    assert evaluate_expression("17 % 5") == 2


def test_calculator_math_functions():
    """Verify safe whitelisted math functions."""
    assert evaluate_expression("sqrt(144)") == 12.0
    assert evaluate_expression("abs(-55)") == 55
    assert evaluate_expression("min(10, 20, 5)") == 5
    assert evaluate_expression("max(10, 20, 5)") == 20
    assert evaluate_expression("round(3.14159, 2)") == 3.14


def test_calculator_division_by_zero():
    """Verify division by zero is safely caught."""
    with pytest.raises(ZeroDivisionError):
        evaluate_expression("100 / 0")


def test_calculator_security_sandbox():
    """Verify arbitrary code execution and malicious payloads are strictly rejected."""
    # Attempt import
    with pytest.raises(ValueError):
        evaluate_expression("__import__('os').system('dir')")

    # Attempt built-in access
    with pytest.raises(ValueError):
        evaluate_expression("open('secrets.txt')")

    # Attempt attribute access
    with pytest.raises(ValueError):
        evaluate_expression("().__class__.__bases__[0]")

    # Attempt lambda / statement
    with pytest.raises(ValueError):
        evaluate_expression("lambda x: x + 1")


@pytest.mark.asyncio
async def test_datetime_tool():
    """Verify timezone-aware datetime tool outputs."""
    tool = DateTimeTool()

    # UTC execution
    utc_result = await tool.execute(timezone_name="UTC")
    assert utc_result["timezone"] == "UTC"
    assert "iso_timestamp" in utc_result
    assert "formatted" in utc_result
    assert "date" in utc_result

    # Custom timezone execution
    tokyo_result = await tool.execute(timezone_name="Asia/Tokyo")
    assert tokyo_result["timezone"] == "Asia/Tokyo"
    assert "+0900" in tokyo_result["utc_offset"]


@pytest.mark.asyncio
async def test_tool_registry_execution():
    """Verify safe tool execution through ToolRegistry."""
    # Valid calculator call
    res = await tool_registry.execute_tool("calculator", {"expression": "15 * 6"})
    assert res["success"] is True
    assert res["result"]["result"] == 90

    # Invalid arguments rejection (Pydantic schema validation failure)
    bad_res = await tool_registry.execute_tool("calculator", {"wrong_arg": "test"})
    assert bad_res["success"] is False
    assert "Invalid arguments" in bad_res["error"]

    # Non-existent tool lookup
    missing_res = await tool_registry.execute_tool("non_existent_tool", {})
    assert missing_res["success"] is False
    assert "not registered" in missing_res["error"]


def test_tool_schemas_for_llm():
    """Verify tool schemas export valid OpenAI/Groq function calling definitions."""
    schemas = tool_registry.get_schemas_for_llm()
    assert len(schemas) >= 2

    tool_names = [s["function"]["name"] for s in schemas]
    assert "calculator" in tool_names
    assert "get_current_datetime" in tool_names

    calc_schema = next(s for s in schemas if s["function"]["name"] == "calculator")
    assert "expression" in calc_schema["function"]["parameters"]["properties"]
