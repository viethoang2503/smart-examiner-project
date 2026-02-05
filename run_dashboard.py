#!/usr/bin/env python3
"""
Run FocusGuard Teacher Dashboard
Usage: python run_dashboard.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gui.dashboard import main

if __name__ == "__main__":
    main()
