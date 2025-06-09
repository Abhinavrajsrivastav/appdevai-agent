@echo off
echo ========================================
echo       Starting Dev AI Agent...
echo ========================================
echo.

echo Step 1: Activating virtual environment
cd backend
if not exist venv (
    echo Virtual environment not found. Creating new one...
    python -m venv venv
)

call venv\Scripts\activate

echo Step 2: Installing dependencies
pip install -r requirements.txt

echo Step 3: Checking API key configuration
if not exist .env (
    echo WARNING: .env file not found in the backend directory.
    echo Creating a default .env file. You need to edit it with your API key.
    echo # Google Gemini API Key > .env
    echo # Replace the line below with your actual API key from https://makersuite.google.com/app/apikey >> .env
    echo GEMINI_API_KEY=your-api-key-here >> .env
    echo. >> .env
    echo # Optional Configuration >> .env
    echo MAX_TOKENS=1024 >> .env
    echo TEMPERATURE=0.7 >> .env
    echo.
    echo IMPORTANT: Please edit the .env file with your API key before continuing.
    echo Press any key to open the .env file for editing...
    pause > nul
    notepad .env
)

echo Step 4: Starting the server
echo.
echo The backend server will start now. Please keep this window open.
echo To view the application, open frontend/index.html in your browser.
echo.
echo NOTE: If you see API key errors, please edit the .env file with a valid key.
echo Press Ctrl+C to stop the server when you're done.
echo.
uvicorn main:app --reload --log-level info

pause
