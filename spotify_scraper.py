#!/usr/bin/env python3
"""
Spotify Playlist Scraper Backend
Uses headless browser to extract tracks automatically
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import re
import os
import time
from datetime import datetime

app = Flask(__name__)
CORS(app)

def log_message(message):
    """Log message to both console and file"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    log_line = f"[{timestamp}] {message}"
    print(log_line, flush=True)
    
    with open('scraper_log.txt', 'a', encoding='utf-8') as f:
        f.write(log_line + "\n")

def extract_playlist_id(url):
    """Extract playlist ID from Spotify URL"""
    clean_url = url.split('?')[0]
    patterns = [
        r'spotify:playlist:([a-zA-Z0-9]+)',
        r'open\.spotify\.com/playlist/([a-zA-Z0-9]+)',
        r'playlist/([a-zA-Z0-9]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, clean_url)
        if match:
            return match.group(1)
    
    raise ValueError('Invalid Spotify playlist URL')

def setup_chrome_driver():
    """Set up Chrome headless driver for cloud deployment"""
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.chrome.options import Options
        
        options = Options()
        # Cloud-specific Chrome options
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-features=VizDisplayCompositor')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--remote-debugging-port=9222')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-plugins')
        options.add_argument('--disable-images')
        options.add_argument('--disable-javascript')
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        # Try webdriver-manager first
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            log_message("🔧 Using webdriver-manager for Chrome (cloud)")
            service = Service(ChromeDriverManager().install())
            return webdriver.Chrome(service=service, options=options)
        except Exception as e:
            log_message(f"❌ webdriver-manager failed: {e}")
            log_message("🔧 Trying system ChromeDriver")
            return webdriver.Chrome(options=options)
            
    except Exception as e:
        log_message(f"❌ Chrome setup failed: {e}")
        raise

def setup_firefox_driver():
    """Set up Firefox headless driver"""
    try:
        from selenium import webdriver
        from selenium.webdriver.firefox.service import Service
        from selenium.webdriver.firefox.options import Options
        
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--width=1920')
        options.add_argument('--height=1080')
        
        # Try webdriver-manager first
        try:
            from webdriver_manager.firefox import GeckoDriverManager
            log_message("🔧 Using webdriver-manager for Firefox")
            service = Service(GeckoDriverManager().install())
            return webdriver.Firefox(service=service, options=options)
        except ImportError:
            log_message("🔧 Using system GeckoDriver")
            return webdriver.Firefox(options=options)
            
    except Exception as e:
        log_message(f"❌ Firefox setup failed: {e}")
        raise

def extract_tracks_from_page(driver):
    """Extract track URIs from loaded Spotify page with scrolling to load all tracks"""
    log_message("🔍 Extracting tracks from loaded page...")
    
    # Scroll down to load all tracks (Song Radio has 50 tracks)
    log_message("📜 Scrolling to load all tracks...")
    last_track_count = 0
    scroll_attempts = 0
    max_scroll_attempts = 10
    
    while scroll_attempts < max_scroll_attempts:
        # Scroll to bottom
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)  # Wait for tracks to load
        
        # Count current tracks
        current_tracks = driver.execute_script("""
            return document.querySelectorAll('[data-uri*="spotify:track:"], [data-testid="tracklist-row"]').length;
        """)
        
        log_message(f"   Scroll {scroll_attempts + 1}: Found {current_tracks} track elements")
        
        # If no new tracks loaded, we're done
        if current_tracks == last_track_count:
            log_message(f"   No new tracks loaded, stopping scroll")
            break
            
        last_track_count = current_tracks
        scroll_attempts += 1
        
        # If we have 50+ tracks (Song Radio limit), we're probably done
        if current_tracks >= 50:
            log_message(f"   Found {current_tracks} tracks, likely all loaded")
            break
    
    log_message(f"🎯 Finished scrolling, found {last_track_count} total track elements")
    
    # JavaScript to extract all tracks after scrolling
    js_extract = """
    let tracks = [];
    
    // Method 1: Look for data-uri attributes
    document.querySelectorAll('[data-uri*="spotify:track:"]').forEach(el => {
        const uri = el.getAttribute('data-uri');
        if (uri && uri.startsWith('spotify:track:')) {
            tracks.push(uri);
        }
    });
    
    // Method 2: Look in track rows
    document.querySelectorAll('[data-testid="tracklist-row"], .tracklist-row, [role="row"]').forEach(row => {
        const uriEl = row.querySelector('[data-uri]');
        if (uriEl) {
            const uri = uriEl.getAttribute('data-uri');
            if (uri && uri.startsWith('spotify:track:')) {
                tracks.push(uri);
            }
        }
    });
    
    // Method 3: Look for track links
    document.querySelectorAll('a[href*="/track/"]').forEach(link => {
        const href = link.getAttribute('href');
        const match = href.match(/\\/track\\/([a-zA-Z0-9]{22})/);
        if (match) {
            tracks.push('spotify:track:' + match[1]);
        }
    });
    
    // Remove duplicates and return
    return [...new Set(tracks)];
    """
    
    try:
        tracks = driver.execute_script(js_extract)
        log_message(f"🎵 JavaScript extraction found {len(tracks) if tracks else 0} unique tracks after scrolling")
        return tracks or []
    except Exception as e:
        log_message(f"❌ JavaScript extraction failed: {e}")
        return []

