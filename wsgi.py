#!/usr/bin/env python3
"""
WSGI entry point for Railway deployment
"""
from rss_server import app
import os

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000))) 