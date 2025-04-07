"""
Logger configuration for the application.
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
import datetime

# Define custom log formats
CONSOLE_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"
FILE_LOG_FORMAT = "%(asctime)s [%(levelname)s] [%(filename)s:%(lineno)d] %(message)s"

# Define colors for console output
COLORS = {
    'RESET': '\033[0m',
    'DEBUG': '\033[94m',    # Blue
    'INFO': '\033[92m',     # Green
    'WARNING': '\033[93m',  # Yellow
    'ERROR': '\033[91m',    # Red
    'CRITICAL': '\033[41m', # White text on red background
}

class ColoredFormatter(logging.Formatter):
    """Custom formatter to add colors to console logs."""
    
    def format(self, record):
        log_message = super().format(record)
        if record.levelname in COLORS:
            return f"{COLORS[record.levelname]}{log_message}{COLORS['RESET']}"
        return log_message

def setup_logger(log_file=None, debug=False):
    """
    Configure and return a logger instance.
    
    Args:
        log_file (str, optional): Path to log file.
        debug (bool, optional): Whether to enable debug logging. Defaults to False.
    
    Returns:
        logging.Logger: Configured logger instance.
    """
    # Create logger
    logger = logging.getLogger('russia_edu_scraper')
    logger.setLevel(logging.DEBUG if debug else logging.INFO)
    logger.handlers = []  # Clear existing handlers
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG if debug else logging.INFO)
    console_formatter = ColoredFormatter(CONSOLE_LOG_FORMAT)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # Create file handler if log_file is provided
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Use RotatingFileHandler to prevent log files from growing too large
        file_handler = RotatingFileHandler(
            log_path,
            maxBytes=10*1024*1024,  # 10 MB
            backupCount=5
        )
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(FILE_LOG_FORMAT)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    logger.debug(f"Logger initialized at {datetime.datetime.now().isoformat()}")
    if debug:
        logger.debug("Debug mode enabled")
    
    return logger

def get_logger():
    """Get the application logger instance."""
    return logging.getLogger('russia_edu_scraper')