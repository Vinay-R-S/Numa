@echo off
echo.
echo ╔════════════════════════════════════════════════════════════╗
echo ║         HEALTH DASHBOARD - ONE-CLICK STARTUP               ║
echo ╚════════════════════════════════════════════════════════════╝
echo.

REM Check if this is first run
if not exist "dashboard-ui\node_modules" (
    echo [FIRST TIME SETUP DETECTED]
    echo.
    echo Installing dependencies...
    echo.
    
    REM Install Python dependencies
    echo [1/2] Installing Python packages...
    pip install -r requirements.txt > nul 2>&1
    if %errorlevel% neq 0 (
        echo ERROR: Failed to install Python dependencies
        echo Make sure Python is installed: python.org
        pause
        exit /b 1
    )
    echo ✓ Python packages installed
    
    REM Install React dependencies
    echo [2/2] Installing React packages...
    cd dashboard-ui
    call npm install > nul 2>&1
    if %errorlevel% neq 0 (
        echo ERROR: Failed to install React dependencies
        echo Make sure Node.js is installed: nodejs.org
        cd ..
        pause
        exit /b 1
    )
    cd ..
    echo ✓ React packages installed
    echo.
    echo ══════════════════════════════════════════════════════════
    echo Setup complete!
    echo ══════════════════════════════════════════════════════════
    echo.
)

REM Check if Google Fit is authorized
if not exist "token.json" (
    echo.
    echo ╔════════════════════════════════════════════════════════════╗
    echo ║         GOOGLE FIT AUTHORIZATION REQUIRED                  ║
    echo ╚════════════════════════════════════════════════════════════╝
    echo.
    echo First-time setup: Authorizing Google Fit...
    echo.
    echo A browser window will open. Please:
    echo   1. Sign in with your Google account
    echo   2. Grant permissions for Fitness API
    echo   3. Return to this window
    echo.
    pause
    python google_fit_api.py
    if %errorlevel% neq 0 (
        echo.
        echo ERROR: Authorization failed
        echo Make sure credentials.json exists in this folder
        pause
        exit /b 1
    )
    echo.
    echo ✓ Google Fit authorized successfully!
    echo.
)

echo.
echo ══════════════════════════════════════════════════════════
echo Starting Health Dashboard...
echo ══════════════════════════════════════════════════════════
echo.
echo [Backend ] Flask API starting on http://localhost:5000
echo [Frontend] React app will open at http://localhost:3000
echo.
echo Press Ctrl+C in BOTH windows to stop the servers
echo ══════════════════════════════════════════════════════════
echo.
timeout /t 2 > nul

REM Start Flask API in new window
start "Health Dashboard - API Server" cmd /k "python api_server.py"

REM Wait a moment for API to start
timeout /t 3 > nul

REM Start React dev server in new window
start "Health Dashboard - Frontend" cmd /k "cd dashboard-ui && npm run dev"

echo.
echo ✓ Both servers started in separate windows
echo.
echo Dashboard should open automatically in your browser
echo If not, open: http://localhost:3000
echo.
echo To stop: Close both terminal windows or press Ctrl+C
echo.
