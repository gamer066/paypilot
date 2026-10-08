@echo off
REM Records your whole screen to demo_backup.mp4. Press Q in this window to stop.
cd /d "%~dp0"
echo Recording starts in 5 seconds. Switch to the PayPilot browser tab. Press Q here to stop.
timeout /t 5 >nul
ffmpeg -y -f gdigrab -framerate 15 -i desktop -c:v libx264 -preset ultrafast -pix_fmt yuv420p demo_backup.mp4
