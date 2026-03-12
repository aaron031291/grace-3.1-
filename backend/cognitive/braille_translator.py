import ast
import os
import sys
from typing import List, Optional

# Add the parent of backend to sys.path so 'backend.xxx' resolves
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from backend.cognitive.braille_mapper import BrailleMapper, mapper as default_mapper

class BrailleTranslator(ast.NodeVisitor):
    def __init__(self, mapper: BrailleMapper = default_mapper):
        self.mapper = mapper
        self.output: List[str] = []
        
    def translate_file(self, filepath: str) -> str:
        with open(filepath, 'r', encoding='utf-8') as f:
            source = f.read()
        return self.translate_code(source)
        
    def translate_code(self, source: str) -> str:
        self.output = []
        tree = ast.parse(source)
        self.visit(tree)
        return "\n".join(self.output)

    def _emit(self, keyword_or_symbol: str, default: Optional[str] = None):
        """Looks up the brille symbol and appends it to output."""
        mapping = self.mapper.python_to_braille(keyword_or_symbol)
        if mapping:
            self.output.append(mapping["braille"])
        elif default:
            self.output.append(default)
        else:
            # Fallback to appending the raw string if not found, 
            # though in a pure braille encoded AST, we might want a raw token format.
            self.output.append(f"[{keyword_or_symbol}]")

    def visit_FunctionDef(self, node: ast.FunctionDef):
        # Composition Rule 2: def + name + ( + parameters + ) + : + body
        # ●●●●●● 1mm □ + identifier + ●●●●●● 1mm □△ + args + ●●●●●● 2mm □△ + block
        
        # 'def'
        self._emit("def")
        
        # Function name
        self.output.append(node.name)
        
        # Parameters (start with specific symbol according to spec if we want to be exact,
        # but the spec says "●●●●●● 1mm □△ + args + ●●●●●● 2mm □△ + block"
        self.output.append("●●●●●● 1mm □△") # open args
        
        for arg in node.args.args:
            self.output.append(arg.arg)
            
        self.output.append("●●●●●● 2mm □△") # begin block
        
        self.generic_visit(node)
        
    def visit_ClassDef(self, node: ast.ClassDef):
        # Composition Rule 3: class + name + ( + inherit + ) + : + body
        self._emit("class")
        self.output.append(node.name)
        if node.bases:
            self._emit("inherit", default="●●●●●● 3mm □△")
            for base in node.bases:
                if isinstance(base, ast.Name):
                    self.output.append(base.id)
        
        self.generic_visit(node)

    def visit_If(self, node: ast.If):
        self._emit("if")
        self.visit(node.test)
        for stmt in node.body:
            self.visit(stmt)
        for stmt in node.orelse:
            # Handle elif
            if isinstance(stmt, ast.If):
                self._emit("elif")
                self.visit(stmt.test)
                for substmt in stmt.body:
                    self.visit(substmt)
                for sub_orelse in stmt.orelse:
                    self.visit(sub_orelse)
            else:
                self._emit("else")
                self.visit(stmt)

    def visit_Return(self, node: ast.Return):
        self._emit("return")
        if node.value:
            self.visit(node.value)

    def visit_Assign(self, node: ast.Assign):
        # target + = + value
        for target in node.targets:
            self.visit(target)
        self._emit("assign")
        self.visit(node.value)

    def visit_Call(self, node: ast.Call):
        if isinstance(node.func, ast.Name):
            # Check if it's a built in function
            mapped = self.mapper.python_to_braille(node.func.id)
            if mapped:
                self._emit(node.func.id)
            else:
                self.output.append(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            self.visit(node.func)
            
        self.output.append("●●●●●● 1mm □△") # args open
        for arg in node.args:
            self.visit(arg)
        self.output.append("●●●●●● 2mm □△") # args close

    def visit_Name(self, node: ast.Name):
        mapped = self.mapper.python_to_braille(node.id)
        if mapped:
            self._emit(node.id)
        else:
            self.output.append(node.id)

    def visit_Constant(self, node: ast.Constant):
        if isinstance(node.value, bool):
            self._emit(str(node.value))
        elif node.value is None:
            self._emit("None")
        else:
            # For raw strings or numbers we might just emit their value
            self.output.append(repr(node.value))

    def visit_Import(self, node: ast.Import):
        self._emit("import")
        for alias in node.names:
            self.output.append(alias.name)
            if alias.asname:
                self._emit("as")
                self.output.append(alias.asname)
                
    def visit_ImportFrom(self, node: ast.ImportFrom):
        self._emit("from")
        if node.module:
            self.output.append(node.module)
        self._emit("import")
        for alias in node.names:
            self.output.append(alias.name)
            if alias.asname:
                self._emit("as")
                self.output.append(alias.asname)

    def visit_BinOp(self, node: ast.BinOp):
        self.visit(node.left)
        
        op_map = {
            ast.Add: "add",
            ast.Sub: "subtract",
            ast.Mult: "multiply",
            ast.Div: "divide",
            ast.FloorDiv: "floor_divide",
            ast.Mod: "modulo",
            ast.Pow: "power",
            ast.BitAnd: "bitwise_and",
            ast.BitOr: "bitwise_or",
            ast.BitXor: "bitwise_xor",
            ast.LShift: "left_shift",
            ast.RShift: "right_shift"
        }
        
        op_name = op_map.get(type(node.op))
        if op_name:
            self._emit(op_name)
            
        self.visit(node.right)
