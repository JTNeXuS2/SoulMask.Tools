@echo off
title "SoulMask_bot %cd%"
mode con:cols=70 lines=8

:start
python SoulMask_bot.py
timeout /t 5
goto start
