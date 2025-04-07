"""
Data validation utilities for the Russia-Edu Status Checker application.
"""

import re
import os
from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path

from app.utils.exceptions import ValidationError
from app.utils.logger import get_logger

logger = get_logger()

# Regular expressions for validation
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
REG_NUMBER_REGEX = re.compile(r"^[A-Z]{3}-\d+/\d+$")  # Example: ECU-10209/25
FILE_PATH_REGEX = re.compile(r'^[^<>:"/\\|?*]+$')  # Valid file name chars

def validate_email(email: str) -> Tuple[bool, Optional[str]]:
    """
    Validate email address format.
    
    Args:
        email (str): Email address to validate.
        
    Returns:
        Tuple[bool, Optional[str]]: (is_valid, error_message)
    """
    if not email:
        return False, "Email cannot be empty"
    
    if not EMAIL_REGEX.match(email):
        return False, "Invalid email format"
    
    return True, None

def validate_reg_number(reg_number: str) -> Tuple[bool, Optional[str]]:
    """
    Validate registration number format.
    
    Args:
        reg_number (str): Registration number to validate.
        
    Returns:
        Tuple[bool, Optional[str]]: (is_valid, error_message)
    """
    if not reg_number:
        return False, "Registration number cannot be empty"
    
    if not REG_NUMBER_REGEX.match(reg_number):
        return False, "Invalid registration number format (expected format: XXX-#####/##)"
    
    return True, None

def validate_excel_file(file_path: str) -> Tuple[bool, Optional[str]]:
    """
    Validate Excel file existence and format.
    
    Args:
        file_path (str): Path to Excel file.
        
    Returns:
        Tuple[bool, Optional[str]]: (is_valid, error_message)
    """
    if not file_path:
        return False, "File path cannot be empty"
    
    path = Path(file_path)
    
    if not path.exists():
        return False, f"File does not exist: {file_path}"
    
    if not path.is_file():
        return False, f"Not a file: {file_path}"
    
    valid_extensions = ['.xlsx', '.xls', '.xlsm', '.xlsb']
    if path.suffix.lower() not in valid_extensions:
        return False, f"Invalid file type. Expected Excel file with extensions: {', '.join(valid_extensions)}"
    
    # Check if file is readable
    try:
        with open(file_path, 'rb') as f:
            f.read(1)
    except Exception as e:
        return False, f"Cannot read file: {str(e)}"
    
    return True, None

def validate_output_path(directory: str, filename: str) -> Tuple[bool, Optional[str]]:
    """
    Validate output path for saving results.
    
    Args:
        directory (str): Directory path.
        filename (str): File name.
        
    Returns:
        Tuple[bool, Optional[str]]: (is_valid, error_message)
    """
    # Validate directory
    if not directory:
        return False, "Directory path cannot be empty"
    
    dir_path = Path(directory)
    
    if not dir_path.exists():
        try:
            dir_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            return False, f"Cannot create directory: {str(e)}"
    
    if not dir_path.is_dir():
        return False, f"Not a directory: {directory}"
    
    # Check if directory is writable
    try:
        test_file = dir_path / ".test_write_permission"
        test_file.touch()
        test_file.unlink()
    except Exception as e:
        return False, f"Directory is not writable: {str(e)}"
    
    # Validate filename
    if not filename:
        return False, "Filename cannot be empty"
    
    if not FILE_PATH_REGEX.match(filename):
        return False, "Filename contains invalid characters"
    
    # Check for valid extension
    file_path = dir_path / filename
    if file_path.suffix.lower() not in ['.xlsx', '.xls']:
        return False, "Invalid file extension. Expected .xlsx or .xls"
    
    # Check if file exists and is writable
    if file_path.exists():
        if not os.access(file_path, os.W_OK):
            return False, f"File exists and is not writable: {file_path}"
    
    return True, None

def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to ensure it's valid.
    
    Args:
        filename (str): Filename to sanitize.
        
    Returns:
        str: Sanitized filename.
    """
    # Replace invalid characters with underscore
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Ensure it has .xlsx extension
    if not sanitized.lower().endswith(('.xlsx', '.xls')):
        sanitized += '.xlsx'
    
    return sanitized