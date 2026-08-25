@echo off
title Mark LI - Install Requirements
cd /d "%~dp0"

echo ==========================================
echo       MARK LI - INSTALLING REQUIREMENTS
echo ==========================================
echo.

set PYTHON=C:\Users\fivxb\AppData\Local\Programs\Python\Python314\python.exe

echo Updating pip...
"%PYTHON%" -m pip install --upgrade pip

echo.
echo Installing Mark LI dependencies...
"%PYTHON%" -m pip install ^
sounddevice ^
google-genai ^
numpy ^
requests ^
httpx ^
pillow ^
python-dotenv ^
psutil ^
pyautogui ^
keyboard ^
pyperclip ^
SpeechRecognition ^
edge-tts ^
pygame ^
PySide6 ^
customtkinter ^
beautifulsoup4 ^
lxml ^
aiohttp ^
websockets ^
yt-dlp

echo.
echo ==========================================
echo       INSTALLATION COMPLETE
echo ==========================================
echo.

echo Testing imports...
"%PYTHON%" -c "import sounddevice; from google import genai; import numpy; import requests; import PIL; import dotenv; import psutil; import pyautogui; import pygame; import PySide6; print('ALL IMPORTS OK')"

echo.
pause