@echo off
echo Starting Spotify Playlist Cleaner Backend...
echo.

REM Activate virtual environment
call spotify-env\Scripts\activate

REM Check if packages are installed
python -c "import flask, requests, bs4; print('✅ All packages installed')" 2>nul || (
    echo Installing required packages...
    pip install flask flask-cors requests beautifulsoup4
)

echo.
echo 🚀 Starting Python backend server...
echo 📍 Frontend will be available at: http://localhost:5000
echo 💡 Make sure Spotify is logged out in incognito browser for best results
echo.
echo Press Ctrl+C to stop the server
echo.

python spotify_scraper.py

pause