#!/usr/bin/env python3
"""Build script for BoothList ETL pipeline."""

import sys
import os
from pathlib import Path

# Add src directory to Python path
src_path = Path(__file__).parent / 'src'
sys.path.insert(0, str(src_path))

# Import and run the main ETL pipeline
from boothlist.main import main
Wf __name__ == '__main__':
    main()