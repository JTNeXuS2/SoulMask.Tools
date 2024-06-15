@echo off
title "SoulMask LogBot 1"
mode con:cols=70 lines=7

:start
echo Started
python LogBot.py
timeout /t 5
goto start
