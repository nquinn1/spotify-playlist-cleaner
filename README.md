# Spotify Playlist Cleaner

Automatically extract original tracks from Spotify's personalized "Song Radio" playlists using headless browser technology.

## What it does

- Takes a personalized Spotify playlist URL (like Song Radio)
- Uses headless browser to extract the original, non-personalized tracks
- Creates a new playlist in your account with all 50 original tracks
- Bypasses Spotify's client-side personalization

## Deployment to Railway

### 1. Prepare Files
Ensure you have these files in your project:
- `spotify_scraper.py` (main application)
- `index.html` (frontend)
- `requirements.txt` (dependencies)
- `Procfile` (Railway config)
- `railway.json` (deployment config)

### 2. Create GitHub Repository
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/yourusername/spotify-cleaner.git
git push -u origin main
```

### 3. Deploy to Railway
1. Go to [railway.app](https://railway.app)
2. Sign up/login with GitHub
3. Click "New Project" → "Deploy from GitHub repo"
4. Select your repository
5. Railway will automatically detect Python and deploy

### 4. Update Spotify App Settings
1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Edit your app settings
3. Add new redirect URI: `https://your-app-name.up.railway.app/`
4. Update the `CLIENT_ID` in your deployed `index.html`

### 5. Environment Variables (Optional)
No additional environment variables needed - Railway handles everything automatically.

## Local Development

```bash
pip install -r requirements.txt
python spotify_scraper.py
```

Access at: `http://127.0.0.1:5000`

## Dependencies

- Flask (web framework)
- Selenium (headless browser)
- Chrome/Chromium (automatically installed on Railway)
- webdriver-manager (automatic driver management)