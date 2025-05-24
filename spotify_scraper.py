#!/usr/bin/env python3
"""
Spotify Playlist Scraper Backend
Uses headless browser to extract tracks automatically with multi-browser fallback
"""

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import re
import os
import time
import glob
import signal
import sys
from datetime import datetime
from contextlib import contextmanager

app = Flask(__name__)
CORS(app)

def log_message(message):
    """Log message to both console and file"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    log_line = f"[{timestamp}] {message}"
    print(log_line, flush=True)
    
    try:
        with open('scraper_log.txt', 'a', encoding='utf-8') as f:
            f.write(log_line + "\n")
    except:
        pass  # Don't fail if we can't write to log file

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

@contextmanager
def timeout_handler(seconds):
    """Context manager for handling timeouts"""
    def timeout_signal(signum, frame):
        raise TimeoutError(f"Operation timed out after {seconds} seconds")
    
    # Set the signal handler
    old_handler = signal.signal(signal.SIGALRM, timeout_signal)
    signal.alarm(seconds)
    
    try:
        yield
    finally:
        # Restore the old signal handler
        signal.signal(signal.SIGALRM, old_handler)
        signal.alarm(0)

def check_browser_availability():
    """Check what browsers and drivers are available"""
    availability = {
        'browsers': {},
        'drivers': {}
    }
    
    # Check browsers
    browser_paths = [
        ('/usr/bin/google-chrome', 'google-chrome'),
        ('/usr/bin/google-chrome-stable', 'google-chrome-stable'),
        ('/usr/bin/chromium-browser', 'chromium-browser'),
        ('/usr/bin/chromium', 'chromium'),
        ('/usr/bin/firefox', 'firefox'),
        ('/usr/bin/firefox-esr', 'firefox-esr')
    ]
    
    for path, name in browser_paths:
        availability['browsers'][name] = os.path.exists(path)
    
    # Check drivers
    driver_paths = [
        ('/usr/local/bin/chromedriver', 'chromedriver-local'),
        ('/usr/bin/chromedriver', 'chromedriver-system'),
        ('/usr/bin/chromium-chromedriver', 'chromium-chromedriver'),
        ('/usr/local/bin/geckodriver', 'geckodriver-local'),
        ('/usr/bin/geckodriver', 'geckodriver-system')
    ]
    
    for path, name in driver_paths:
        availability['drivers'][name] = os.path.exists(path)
    
    return availability
# Replace your browser setup functions with these webdriver-manager only versions

def setup_chrome_driver():
    """Set up Chrome driver using webdriver-manager only"""
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.chrome.options import Options
        from webdriver_manager.chrome import ChromeDriverManager
        
        log_message("🔧 Setting up Chrome with webdriver-manager...")
        
        options = Options()
        
        # Essential headless options
        chrome_options = [
            '--headless=new',
            '--no-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu',
            '--window-size=1920,1080',
            '--disable-extensions',
            '--disable-plugins',
            '--disable-images',
            '--single-process',
            '--memory-pressure-off',
            '--disable-web-security',
            '--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
        ]
        
        for option in chrome_options:
            options.add_argument(option)
        
        # Let webdriver-manager handle everything
        log_message("📥 Downloading Chrome and ChromeDriver via webdriver-manager...")
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        
        log_message("✅ Chrome driver created successfully with webdriver-manager!")
        return driver
        
    except Exception as e:
        log_message(f"❌ Chrome webdriver-manager setup failed: {e}")
        raise

def setup_firefox_driver():
    """Set up Firefox driver using webdriver-manager only"""
    try:
        from selenium import webdriver
        from selenium.webdriver.firefox.service import Service
        from selenium.webdriver.firefox.options import Options
        from webdriver_manager.firefox import GeckoDriverManager
        
        log_message("🦊 Setting up Firefox with webdriver-manager...")
        
        options = Options()
        firefox_options = [
            '--headless',
            '--width=1920',
            '--height=1080',
            '--disable-gpu'
        ]
        
        for option in firefox_options:
            options.add_argument(option)
        
        # Let webdriver-manager handle everything
        log_message("📥 Downloading Firefox and GeckoDriver via webdriver-manager...")
        service = Service(GeckoDriverManager().install())
        driver = webdriver.Firefox(service=service, options=options)
        
        log_message("✅ Firefox driver created successfully with webdriver-manager!")
        return driver
        
    except Exception as e:
        log_message(f"❌ Firefox webdriver-manager setup failed: {e}")
        raise

def _try_chrome_with_driver(options, driver_path):
    """Try Chrome with specific driver path"""
    if not driver_path or not os.path.exists(driver_path):
        raise Exception(f"Driver path not found: {driver_path}")
    
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    
    service = Service(driver_path)
    return webdriver.Chrome(service=service, options=options)

def _try_chrome_with_webdriver_manager(options):
    """Try Chrome with webdriver-manager"""
    try:
        from webdriver_manager.chrome import ChromeDriverManager
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        
        service = Service(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=options)
    except ImportError:
        raise Exception("webdriver-manager not available")

def setup_firefox_driver():
    """Set up Firefox headless driver"""
    try:
        from selenium import webdriver
        from selenium.webdriver.firefox.service import Service
        from selenium.webdriver.firefox.options import Options
        
        log_message("🦊 Setting up Firefox driver...")
        
        options = Options()
        firefox_options = [
            '--headless',
            '--width=1920',
            '--height=1080',
            '--disable-gpu'
        ]
        
        for option in firefox_options:
            options.add_argument(option)
        
        # Try to find Firefox binary
        firefox_paths = [
            '/usr/bin/firefox',
            '/usr/bin/firefox-esr'
        ]
        
        found_firefox = None
        for path in firefox_paths:
            if os.path.exists(path):
                found_firefox = path
                log_message(f"📍 Found Firefox at: {found_firefox}")
                break
        
        if found_firefox:
            options.binary_location = found_firefox
        
        # Try different driver approaches
        driver_attempts = [
            # Method 1: Use environment variable
            lambda: _try_firefox_with_driver(options, os.environ.get('GECKODRIVER_PATH')),
            # Method 2: Use local bin
            lambda: _try_firefox_with_driver(options, '/usr/local/bin/geckodriver'),
            # Method 3: Use system bin  
            lambda: _try_firefox_with_driver(options, '/usr/bin/geckodriver'),
            # Method 4: Let selenium find driver
            lambda: webdriver.Firefox(options=options),
            # Method 5: Try webdriver-manager
            lambda: _try_firefox_with_webdriver_manager(options)
        ]
        
        for i, attempt in enumerate(driver_attempts, 1):
            try:
                log_message(f"🔧 Firefox driver attempt {i}...")
                driver = attempt()
                if driver:
                    log_message(f"✅ Firefox driver created successfully on attempt {i}!")
                    return driver
            except Exception as e:
                log_message(f"❌ Firefox attempt {i} failed: {str(e)[:100]}")
                continue
        
        raise Exception("All Firefox driver attempts failed")
        
    except Exception as e:
        log_message(f"❌ Firefox setup failed: {e}")
        raise

def _try_firefox_with_driver(options, driver_path):
    """Try Firefox with specific driver path"""
    if not driver_path or not os.path.exists(driver_path):
        raise Exception(f"Driver path not found: {driver_path}")
    
    from selenium import webdriver
    from selenium.webdriver.firefox.service import Service
    
    service = Service(driver_path)
    return webdriver.Firefox(service=service, options=options)

def _try_firefox_with_webdriver_manager(options):
    """Try Firefox with webdriver-manager"""
    try:
        from webdriver_manager.firefox import GeckoDriverManager
        from selenium import webdriver
        from selenium.webdriver.firefox.service import Service
        
        service = Service(GeckoDriverManager().install())
        return webdriver.Firefox(service=service, options=options)
    except ImportError:
        raise Exception("webdriver-manager not available")

def extract_tracks_from_page(driver):
    """Extract track URIs from loaded Spotify page with comprehensive scrolling"""
    log_message("🔍 Extracting tracks from loaded page...")
    
    # Scroll down to load all tracks (Song Radio has 50 tracks)
    log_message("📜 Scrolling to load all tracks...")
    last_track_count = 0
    scroll_attempts = 0
    max_scroll_attempts = 15  # Increased for reliability
    
    while scroll_attempts < max_scroll_attempts:
        # Multiple scroll strategies
        scroll_strategies = [
            "window.scrollTo(0, document.body.scrollHeight);",
            "window.scrollBy(0, 1000);",
            "document.body.scrollTop = document.body.scrollHeight;",
            "document.documentElement.scrollTop = document.documentElement.scrollHeight;"
        ]
        
        for strategy in scroll_strategies:
            try:
                driver.execute_script(strategy)
                time.sleep(0.5)
            except:
                continue
        
        time.sleep(2)  # Wait for tracks to load
        
        # Count current tracks with multiple methods
        track_count_scripts = [
            "return document.querySelectorAll('[data-uri*=\"spotify:track:\"]').length;",
            "return document.querySelectorAll('[data-testid=\"tracklist-row\"]').length;",
            "return document.querySelectorAll('.tracklist-row').length;",
            "return document.querySelectorAll('[role=\"row\"]').length;"
        ]
        
        current_tracks = 0
        for script in track_count_scripts:
            try:
                count = driver.execute_script(script)
                current_tracks = max(current_tracks, count)
            except:
                continue
        
        log_message(f"   Scroll {scroll_attempts + 1}: Found {current_tracks} track elements")
        
        # If no new tracks loaded, we're done
        if current_tracks == last_track_count and current_tracks > 0:
            log_message(f"   No new tracks loaded, stopping scroll")
            break
            
        last_track_count = current_tracks
        scroll_attempts += 1
        
        # If we have 50+ tracks (Song Radio limit), we're probably done
        if current_tracks >= 50:
            log_message(f"   Found {current_tracks} tracks, likely all loaded")
            break
    
    log_message(f"🎯 Finished scrolling, found {last_track_count} total track elements")
    
    # Comprehensive JavaScript extraction with multiple methods
    js_extract = """
    let tracks = new Set(); // Use Set to avoid duplicates automatically
    
    // Method 1: Look for data-uri attributes (most reliable)
    document.querySelectorAll('[data-uri*="spotify:track:"]').forEach(el => {
        const uri = el.getAttribute('data-uri');
        if (uri && uri.startsWith('spotify:track:')) {
            tracks.add(uri);
        }
    });
    
    // Method 2: Look in track rows with data-uri
    document.querySelectorAll('[data-testid="tracklist-row"], .tracklist-row, [role="row"]').forEach(row => {
        const uriEl = row.querySelector('[data-uri]');
        if (uriEl) {
            const uri = uriEl.getAttribute('data-uri');
            if (uri && uri.startsWith('spotify:track:')) {
                tracks.add(uri);
            }
        }
    });
    
    // Method 3: Look for track links in rows
    document.querySelectorAll('[data-testid="tracklist-row"], .tracklist-row, [role="row"]').forEach(row => {
        const links = row.querySelectorAll('a[href*="/track/"]');
        links.forEach(link => {
            const href = link.getAttribute('href');
            const match = href.match(/\\/track\\/([a-zA-Z0-9]{22})/);
            if (match) {
                tracks.add('spotify:track:' + match[1]);
            }
        });
    });
    
    // Method 4: Look for track links anywhere
    document.querySelectorAll('a[href*="/track/"]').forEach(link => {
        const href = link.getAttribute('href');
        const match = href.match(/\\/track\\/([a-zA-Z0-9]{22})/);
        if (match) {
            tracks.add('spotify:track:' + match[1]);
        }
    });
    
    // Method 5: Look in any element with track data
    document.querySelectorAll('[data-track-uri], [data-track-id]').forEach(el => {
        const trackUri = el.getAttribute('data-track-uri');
        const trackId = el.getAttribute('data-track-id');
        
        if (trackUri && trackUri.startsWith('spotify:track:')) {
            tracks.add(trackUri);
        } else if (trackId && trackId.length === 22) {
            tracks.add('spotify:track:' + trackId);
        }
    });
    
    // Convert Set back to Array and return
    return Array.from(tracks);
    """
    
    try:
        tracks = driver.execute_script(js_extract)
        log_message(f"🎵 JavaScript extraction found {len(tracks) if tracks else 0} unique tracks")
        return tracks or []
    except Exception as e:
        log_message(f"❌ JavaScript extraction failed: {e}")
        return []

def scrape_with_headless_browser(playlist_id):
    """Use headless browser to scrape Spotify playlist with robust multi-browser support"""
    playlist_url = f"https://open.spotify.com/playlist/{playlist_id}"
    log_message(f"🚀 Starting headless browser for: {playlist_url}")
    
    # Check if Selenium is installed
    try:
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.common.exceptions import TimeoutException, WebDriverException
    except ImportError:
        raise Exception("Selenium not installed. Run: pip install selenium")
    
    driver = None
    tracks = []
    
    # Try browsers in order of preference
    browsers = [
        ('Chrome/Chromium', setup_chrome_driver),
        ('Firefox', setup_firefox_driver)
    ]
    
    for browser_name, setup_func in browsers:
        try:
            log_message(f"🔧 Trying {browser_name} headless browser...")
            
            # Use timeout handler for driver creation
            with timeout_handler(60):  # 60 second timeout for driver setup
                driver = setup_func()
            
            log_message(f"📡 Loading playlist page with {browser_name}...")
            
            # Use timeout for page loading
            with timeout_handler(45):  # 45 second timeout for page load
                driver.set_page_load_timeout(30)
                driver.get(playlist_url)
            
            # Wait for page to load
            log_message(f"⏳ Waiting for page to load...")
            time.sleep(8)  # Increased wait time
            
            # Try to wait for track elements with multiple selectors
            wait = WebDriverWait(driver, 20)  # Increased timeout
            element_found = False
            
            selectors = [
                '[data-testid="tracklist-row"]',
                '[data-uri*="spotify:track:"]',
                '.tracklist-row',
                '[role="row"]',
                'a[href*="/track/"]'
            ]
            
            for selector in selectors:
                try:
                    elements = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, selector)))
                    if elements:
                        log_message(f"✅ Found {len(elements)} elements with selector: {selector}")
                        element_found = True
                        break
                except TimeoutException:
                    log_message(f"⏰ Timeout waiting for selector: {selector}")
                    continue
            
            if not element_found:
                log_message(f"⚠️ No track elements found with {browser_name}, but proceeding...")
            
            # Extract tracks using JavaScript with timeout
            log_message(f"🎵 Extracting tracks with {browser_name}...")
            with timeout_handler(60):  # 60 second timeout for extraction
                tracks = extract_tracks_from_page(driver)
            
            if tracks and len(tracks) > 0:
                log_message(f"🎵 Successfully extracted {len(tracks)} tracks with {browser_name}")
                break
            else:
                log_message(f"❌ No tracks found with {browser_name}")
                
        except TimeoutError as e:
            log_message(f"⏰ {browser_name} timed out: {e}")
            continue
        except WebDriverException as e:
            log_message(f"❌ {browser_name} WebDriver error: {str(e)[:200]}")
            continue
        except Exception as e:
            log_message(f"❌ {browser_name} failed: {str(e)[:200]}")
            continue
        finally:
            if driver:
                try:
                    with timeout_handler(10):  # 10 second timeout for cleanup
                        driver.quit()
                except:
                    log_message("⚠️ Driver cleanup failed")
                    pass
                driver = None
    
    if not tracks:
        raise Exception("All browser attempts failed to extract tracks")
    
    # Remove duplicates and validate track URIs
    unique_tracks = []
    for track in tracks:
        if track and track.startswith('spotify:track:'):
            track_parts = track.split(':')
            if len(track_parts) == 3 and len(track_parts[2]) == 22:
                if track not in unique_tracks:
                    unique_tracks.append(track)
    
    log_message(f"✅ Final result: {len(unique_tracks)} valid unique tracks")
    return unique_tracks

@app.route('/health')
def health_check():
    """Health check endpoint with browser availability"""
    log_message("🏥 Health check requested")
    
    availability = check_browser_availability()
    
    return jsonify({
        'status': 'healthy',
        'message': 'Headless browser scraper running',
        'browser_availability': availability,
        'timestamp': str(datetime.now())
    })

@app.route('/test')
def test_endpoint():
    """Test endpoint"""
    log_message("🧪 Test endpoint called")
    return jsonify({
        'message': 'Headless browser backend working!',
        'timestamp': str(datetime.now()),
        'browser_availability': check_browser_availability()
    })

@app.route('/debug-selenium')
def debug_selenium():
    """Debug Selenium setup with comprehensive browser testing"""
    log_message("🧪 Testing Selenium setup...")
    
    try:
        debug_info = {
            'environment_variables': {
                'CHROME_BIN': os.environ.get('CHROME_BIN', 'Not set'),
                'CHROMEDRIVER_PATH': os.environ.get('CHROMEDRIVER_PATH', 'Not set'),
                'GECKODRIVER_PATH': os.environ.get('GECKODRIVER_PATH', 'Not set'),
                'DISPLAY': os.environ.get('DISPLAY', 'Not set')
            }
        }
        
        # Check browser and driver availability
        availability = check_browser_availability()
        debug_info.update(availability)
        
        # Test Selenium import
        try:
            from selenium import webdriver
            debug_info['selenium_import'] = 'Success'
        except ImportError as e:
            debug_info['selenium_import'] = f'Failed: {str(e)}'
            return jsonify({
                'status': 'debug_failed',
                'error': 'Selenium not available',
                'debug_info': debug_info
            }), 500
        
        # Test browser creation
        browser_tests = {}
        
        # Test Chrome/Chromium
        try:
            log_message("🧪 Testing Chrome driver creation...")
            driver = setup_chrome_driver()
            browser_tests['chrome'] = 'Success - driver created'
            driver.quit()
        except Exception as e:
            browser_tests['chrome'] = f'Failed: {str(e)[:300]}'
        
        # Test Firefox
        try:
            log_message("🧪 Testing Firefox driver creation...")
            driver = setup_firefox_driver()
            browser_tests['firefox'] = 'Success - driver created'
            driver.quit()
        except Exception as e:
            browser_tests['firefox'] = f'Failed: {str(e)[:300]}'
        
        debug_info['browser_creation_tests'] = browser_tests
        
        # Test webdriver-manager availability
        webdriver_manager_available = {}
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            webdriver_manager_available['chrome'] = 'Available'
        except ImportError:
            webdriver_manager_available['chrome'] = 'Not available'
        
        try:
            from webdriver_manager.firefox import GeckoDriverManager
            webdriver_manager_available['firefox'] = 'Available'
        except ImportError:
            webdriver_manager_available['firefox'] = 'Not available'
        
        debug_info['webdriver_manager'] = webdriver_manager_available
        
        log_message(f"🔍 Debug completed successfully")
        return jsonify({
            'status': 'debug_complete',
            'debug_info': debug_info,
            'timestamp': str(datetime.now())
        })
        
    except Exception as e:
        log_message(f"❌ Debug failed: {e}")
        return jsonify({
            'status': 'debug_failed',
            'error': str(e),
            'timestamp': str(datetime.now())
        }), 500

@app.route('/scrape', methods=['POST'])
def scrape_playlist():
    """Scrape a Spotify playlist using headless browser with comprehensive error handling"""
    log_message("="*60)
    log_message("🚨 HEADLESS BROWSER SCRAPE REQUEST!")
    log_message("="*60)
    
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
        
        # Check browser availability before attempting scrape
        availability = check_browser_availability()
        log_message(f"🔍 Browser availability: {availability}")
        
        has_browser = (
            any(availability['browsers'].values()) and 
            any(availability['drivers'].values())
        )
        
        if not has_browser:
            log_message("❌ No browsers or drivers available")
            return jsonify({
                'error': 'No browsers available for scraping',
                'browser_availability': availability
            }), 503
        
        # Use headless browser to scrape with timeout
        log_message("🚀 Starting scraping process...")
        with timeout_handler(300):  # 5 minute timeout for entire scrape process
            tracks = scrape_with_headless_browser(playlist_id)
        
        result = {
            'success': True,
            'playlist_id': playlist_id,
            'tracks': tracks,
            'count': len(tracks),
            'browser_availability': availability,
            'timestamp': str(datetime.now())
        }
        
        log_message(f"✅ Headless browser scraping completed: {len(tracks)} tracks")
        return jsonify(result)
        
    except ValueError as e:
        log_message(f"❌ Invalid URL: {e}")
        return jsonify({'error': f'Invalid playlist URL: {str(e)}'}), 400
    except TimeoutError as e:
        log_message(f"⏰ Scraping timed out: {e}")
        return jsonify({'error': f'Scraping timed out: {str(e)}'}), 504
    except Exception as e:
        log_message(f"❌ Headless browser error: {e}")
        return jsonify({'error': f'Headless browser error: {str(e)}'}), 500

@app.route('/')
def serve_frontend():
    """Serve the frontend"""
    try:
        if os.path.exists('index.html'):
            with open('index.html', 'r', encoding='utf-8') as f:
                return f.read()
    except Exception as e:
        log_message(f"❌ Error serving frontend: {e}")
    
    # Fallback HTML
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>🚀 Spotify Headless Browser Scraper</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; background: #191414; color: white; }}
            .container {{ max-width: 800px; margin: 0 auto; }}
            .status {{ background: rgba(29, 185, 84, 0.1); padding: 20px; border-radius: 10px; margin: 20px 0; }}
            a {{ color: #1DB954; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 Spotify Headless Browser Scraper</h1>
            <div class="status">
                <p><strong>Backend is running!</strong></p>
                <p>Timestamp: {datetime.now()}</p>
            </div>
            
            <h2>Available Endpoints:</h2>
            <ul>
                <li><a href="/health">GET /health</a> - Health check with browser availability</li>
                <li><a href="/debug-selenium">GET /debug-selenium</a> - Debug Selenium setup</li>
                <li><a href="/test">GET /test</a> - Test endpoint</li>
                <li>POST /scrape - Scrape playlist with headless browser</li>
            </ul>
            
            <h2>Browser Status:</h2>
            <pre>{check_browser_availability()}</pre>
        </div>
    </body>
    </html>
    """

if __name__ == '__main__':
    # Initialize logging
    try:
        with open('scraper_log.txt', 'w') as f:
            f.write(f"=== HEADLESS BROWSER SCRAPER STARTED at {datetime.now()} ===\n")
    except:
        pass
    
    # Log startup info
    log_message("🚀 Starting Spotify Headless Browser Scraper...")
    log_message(f"🐍 Python version: {sys.version}")
    log_message(f"📍 Current working directory: {os.getcwd()}")
    
    # Check browser availability at startup
    availability = check_browser_availability()
    log_message(f"🔍 Browser availability at startup: {availability}")
    
    # Get port from environment variable (for cloud deployment) or default to 5000
    port = int(os.environ.get('PORT', 5000))
    host = '0.0.0.0'  # Bind to all interfaces for cloud deployment
    
    log_message(f"📍 Server starting on: http://{host}:{port}")
    log_message("🤖 Multi-browser support: Chrome/Chromium + Firefox")
    log_message("📦 Dependencies: selenium, webdriver-manager (optional)")
    log_message("-" * 60)
    
    app.run(host=host, port=port, debug=False, use_reloader=False)