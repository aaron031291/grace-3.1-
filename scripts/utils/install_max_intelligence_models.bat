@echo off
REM Install Maximum Intelligence Models for GRACE (Windows)
REM Balances maximum intelligence with storage efficiency

echo ==========================================
echo Installing Maximum Intelligence Models
echo ==========================================
echo.

REM Phase 1: Core Intelligence (Maximum Intelligence)
echo Phase 1: Installing Core Intelligence Models...
echo.

echo 1. DeepSeek Coder V2 16B (Best Code Intelligence)
ollama pull deepseek-coder-v2:16b-instruct
echo.

echo 2. DeepSeek-R1 70B (Best Reasoning Intelligence)
ollama pull deepseek-r1:70b
echo.

echo 3. Qwen 2.5 72B (Best General Intelligence)
ollama pull qwen2.5:72b-instruct
echo.

echo [OK] Phase 1 Complete: ~90GB, Maximum Intelligence
echo.

REM Ask if user wants Phase 2
set /p phase2="Install Phase 2: Specialized Intelligence Models? (y/n) "
if /i "%phase2%"=="y" (
    echo.
    echo Phase 2: Installing Specialized Intelligence Models...
    echo.
    
    echo 4. Qwen 2.5 Coder 32B (Large Context Code)
    ollama pull qwen2.5-coder:32b-instruct
    echo.
    
    echo 5. Mixtral 8x7B (Efficient General Intelligence)
    ollama pull mixtral:8x7b
    echo.
    
    echo [OK] Phase 2 Complete: +46GB, Specialized Capabilities
    echo.
)

REM Ask if user wants Phase 3
set /p phase3="Install Phase 3: Fast Intelligence Models? (y/n) "
if /i "%phase3%"=="y" (
    echo.
    echo Phase 3: Installing Fast Intelligence Models...
    echo.
    
    echo 6. CodeQwen 1.5 7B (Fast Code)
    ollama pull codeqwen1.5:7b
    echo.
    
    echo 7. DeepSeek-R1 Distill 1.3B (Fast Reasoning)
    ollama pull deepseek-r1-distill:1.3b
    echo.
    
    echo [OK] Phase 3 Complete: +6GB, Fast Responses
    echo.
)

echo.
echo ==========================================
echo Installation Complete!
echo ==========================================
echo.
echo Verify models:
echo   ollama list
echo.
echo Test a model:
echo   ollama run deepseek-coder-v2:16b-instruct "Hello"
echo.
echo Check in GRACE:
echo   curl http://localhost:8000/llm/models
echo.
pause
