#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Main entry point for the Russia-Edu Scraper application.
This module initializes the application, sets up logging,
and launches the main UI window.
"""

import os
import sys
import logging
from pathlib import Path

# Add the parent directory to sys.path
current_dir = Path(__file__).resolve().parent
parent_dir = current_dir.parent
sys.path.append(str(parent_dir))

from app.utils.logger import setup_logger
from app.ui.main_window import MainApplication
from app.config import APP_NAME, APP_VERSION, DEBUG_MODE

def main():
    """Main entry point of the application."""
    # Create logs directory if it doesn't exist
    logs_dir = parent_dir / "logs"
    logs_dir.mkdir(exist_ok=True)
    
    # Setup logger
    log_file = logs_dir / f"{APP_NAME.lower().replace(' ', '_')}.log"
    logger = setup_logger(log_file, debug=DEBUG_MODE)
    
    logger.info(f"Starting {APP_NAME} v{APP_VERSION}")
    
    try:
        # Initialize and start the main application
        app = MainApplication()
        app.mainloop()
        logger.info(f"Shutting down {APP_NAME} v{APP_VERSION}")
    except Exception as e:
        logger.critical(f"Unhandled exception: {str(e)}", exc_info=True)
        # You might want to show an error dialog here
        raise

if __name__ == "__main__":
    main()