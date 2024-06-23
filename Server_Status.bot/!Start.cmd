@echo off
title "SoulMask_bot %cd%"

:start
python SoulMask_bot.py
timeout /t 5
goto start
