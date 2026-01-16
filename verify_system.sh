#!/bin/bash

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║         FILE MANAGEMENT SYSTEM - VERIFICATION TESTS            ║"
echo "╚════════════════════════════════════════════════════════════════╝"

ERROR_COUNT=0

echo ""
echo "▶ Checking Backend Files..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

cd /home/umer/Public/projects/grace_3/backend

# Check Python files exist
files=(
  "file_manager/__init__.py"
  "file_manager/file_handler.py"
  "file_manager/knowledge_base_manager.py"
  "api/file_management.py"
  "app.py"
  "requirements.txt"
)

for file in "${files[@]}"; do
  if [ -f "$file" ]; then
    echo "✓ $file"
  else
    echo "✗ $file - MISSING"
    ((ERROR_COUNT++))
  fi
done

echo ""
echo "▶ Checking Python Imports..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

python << 'PYTHON_EOF'
import sys
import os

modules = [
  ("file_manager", "FileHandler, extract_file_text, KnowledgeBaseManager"),
  ("api.file_management", "router"),
  ("app", "app"),
]

for module_name, items in modules:
  try:
    if module_name == "file_manager":
      from file_manager import FileHandler, extract_file_text, KnowledgeBaseManager
      print(f"✓ {module_name}")
    elif module_name == "api.file_management":
      from api.file_management import router
      print(f"✓ {module_name}")
    elif module_name == "app":
      from app import app
      print(f"✓ {module_name}")
  except ImportError as e:
    print(f"✗ {module_name} - {e}")
    sys.exit(1)

print("\n✓ All Python modules import successfully!")
PYTHON_EOF

echo ""
echo "▶ Checking Required Dependencies..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

python << 'PYTHON_EOF'
import sys

packages = [
  "pdfplumber",
  "fastapi",
  "pydantic",
  "sqlalchemy",
  "qdrant_client",
  "sentence_transformers",
]

for package in packages:
  try:
    __import__(package)
    print(f"✓ {package}")
  except ImportError:
    print(f"✗ {package} - NOT INSTALLED")
    sys.exit(1)

print("\n✓ All required packages are installed!")
PYTHON_EOF

echo ""
echo "▶ Checking Frontend Files..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

cd /home/umer/Public/projects/grace_3/frontend

files=(
  "src/components/FileBrowser.jsx"
  "src/components/FileBrowser.css"
  "src/components/RAGTab.jsx"
)

for file in "${files[@]}"; do
  if [ -f "$file" ]; then
    size=$(wc -c < "$file")
    echo "✓ $file ($size bytes)"
  else
    echo "✗ $file - MISSING"
    ((ERROR_COUNT++))
  fi
done

echo ""
echo "▶ Checking API Endpoints Registration..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

cd /home/umer/Public/projects/grace_3/backend

python << 'PYTHON_EOF'
from app import app

endpoints = [
  '/files/browse',
  '/files/create-folder', 
  '/files/upload',
  '/files/delete',
  '/files/delete-folder',
]

all_paths = [route.path for route in app.routes]

for endpoint in endpoints:
  found = any(endpoint in path for path in all_paths)
  if found:
    print(f"✓ {endpoint}")
  else:
    print(f"✗ {endpoint} - NOT REGISTERED")
    import sys
    sys.exit(1)

print(f"\n✓ All API endpoints registered!")
PYTHON_EOF

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
if [ $ERROR_COUNT -eq 0 ]; then
  echo "║            ✓ ALL VERIFICATION TESTS PASSED                       ║"
  echo "╚════════════════════════════════════════════════════════════════╝"
  exit 0
else
  echo "║         ✗ SOME TESTS FAILED - PLEASE FIX ERRORS                  ║"
  echo "╚════════════════════════════════════════════════════════════════╝"
  exit 1
fi
