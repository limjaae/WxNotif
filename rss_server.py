from flask import Flask, render_template_string, request, jsonify, send_file
import os
import json
from datetime import datetime
import threading
import time
import glob
from scraper import scrape_ibm_deprecated_models, convert_to_rss_xml

app = Flask(__name__)

# Global variables to store the latest data
latest_data = []
latest_rss_content = ""
last_update_time = None
is_scraping = False

# HTML template for the web interface
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>IBM Watson RSS Feed Server</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 {
            color: #2c3e50;
            text-align: center;
            margin-bottom: 30px;
        }
        .status {
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
            font-weight: bold;
        }
        .status.success { background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .status.error { background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        .status.info { background-color: #d1ecf1; color: #0c5460; border: 1px solid #bee5eb; }
        .button {
            background-color: #007bff;
            color: white;
            padding: 12px 24px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
            margin: 10px 5px;
            text-decoration: none;
            display: inline-block;
        }
        .button:hover { background-color: #0056b3; }
        .button:disabled { background-color: #6c757d; cursor: not-allowed; }
        .button.secondary { background-color: #6c757d; }
        .button.secondary:hover { background-color: #545b62; }
        .feed-info {
            background-color: #e9ecef;
            padding: 20px;
            border-radius: 5px;
            margin: 20px 0;
        }
        .feed-url {
            background-color: #f8f9fa;
            padding: 10px;
            border-radius: 3px;
            font-family: monospace;
            word-break: break-all;
            border: 1px solid #dee2e6;
        }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }
        .stat-card {
            background: white;
            padding: 20px;
            border-radius: 5px;
            text-align: center;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        .stat-number {
            font-size: 2em;
            font-weight: bold;
            color: #007bff;
        }
        .stat-label {
            color: #6c757d;
            margin-top: 5px;
        }
        .loading {
            display: none;
            text-align: center;
            margin: 20px 0;
        }
        .spinner {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #007bff;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 IBM Watson RSS Feed Server</h1>
        
        <div id="status" class="status info">
            {% if last_update_time %}
                Last updated: {{ last_update_time }}
            {% else %}
                No data available. Click "Update Feed" to start.
            {% endif %}
        </div>

        <div class="stats">
            <div class="stat-card">
                <div class="stat-number">{{ models_count }}</div>
                <div class="stat-label">Models Found</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ models_with_alternatives }}</div>
                <div class="stat-label">With Alternatives</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ models_without_alternatives }}</div>
                <div class="stat-label">Without Alternatives</div>
            </div>
        </div>

        <div class="feed-info">
            <h3>📡 RSS Feed URL</h3>
            <p>Use this URL in your RSS reader:</p>
            <div class="feed-url">{{ feed_url }}</div>
            <p><strong>Supported RSS Readers:</strong> Feedly, Inoreader, Feedbro, QuiteRSS, and most others.</p>
        </div>

        <div style="text-align: center;">
            <button id="updateBtn" class="button" onclick="updateFeed()">
                🔄 Update Feed
            </button>
            <a href="/feed.xml" class="button secondary" target="_blank">
                📄 View RSS XML
            </a>
            <a href="/api/data" class="button secondary" target="_blank">
                📊 View JSON Data
            </a>
        </div>

        <div id="loading" class="loading">
            <div class="spinner"></div>
            <p>Updating feed... This may take a few moments.</p>
        </div>

        {% if latest_data %}
        <div style="margin-top: 30px;">
            <h3>📋 Latest Models (First 5)</h3>
            <div style="max-height: 400px; overflow-y: auto; border: 1px solid #dee2e6; border-radius: 5px; padding: 15px;">
                {% for model in latest_data[:5] %}
                <div style="border-bottom: 1px solid #eee; padding: 10px 0;">
                    <strong>{{ model.foundation_model_name }}</strong><br>
                    <small>
                        📅 Available: {{ model.availability_date }} | 
                        ⚠️ Deprecated: {{ model.deprecation_date }} | 
                        🗓️ Withdrawal: {{ model.withdrawal_date }}<br>
                        🔄 Alternative: {{ model.recommended_alternative }}
                    </small>
                </div>
                {% endfor %}
            </div>
        </div>
        {% endif %}
    </div>

    <script>
        function updateFeed() {
            const btn = document.getElementById('updateBtn');
            const loading = document.getElementById('loading');
            const status = document.getElementById('status');
            
            btn.disabled = true;
            loading.style.display = 'block';
            status.className = 'status info';
            status.textContent = 'Updating feed...';
            
            fetch('/api/update', { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        status.className = 'status success';
                        status.textContent = `Feed updated successfully! Found ${data.models_count} models.`;
                        setTimeout(() => {
                            location.reload();
                        }, 2000);
                    } else {
                        status.className = 'status error';
                        status.textContent = 'Error updating feed: ' + data.error;
                    }
                })
                .catch(error => {
                    status.className = 'status error';
                    status.textContent = 'Error updating feed: ' + error.message;
                })
                .finally(() => {
                    btn.disabled = false;
                    loading.style.display = 'none';
                });
        }

        // Auto-refresh status every 30 seconds
        setInterval(() => {
            fetch('/api/status')
                .then(response => response.json())
                .then(data => {
                    if (data.is_scraping) {
                        document.getElementById('status').textContent = 'Currently scraping...';
                    }
                });
        }, 30000);
    </script>
</body>
</html>
"""

def update_feed_data():
    """Update the feed data by running the scraper"""
    global latest_data, latest_rss_content, last_update_time, is_scraping
    
    is_scraping = True
    try:
        print("🔄 Running scraper...")
        # Run the scraper
        latest_data = scrape_ibm_deprecated_models()
        
        print(f"📊 Scraper returned {len(latest_data) if latest_data else 0} models")
        
        if latest_data:
            # Generate RSS content
            print("📝 Generating RSS content...")
            latest_rss_content = generate_rss_content(latest_data)
            last_update_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"✅ RSS content generated successfully!")
            return True, len(latest_data)
        else:
            print("❌ No data found from scraper")
            return False, "No data found"
    except Exception as e:
        print(f"❌ Error in update_feed_data: {e}")
        import traceback
        traceback.print_exc()
        return False, str(e)
    finally:
        is_scraping = False

def load_data_from_files():
    """Load data from existing JSON files as fallback"""
    global latest_data, latest_rss_content, last_update_time
    
    try:
        # Look for the most recent JSON file
        json_files = glob.glob("ibm_deprecated_models_*.json")
        if not json_files:
            print("❌ No existing JSON files found")
            return False, "No existing data files found"
        
        # Get the most recent file
        latest_file = max(json_files, key=os.path.getctime)
        print(f"📁 Loading data from existing file: {latest_file}")
        
        with open(latest_file, 'r', encoding='utf-8') as f:
            latest_data = json.load(f)
        
        if latest_data:
            # Generate RSS content
            latest_rss_content = generate_rss_content(latest_data)
            last_update_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"✅ Loaded {len(latest_data)} models from existing file")
            return True, len(latest_data)
        else:
            return False, "No data in existing file"
            
    except Exception as e:
        print(f"❌ Error loading from files: {e}")
        return False, str(e)

def generate_rss_content(data):
    """Generate RSS XML content from data"""
    from xml.etree.ElementTree import Element, SubElement, tostring
    from xml.dom import minidom
    
    rss = Element("rss", version="2.0")
    channel = SubElement(rss, "channel")
    
    # Add channel metadata
    SubElement(channel, "title").text = "IBM Watson Deprecated Foundation Models"
    SubElement(channel, "link").text = "https://www.ibm.com/docs/en/watsonx/saas?topic=model-foundation-lifecycle#foundation-model-deprecation"
    SubElement(channel, "description").text = "List of deprecated foundation models from IBM WatsonX documentation with deprecation dates and recommended alternatives."
    SubElement(channel, "language").text = "en-us"
    SubElement(channel, "lastBuildDate").text = datetime.now().strftime("%a, %d %b %Y %H:%M:%S GMT")
    
    # Add items for each model
    for model in data:
        item = SubElement(channel, "item")
        
        # Create title from model name
        title = model['foundation_model_name']
        SubElement(item, "title").text = title
        
        # Create description with all model details
        description = f"""
        <strong>Model:</strong> {model['foundation_model_name']}<br/>
        <strong>Availability Date:</strong> {model['availability_date']}<br/>
        <strong>Deprecation Date:</strong> {model['deprecation_date']}<br/>
        <strong>Withdrawal Date:</strong> {model['withdrawal_date']}<br/>
        <strong>Recommended Alternative:</strong> {model['recommended_alternative']}
        """
        SubElement(item, "description").text = description.strip()
        
        # Use withdrawal date as pubDate if available, otherwise use current date
        if model['withdrawal_date'] and model['withdrawal_date'] != '–':
            try:
                # Simple date parsing for common formats
                date_str = model['withdrawal_date']
                month_map = {
                    'January': '01', 'February': '02', 'March': '03', 'April': '04',
                    'May': '05', 'June': '06', 'July': '07', 'August': '08',
                    'September': '09', 'October': '10', 'November': '11', 'December': '12'
                }
                
                month = '01'
                for month_name, month_num in month_map.items():
                    if month_name in date_str:
                        month = month_num
                        break
                
                # Extract day and year
                parts = date_str.split()
                day = parts[0] if parts[0].isdigit() else '01'
                year = parts[-1] if parts[-1].isdigit() else '2025'
                
                # Format as RSS date
                pub_date = f"{day} {month} {year} 00:00:00 GMT"
                SubElement(item, "pubDate").text = pub_date
            except:
                SubElement(item, "pubDate").text = datetime.now().strftime("%a, %d %b %Y %H:%M:%S GMT")
        else:
            SubElement(item, "pubDate").text = datetime.now().strftime("%a, %d %b %Y %H:%M:%S GMT")
        
        # Add unique GUID
        SubElement(item, "guid").text = f"ibm-model-{hash(model['foundation_model_name'])}"
        
        # Add category
        SubElement(item, "category").text = "AI/ML Models"
    
    # Convert to pretty XML string
    rough_string = tostring(rss, 'unicode')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")

@app.route('/')
def index():
    """Main web interface"""
    models_count = len(latest_data) if latest_data else 0
    models_with_alternatives = len([m for m in latest_data if m.get('recommended_alternative') and m.get('recommended_alternative') != '–']) if latest_data else 0
    models_without_alternatives = models_count - models_with_alternatives
    
    # Get the current URL for the feed
    feed_url = request.url_root.rstrip('/') + '/feed.xml'
    
    return render_template_string(HTML_TEMPLATE, 
                                last_update_time=last_update_time,
                                models_count=models_count,
                                models_with_alternatives=models_with_alternatives,
                                models_without_alternatives=models_without_alternatives,
                                feed_url=feed_url,
                                latest_data=latest_data[:5] if latest_data else [])

@app.route('/feed.xml')
def rss_feed():
    """Serve the RSS feed"""
    if not latest_rss_content:
        return "No RSS feed available. Please update the feed first.", 404
    
    return latest_rss_content, 200, {'Content-Type': 'application/rss+xml; charset=utf-8'}

@app.route('/api/update', methods=['POST'])
def api_update():
    """API endpoint to update the feed"""
    try:
        success, result = update_feed_data()
        if success:
            return jsonify({
                'success': True,
                'models_count': result,
                'message': f'Feed updated successfully with {result} models'
            })
        else:
            return jsonify({
                'success': False,
                'error': result
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/status')
def api_status():
    """API endpoint to get current status"""
    return jsonify({
        'is_scraping': is_scraping,
        'last_update': last_update_time,
        'models_count': len(latest_data) if latest_data else 0
    })

@app.route('/api/data')
def api_data():
    """API endpoint to get raw data"""
    return jsonify({
        'last_update': last_update_time,
        'models_count': len(latest_data) if latest_data else 0,
        'data': latest_data
    })

if __name__ == '__main__':
    print("🚀 Starting IBM Watson RSS Feed Server...")
    print("📡 RSS Feed will be available at: http://localhost:5000/feed.xml")
    print("🌐 Web interface available at: http://localhost:5000")
    print("=" * 60)
    
    # Initial data load
    print("🔄 Loading initial data...")
    success, result = update_feed_data()
    if success:
        print(f"✅ Initial load successful! Found {result} models.")
    else:
        print(f"⚠️ Initial load failed: {result}")
        print("🔄 Trying to load from existing files...")
        success, result = load_data_from_files()
        if success:
            print(f"✅ Loaded from existing files! Found {result} models.")
        else:
            print(f"❌ Failed to load from files: {result}")
    
    # Start the Flask server
    app.run(host='0.0.0.0', port=5000, debug=False) 