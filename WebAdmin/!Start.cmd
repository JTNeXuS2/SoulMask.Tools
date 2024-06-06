@echo off
title "WebAdmin"

:start
python WebAdmin.py
timeout /t 5
goto start
