"""
Backward compatibility wrapper.
Real code moved to cognitive/grace_tool_executor.py

Classes:
- `ToolCategory`
- `ToolDefinition`
- `ToolCall`
- `ToolResult`
- `KimiToolExecutor`

Key Methods:
- `list_tools()`
- `list_categories()`
- `get_tool_schema()`
- `get_stats()`
- `get_kimi_tool_executor()`
"""
from cognitive.grace_tool_executor import *
from cognitive.grace_tool_executor import GraceToolExecutor as KimiToolExecutor
from cognitive.grace_tool_executor import get_kimi_tool_executor, TOOL_REGISTRY, ToolCategory
