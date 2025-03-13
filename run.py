#!/usr/bin/env python3
"""
Wrapper script to maintain backward compatibility with existing commands.
This simply calls the strteam module.
"""

import sys
import os

if __name__ == "__main__":
    # Add the current directory to the Python path
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    # Import and run the main function from strteam.__main__
    from strteam.__main__ import main
    main()