def scrape_with_headless_browser(playlist_id):
    """Use headless browser to scrape Spotify playlist"""
    playlist_url = f"https://open.spotify.com/playlist/{playlist_id}"
    log_message(f"🚀 Starting headless browser for: {playlist_url}")
    
    # Check if Selenium is installed
    try:
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.common.exceptions import TimeoutException
    except ImportError:
        raise Exception("Selenium not installed. Run: pip install selenium webdriver-manager")
    
    driver = None
    tracks = []
    
    # Try Chrome first, then Firefox
    browsers = [
        ('Chrome', setup_chrome_driver),
        ('Firefox', setup_firefox_driver)
    ]
    
    for browser_name, setup_func in browsers:
        try:
            log_message(f"🔧 Trying {browser_name} headless browser...")
            driver = setup_func()
            
            log_message(f"📡 Loading playlist page...")
            driver.get(playlist_url)
            
            # Wait for page to load
            log_message(f"⏳ Waiting for page to load...")
            time.sleep(5)  # Give it time to load
            
            # Try to wait for track elements
            wait = WebDriverWait(driver, 15)
            try:
                # Wait for any track-related elements
                selectors = [
                    '[data-testid="tracklist-row"]',
                    '[data-uri*="spotify:track:"]',
                    '.tracklist-row',
                    '[role="row"]'
                ]
                
                for selector in selectors:
                    try:
                        elements = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, selector)))
                        if elements:
                            log_message(f"✅ Found {len(elements)} elements with selector: {selector}")
                            break
                    except TimeoutException:
                        continue
                        
            except TimeoutException:
                log_message(f"⏰ Timeout waiting for elements, proceeding anyway...")
            
            # Extract tracks using JavaScript
            tracks = extract_tracks_from_page(driver)
            
            if tracks:
                log_message(f"🎵 Successfully extracted {len(tracks)} tracks with {browser_name}")
                break
            else:
                log_message(f"❌ No tracks found with {browser_name}")
                
        except Exception as e:
            log_message(f"❌ {browser_name} failed: {str(e)[:100]}...")
            continue
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass
                driver = None
    
    if not tracks:
        raise Exception("All browser attempts failed to extract tracks")
    
    # Remove duplicates and validate
    unique_tracks = []
    for track in tracks:
        if track.startswith('spotify:track:') and len(track.split(':')[2]) == 22:
            if track not in unique_tracks:
                unique_tracks.append(track)
    
    log_message(f"✅ Final result: {len(unique_tracks)} valid tracks")
    return unique_tracks

@app.route('/health')
def health_check():
    """Health check endpoint"""
    log_message("🏥 Health check requested")
    return jsonify({'status': 'healthy', 'message': 'Headless browser scraper running'})

@app.route('/test')
def test_endpoint():
    """Test endpoint"""
    log_message("🧪 Test endpoint called")
    return jsonify({'message': 'Headless browser backend working!', 'timestamp': str(datetime.now())})

@app.route('/scrape', methods=['POST'])
def scrape_playlist():
    """Scrape a Spotify playlist using headless browser"""
    log_message("="*50)
    log_message("🚨 HEADLESS BROWSER SCRAPE REQUEST!")
    log_message("="*50)
    
    try:
        data = request.get_json()
        
        if not data or 'url' not in data:
            log_message("❌ Missing playlist URL")
            return jsonify({'error': 'Missing playlist URL'}), 400
        
        playlist_url = data['url']
        log_message(f"🎯 Headless browser scrape: {playlist_url}")
        
        # Extract playlist ID
        playlist_id = extract_playlist_id(playlist_url)
        log_message(f"📝 Extracted playlist ID: {playlist_id}")
        
        # Use headless browser to scrape
        tracks = scrape_with_headless_browser(playlist_id)
        
        result = {
            'success': True,
            'playlist_id': playlist_id,
            'tracks': tracks,
            'count': len(tracks)
        }
        
        log_message(f"✅ Headless browser scraping completed: {len(tracks)} tracks")
        return jsonify(result)
        
    except ValueError as e:
        log_message(f"❌ Invalid URL: {e}")
        return jsonify({'error': f'Invalid playlist URL: {str(e)}'}), 400
    except Exception as e:
        log_message(f"❌ Headless browser error: {e}")
        return jsonify({'error': f'Headless browser error: {str(e)}'}), 500

@app.route('/')
def serve_frontend():
    """Serve the frontend"""
    if os.path.exists('index.html'):
        with open('index.html', 'r', encoding='utf-8') as f:
            return f.read()
    else:
        return """
        <h1>🚀 Spotify Headless Browser Scraper</h1>
        <p>Headless browser backend is running!</p>
        <p>Endpoints:</p>
        <ul>
            <li>GET /health - Health check</li>
            <li>POST /scrape - Scrape with headless browser</li>
        </ul>
        """

if __name__ == '__main__':
    # Clear log file
    with open('scraper_log.txt', 'w') as f:
        f.write(f"=== HEADLESS BROWSER SCRAPER STARTED at {datetime.now()} ===\n")
    
    # Get port from environment variable (for cloud deployment) or default to 5000
    port = int(os.environ.get('PORT', 5000))
    host = '0.0.0.0'  # Bind to all interfaces for cloud deployment
    
    print("🚀 Starting Headless Browser Spotify Scraper...")
    print(f"📍 Server: http://{host}:{port}")
    print("🤖 Uses Selenium headless browser to extract tracks")
    print("📦 Install: pip install selenium webdriver-manager")
    print("-" * 60)
    
    app.run(host=host, port=port, debug=False, use_reloader=False)