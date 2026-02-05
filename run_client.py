#!/usr/bin/env python3
"""
Run FocusGuard Client
Usage: python run_client.py [--student-id ID] [--server HOST:PORT]
"""

import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from client.main import main

if __name__ == "__main__":
    main()
