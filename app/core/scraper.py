"""
Main scraper module for the Russia-Edu Status Checker application.
"""

import asyncio
import time
import random
from typing import List, Dict, Any, Optional, Callable, Tuple
from pathlib import Path
import traceback
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor

from playwright.async_api import async_playwright, Page, Browser, BrowserContext
# Modificamos la importación para evitar el error
try:
    from playwright._impl._api_types import Error as PlaywrightError
except ImportError:
    # Definir una clase Error genérica si no podemos importar la original
    class PlaywrightError(Exception):
        pass

from app.data.student import StudentInput, StudentResult
from app.core.captcha_solver import CaptchaSolver
from app.core.data_extractor import DataExtractor
from app.utils.logger import get_logger
from app.utils.exceptions import (
    ScraperError, BrowserError, NavigationError, 
    CaptchaError, DataExtractionError
)
from app.config import (
    BASE_URL, TRACKING_URL, CAPTCHA_TIMEOUT, PAGE_LOAD_TIMEOUT,
    BROWSER_HEADLESS, DEFAULT_BROWSER, BROWSER_ARGS, MAX_RETRY_ATTEMPTS,
    REQUEST_DELAY, TWO_CAPTCHA_API_KEY
)

logger = get_logger()

class RussiaEduScraper:
    """Main scraper class for the Russia-Edu website."""
    
    def __init__(self, 
                 headless: bool = BROWSER_HEADLESS,
                 browser_type: str = DEFAULT_BROWSER,
                 max_retries: int = MAX_RETRY_ATTEMPTS,
                 request_delay: float = REQUEST_DELAY,
                 enable_manual_captcha: bool = True,
                 always_manual_captcha: bool = False,
                 two_captcha_api_key: str = TWO_CAPTCHA_API_KEY):
        """
        Initialize the RussiaEduScraper.
        
        Args:
            headless (bool, optional): Whether to run browser in headless mode.
            browser_type (str, optional): Type of browser to use.
            max_retries (int, optional): Maximum number of retry attempts.
            request_delay (float, optional): Delay between requests in seconds.
            enable_manual_captcha (bool, optional): Whether to enable manual CAPTCHA input.
            always_manual_captcha (bool, optional): Whether to always use manual CAPTCHA input.
            two_captcha_api_key (str, optional): API key for 2Captcha service.
        """
        self.headless = headless
        self.browser_type = browser_type
        self.max_retries = max_retries
        self.request_delay = request_delay
        self.enable_manual_captcha = enable_manual_captcha
        self.always_manual_captcha = always_manual_captcha
        self.two_captcha_api_key = two_captcha_api_key
        
        self.captcha_solver = CaptchaSolver(
            enable_manual_input=enable_manual_captcha,
            always_manual=always_manual_captcha,
            two_captcha_api_key=two_captcha_api_key
        )
        self.data_extractor = DataExtractor()
        
        self.playwright = None
        self.browser = None
        self.context = None
        
        # Flags
        self.is_running = False
        self.should_stop = False
        
        # Callback for progress updates
        self.progress_callback = None
    
    def set_progress_callback(self, callback: Callable[[int, int, Optional[StudentResult]], None]) -> None:
        """
        Set a callback function for progress updates.
        
        Args:
            callback (Callable): Function to call with progress updates.
                               The function should accept (current, total, result).
        """
        self.progress_callback = callback
    
    async def initialize(self) -> None:
        """
        Initialize the browser instance.
        
        Raises:
            BrowserError: If browser initialization fails.
        """
        try:
            logger.info(f"Initializing browser ({self.browser_type}, headless={self.headless})")
            self.playwright = await async_playwright().start()
            
            # Get browser instance based on browser_type
            if self.browser_type == "chromium":
                browser_factory = self.playwright.chromium
            elif self.browser_type == "firefox":
                browser_factory = self.playwright.firefox
            elif self.browser_type == "webkit":
                browser_factory = self.playwright.webkit
            else:
                raise BrowserError(f"Unsupported browser type: {self.browser_type}")
            
            # Launch browser
            self.browser = await browser_factory.launch(
                headless=self.headless,
                args=BROWSER_ARGS
            )
            
            # Create a new browser context
            self.context = await self.browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            )
            
            logger.info("Browser initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing browser: {e}")
            await self.shutdown()
            raise BrowserError(f"Failed to initialize browser: {str(e)}")
    
    async def shutdown(self) -> None:
        """Safely close browser and playwright instances."""
        try:
            if self.context:
                await self.context.close()
                self.context = None
            
            if self.browser:
                await self.browser.close()
                self.browser = None
            
            if self.playwright:
                await self.playwright.stop()
                self.playwright = None
            
            logger.info("Browser and playwright instances closed")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
    
    def stop(self) -> None:
        """Signal the scraper to stop processing."""
        logger.info("Stop signal received")
        self.should_stop = True
    
    async def process_students(self, students: List[StudentInput]) -> List[StudentResult]:
        """
        Process a list of students and get their status information.
        
        Args:
            students (List[StudentInput]): List of student input data.
            
        Returns:
            List[StudentResult]: List of student results.
        """
        if not students:
            logger.warning("No students to process")
            return []
        
        try:
            # Initialize browser if not already initialized
            if not self.browser or not self.context:
                await self.initialize()
            
            self.is_running = True
            self.should_stop = False
            results = []
            total_students = len(students)
            
            logger.info(f"Starting to process {total_students} students")
            
            # Process each student
            for idx, student in enumerate(students):
                if self.should_stop:
                    logger.info("Stopping student processing due to stop signal")
                    break
                
                current = idx + 1
                logger.info(f"Processing student {current}/{total_students}: {student.reg_number}")
                
                # Process student with retries
                result = await self._process_student_with_retry(student)
                results.append(result)
                
                # Call progress callback if set
                if self.progress_callback:
                    try:
                        self.progress_callback(current, total_students, result)
                    except Exception as e:
                        logger.error(f"Error in progress callback: {e}")
                
                # Delay between requests to avoid rate limiting
                if current < total_students and not self.should_stop:
                    delay = self.request_delay + random.uniform(0, 1)
                    logger.debug(f"Waiting {delay:.2f} seconds before next request")
                    await asyncio.sleep(delay)
            
            logger.info(f"Finished processing {len(results)}/{total_students} students")
            return results
        
        except Exception as e:
            logger.error(f"Error processing students: {e}")
            raise ScraperError(f"Error processing students: {str(e)}")
        finally:
            self.is_running = False
    
    async def _process_student_with_retry(self, student: StudentInput) -> StudentResult:
        """
        Process a single student with retry logic.
        
        Args:
            student (StudentInput): Student input data.
            
        Returns:
            StudentResult: Student result.
        """
        result = StudentResult.from_student_input(student)
        
        for attempt in range(1, self.max_retries + 1):
            try:
                # Create a new page for each attempt to avoid state issues
                page = await self.context.new_page()
                page.set_default_timeout(PAGE_LOAD_TIMEOUT * 1000)  # Convert to ms
                
                try:
                    logger.info(f"Attempt {attempt}/{self.max_retries} for student {student.reg_number}")
                    
                    # Process the student
                    result = await self._process_single_student(page, student)
                    
                    # If successful, break the retry loop
                    if result.processed:
                        break
                    
                finally:
                    # Always close the page after use
                    await page.close()
                
            except (NavigationError, CaptchaError, DataExtractionError) as e:
                # For specific errors, we might want to retry
                logger.warning(f"Error on attempt {attempt}: {e}")
                result.error = f"Attempt {attempt}: {str(e)}"
                
                # If this was the last attempt, mark the error
                if attempt == self.max_retries:
                    logger.error(f"Failed all {self.max_retries} attempts for student {student.reg_number}")
                
                # Delay before retry
                if attempt < self.max_retries:
                    retry_delay = self.request_delay * (1.5 ** attempt)  # Exponential backoff
                    logger.debug(f"Waiting {retry_delay:.2f} seconds before retry")
                    await asyncio.sleep(retry_delay)
                
            except Exception as e:
                # For unexpected errors, log and break the retry loop
                logger.error(f"Unexpected error: {e}")
                logger.debug(traceback.format_exc())
                result.error = f"Unexpected error: {str(e)}"
                break
        
        return result
    
    async def _process_single_student(self, page: Page, student: StudentInput) -> StudentResult:
        """
        Process a single student.
        
        Args:
            page (Page): Playwright page object.
            student (StudentInput): Student input data.
            
        Returns:
            StudentResult: Student result.
            
        Raises:
            NavigationError: If navigation to the tracking page fails.
            CaptchaError: If CAPTCHA solving fails.
            DataExtractionError: If data extraction fails.
        """
        result = StudentResult.from_student_input(student)
        
        try:
            # Navigate to the tracking page
            logger.debug(f"Navigating to {TRACKING_URL}")
            await page.goto(TRACKING_URL)
            
            # Fill in registration number
            await page.fill('#registrationNumber', student.reg_number)
            
            # Fill in email
            await page.fill('#email', student.email)
            
            # Check if CAPTCHA is present
            captcha_element = await page.query_selector('#captcha_pic')
            if captcha_element:
                logger.debug("CAPTCHA found, attempting to solve")
                
                # Solve CAPTCHA
                captcha_solution = await self.captcha_solver.solve_captcha(page)
                
                # Fill in CAPTCHA solution
                await page.fill('#adcopy_response', captcha_solution)
            
            # Submit the form
            logger.debug("Submitting tracking form")
            await page.click('button[type="submit"]')
            
            # Wait for navigation
            await page.wait_for_load_state('networkidle')
            
            # Check if we're still on the form page (form errors)
            if '/tracking/' not in page.url:
                form_error = await page.query_selector('.alert-error, .error')
                if form_error:
                    error_text = await form_error.inner_text()
                    raise NavigationError(f"Form submission error: {error_text}")
                else:
                    raise NavigationError("Failed to navigate to tracking result page")
            
            # Extract student data from the page
            logger.debug("Extracting student data from the page")
            result = await self.data_extractor.extract_student_data(page, student)
            
            # Mark as processed
            result.processed = True
            
            return result
            
        except Exception as e:
            # Re-raise specific errors for retry logic
            if isinstance(e, (NavigationError, CaptchaError, DataExtractionError)):
                raise
            
            # Log and wrap other exceptions
            logger.error(f"Error processing student {student.reg_number}: {e}")
            result.error = str(e)
            result.processed = False
            return result