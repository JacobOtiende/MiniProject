@echo off
REM MyAgent convenience runner - Windows batch script
REM Usage: run triage | rundown | achievements | review

if "%1%"=="" (
    echo MyAgent - School Operations Assistant
    echo.
    echo Usage:
    echo   run triage          - Process new school emails
    echo   run rundown         - Daily briefing (calendar + email)
    echo   run achievements    - Summary of completed tasks
    echo   run review          - Rundown + approval review
    echo.
    exit /b 0
)

if "%1%"=="triage" (
    python main.py triage
) else if "%1%"=="rundown" (
    python main.py rundown
) else if "%1%"=="achievements" (
    python main.py achievements
) else if "%1%"=="review" (
    python main.py rundown --review
) else (
    echo Unknown command: %1%
    echo Valid commands: triage, rundown, achievements, review
    exit /b 1
)
