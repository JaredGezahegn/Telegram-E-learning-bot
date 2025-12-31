#!/usr/bin/env python3
"""
Simple startup script for the Telegram English Bot.
This demonstrates the deployment-ready application structure.
"""

import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import and run the main application
from src.main import main

if __name__ == "__main__":
    main()