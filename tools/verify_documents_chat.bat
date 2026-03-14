@echo off
setlocal
set API=http://localhost:8000

echo Documents Tab Chat History Verification
echo ----------------------------------------

REM Check backend is running
powershell -NoProfile -Command "$r=Invoke-WebRequest -Uri '%API%/docs' -UseBasicParsing -Method GET -TimeoutSec 5; if ($r.StatusCode -ge 200 -and $r.StatusCode -lt 500) { exit 0 } else { exit 1 }"
if errorlevel 1 (
  echo Backend API not responding on %API%
  exit /b 1
)

echo.
echo Testing chat creation endpoint...
for /f "usebackq tokens=*" %%i in (`powershell -NoProfile -Command "$body=@{title='Test Chat - /test';description='Test chat for /test folder';folder_path='/test'} | ConvertTo-Json; (Invoke-WebRequest -Uri '%API%/chats' -Method POST -ContentType 'application/json' -Body $body -UseBasicParsing).Content"`) do set CREATE_RESP=%%i

echo %CREATE_RESP% | findstr /c:"\"id\"" >nul
if errorlevel 1 (
  echo Failed to create chat
  echo %CREATE_RESP%
  exit /b 1
)

for /f "tokens=2 delims=:,} " %%a in ('echo %CREATE_RESP% ^| findstr "\"id\":"') do set CHAT_ID=%%a
echo Created Chat ID: %CHAT_ID%

echo.
echo Testing message saving...
for /f "usebackq tokens=*" %%i in (`powershell -NoProfile -Command "$body=@{role='user';content='Test message'} | ConvertTo-Json; (Invoke-WebRequest -Uri '%API%/chats/%CHAT_ID%/messages' -Method POST -ContentType 'application/json' -Body $body -UseBasicParsing).Content"`) do set MSG_RESP=%%i
echo %MSG_RESP% | findstr /c:"\"role\"" >nul
if errorlevel 1 (
  echo Failed to save message
  echo %MSG_RESP%
  exit /b 1
)

echo.
echo Testing message retrieval...
for /f "usebackq tokens=*" %%i in (`powershell -NoProfile -Command "(Invoke-WebRequest -Uri '%API%/chats/%CHAT_ID%/messages' -Method GET -UseBasicParsing).Content"`) do set HISTORY=%%i
echo %HISTORY% | findstr /c:"\"content\"" >nul
if errorlevel 1 (
  echo Failed to retrieve messages
  exit /b 1
)

echo All tests passed!
exit /b 0
endlocal
