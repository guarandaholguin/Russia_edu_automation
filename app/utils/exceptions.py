"""
Custom exceptions for the Russia-Edu Status Checker application.
"""

class BaseAppException(Exception):
    """Base exception for all application exceptions."""
    pass

# Scraper exceptions
class ScraperError(BaseAppException):
    """General scraper error."""
    pass

class BrowserError(ScraperError):
    """Error related to browser initialization or operation."""
    pass

class NavigationError(ScraperError):
    """Error during page navigation."""
    pass

class CaptchaError(ScraperError):
    """Error related to CAPTCHA solving."""
    pass

class DataExtractionError(ScraperError):
    """Error during data extraction."""
    pass

# Data handling exceptions
class DataError(BaseAppException):
    """Base class for data-related errors."""
    pass

class ExcelReadError(DataError):
    """Error reading Excel file."""
    pass

class ExcelWriteError(DataError):
    """Error writing Excel file."""
    pass

class InvalidDataError(DataError):
    """Error when data is invalid or in unexpected format."""
    pass

# UI exceptions
class UIError(BaseAppException):
    """Base class for UI-related errors."""
    pass

class ConfigError(BaseAppException):
    """Error related to configuration."""
    pass

class ValidationError(BaseAppException):
    """Error during data validation."""
    pass

class AsyncOperationError(BaseAppException):
    """Error during asynchronous operation."""
    pass

class NetworkError(BaseAppException):
    """Error related to network operations."""
    pass

# Map exception types to user-friendly messages
ERROR_MESSAGES = {
    BrowserError: "Error initializing browser. Please check that Chrome/Firefox is installed.",
    NavigationError: "Error navigating to the website. Please check your internet connection.",
    CaptchaError: "Error solving CAPTCHA. Please try again later.",
    DataExtractionError: "Error extracting student data from the website.",
    ExcelReadError: "Error reading Excel file. Please make sure the file is valid and not corrupted.",
    ExcelWriteError: "Error writing Excel file. Please make sure you have write permissions.",
    InvalidDataError: "Invalid data encountered. Please check the input data format.",
    ConfigError: "Configuration error. Please check application settings.",
    ValidationError: "Validation error. Please check your input data.",
    AsyncOperationError: "Error during asynchronous operation.",
    NetworkError: "Network error. Please check your internet connection.",
}

def get_user_friendly_message(exception: Exception) -> str:
    """
    Get a user-friendly error message for an exception.
    
    Args:
        exception (Exception): The exception to get a message for.
        
    Returns:
        str: User-friendly error message.
    """
    # Get exception class
    exception_class = exception.__class__
    
    # Find the first matching exception class in ERROR_MESSAGES
    for cls in exception_class.__mro__:
        if cls in ERROR_MESSAGES:
            # Add the specific error message if available
            base_message = ERROR_MESSAGES[cls]
            if str(exception):
                return f"{base_message} Details: {str(exception)}"
            return base_message
    
    # Default message for unhandled exceptions
    return f"An unexpected error occurred: {str(exception)}"