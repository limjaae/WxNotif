#!/usr/bin/env python3
"""
IBM Watson RSS Feed Server Startup Script
This script installs dependencies and starts the RSS server.
"""

import subprocess
import sys
import os

def install_dependencies():
    """Install required Python packages"""
    print("📦 Installing dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Dependencies installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error installing dependencies: {e}")
        return False

def start_server():
    """Start the RSS server"""
    print("🚀 Starting RSS server...")
    try:
        from rss_server import app
        print("✅ Server started successfully!")
        print("📡 RSS Feed URL: http://localhost:5000/feed.xml")
        print("🌐 Web Interface: http://localhost:5000")
        print("=" * 60)
        app.run(host='0.0.0.0', port=5000, debug=False)
    except ImportError as e:
        print(f"❌ Error importing server: {e}")
        return False
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        return False

def main():
    """Main function"""
    print("🤖 IBM Watson RSS Feed Server")
    print("=" * 40)
    
    # Check if we're in a virtual environment
    if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("⚠️  Warning: Not running in a virtual environment.")
        print("   Consider creating one: python3 -m venv venv && source venv/bin/activate")
    
    # Install dependencies
    if not install_dependencies():
        print("❌ Failed to install dependencies. Exiting.")
        return
    
    # Start server
    start_server()

if __name__ == "__main__":
    main() 