@echo off
if exist "%~dp0.venv\Scripts\python.exe" (
  "%~dp0.venv\Scripts\python.exe" "%~dp0engine\agent.py" verify --run reviewed_gpt54_repeat1 --full
) else (
  python "%~dp0engine\agent.py" verify --run reviewed_gpt54_repeat1 --full
)
