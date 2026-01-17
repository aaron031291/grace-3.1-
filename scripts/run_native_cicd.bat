@echo off
REM GRACE Native CI/CD Runner
REM Runs tests natively within GRACE (no external services)

python -m backend.ci_cd.native_test_runner
