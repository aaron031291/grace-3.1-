@echo off
setlocal enabledelayedexpansion
echo ==========================================
echo  FILE MANAGEMENT SYSTEM - VERIFICATION
echo ==========================================

set ERROR_COUNT=0

REM Check Backend Files relative to backend directory
set BACKEND_DIR=%~dp0..\backend

echo.
echo Checking Backend Files...

set files=file_manager\__init__.py file_manager\file_handler.py file_manager\knowledge_base_manager.py api\file_management.py app.py requirements.txt
for %%F in (%files%) do (
  if exist "%BACKEND_DIR%\%%F" (
    echo   [OK] %%F
  ) else (
    echo   [MISS] %%F
    set /a ERROR_COUNT+=1
  )
)

echo.
echo Checking Python Imports...
pushd "%BACKEND_DIR%"
python - <<PY
import sys
ok=True
try:
    from file_manager import FileHandler, extract_file_text, KnowledgeBaseManager
    print('[OK] file_manager')
except Exception as e:
    print('[ERR] file_manager', e); ok=False
try:
    from api.file_management import router
    print('[OK] api.file_management')
except Exception as e:
    print('[ERR] api.file_management', e); ok=False
try:
    from app import app
    print('[OK] app')
except Exception as e:
    print('[ERR] app', e); ok=False
sys.exit(0 if ok else 1)
PY
if errorlevel 1 set /a ERROR_COUNT+=1
popd

echo.
echo Checking Required Dependencies...
python - <<PY
import importlib, sys
packages = [
  'pdfplumber','fastapi','pydantic','sqlalchemy','qdrant_client','sentence_transformers'
]
ok=True
for p in packages:
    try:
        importlib.import_module(p)
        print('[OK]', p)
    except Exception:
        print('[MISS]', p)
        ok=False
sys.exit(0 if ok else 1)
PY
if errorlevel 1 set /a ERROR_COUNT+=1

echo.
echo Checking Frontend Files...
set FRONTEND_DIR=%~dp0..\frontend
set feFiles=src\components\FileBrowser.jsx src\components\FileBrowser.css src\components\RAGTab.jsx
for %%F in (%feFiles%) do (
  if exist "%FRONTEND_DIR%\%%F" (
    for %%A in ("%FRONTEND_DIR%\%%F") do set size=%%~zA
    echo   [OK] %%F (!size! bytes)
  ) else (
    echo   [MISS] %%F
    set /a ERROR_COUNT+=1
  )
)

echo.
echo Checking API Endpoints Registration...
pushd "%BACKEND_DIR%"
python - <<PY
from app import app
required = [
  '/files/browse','/files/create-folder','/files/upload','/files/delete','/files/delete-folder'
]
paths = [r.path for r in app.routes]
missing = [e for e in required if not any(e in p for p in paths)]
if missing:
    print('Missing endpoints:', missing)
    raise SystemExit(1)
print('All endpoints present')
PY
if errorlevel 1 set /a ERROR_COUNT+=1
popd

echo.
echo ==========================================
if %ERROR_COUNT% EQU 0 (
  echo   ALL VERIFICATION TESTS PASSED
  exit /b 0
) else (
  echo   SOME TESTS FAILED - PLEASE FIX ERRORS
  exit /b 1
)
endlocal
