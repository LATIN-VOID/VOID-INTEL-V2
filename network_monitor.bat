@echo off
title VOID INTEL-V2 - Network Monitor
color 0A

:LOOP
cls

echo ==========================================
echo          VOID INTEL-V2
echo          NETWORK MONITOR
echo ==========================================
echo.
echo Active Network Connections:
echo.

netstat -ano | findstr ESTABLISHED

echo.
echo ==========================================
echo Checking again in 10 seconds...
echo Press CTRL+C to stop.
echo ==========================================

timeout /t 10 /nobreak >nul
goto LOOP