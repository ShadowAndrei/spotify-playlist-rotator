@echo off
setlocal enabledelayedexpansion
title Spotify Rotator -- Build Pipeline
chcp 65001 >nul

echo.
echo  ============================================
echo   Spotify Playlist Rotator v4.0 - Builder
echo  ============================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Add Python to PATH.
    pause & exit /b 1
)
for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo [OK] Python %PYVER%

:: Upgrade pip
echo.
echo [1/6] Upgrading pip...
python -m pip install --upgrade pip --quiet
echo       Done.

:: Install pythonnet from binary ONLY - avoids NuGet build failure
echo.
echo [2/6] Installing pythonnet (binary wheel only)...
pip install pythonnet --only-binary :all: --quiet
if errorlevel 1 (
    pip install "pythonnet==3.0.3" --only-binary :all: --quiet
    if errorlevel 1 (
        echo       [WARNING] pythonnet binary unavailable, continuing anyway...
    )
)
echo       Done.

:: Install everything else
echo.
echo [3/6] Installing dependencies...
pip install "pywebview>=4.0" spotipy python-dotenv playsound Pillow pyinstaller --quiet
if errorlevel 1 (
    echo [ERROR] Dependency install failed.
    pause & exit /b 1
)
echo       Done.

:: Generate icon
echo.
echo [4/6] Generating icon.ico...
if exist icon.ico (
    echo       Already exists, skipping.
) else (
    python create_icon.py
    if errorlevel 1 echo       [WARNING] Icon failed, building without it.
)

:: PyInstaller
echo.
echo [5/6] Building exe...
if exist dist\SpotifyRotator rd /s /q dist\SpotifyRotator >nul 2>&1
if exist build rd /s /q build >nul 2>&1
pyinstaller SpotifyRotator.spec --noconfirm
if errorlevel 1 (
    echo [ERROR] PyInstaller failed. Check output above.
    pause & exit /b 1
)
if not exist "dist\SpotifyRotator\SpotifyRotator.exe" (
    echo [ERROR] exe not found after build.
    pause & exit /b 1
)
echo       Done: dist\SpotifyRotator\SpotifyRotator.exe

:: Inno Setup
echo.
echo [6/6] Building installer...
set ISCC=
for %%p in ("C:\Program Files (x86)\Inno Setup 6\ISCC.exe" "C:\Program Files\Inno Setup 6\ISCC.exe" "C:\Program Files (x86)\Inno Setup 5\ISCC.exe") do (
    if exist %%p set ISCC=%%p
)
if "!ISCC!"=="" (
    echo       Inno Setup not found - get it at jrsoftware.org/isinfo.php
    goto :done
)
if not exist installer_output mkdir installer_output
!ISCC! SpotifyRotator.iss /Q
if errorlevel 1 ( echo [ERROR] Inno Setup failed. & pause & exit /b 1 )
echo       Done: installer_output\SpotifyRotator_v4.0.0_Setup.exe

:done
echo.
echo  ============================================
echo   All done!
echo  ============================================
echo.
echo   Portable:   dist\SpotifyRotator\SpotifyRotator.exe
if exist "installer_output\SpotifyRotator_v4.0.0_Setup.exe" (
    echo   Installer:  installer_output\SpotifyRotator_v4.0.0_Setup.exe
)
echo.
echo   To push to GitHub:
echo     git add .
echo     git commit -m "v4.0.0"
echo     git tag v4.0.0
echo     git push && git push --tags
echo.
pause
