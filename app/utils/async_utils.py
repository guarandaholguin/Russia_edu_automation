"""
Async utilities for the Russia-Edu Status Checker application.
"""

import asyncio
import threading
import functools
import inspect
from typing import Any, Callable, Coroutine, Dict, List, Optional, TypeVar, Union, cast
from concurrent.futures import ThreadPoolExecutor, Future
import traceback

from app.utils.logger import get_logger
from app.utils.exceptions import AsyncOperationError

logger = get_logger()

# Type variables for better type hinting
T = TypeVar('T')
R = TypeVar('R')

class AsyncRunner:
    """Utility class to run async functions from synchronous context."""
    
    _loop = None
    _thread = None
    _running = False
    
    @classmethod
    def ensure_event_loop(cls) -> asyncio.AbstractEventLoop:
        """
        Ensure that an event loop is running in a background thread.
        
        Returns:
            asyncio.AbstractEventLoop: The event loop.
        """
        if cls._loop is not None and cls._running:
            return cls._loop
        
        # Create a new loop
        cls._loop = asyncio.new_event_loop()
        
        # Define the target function for the background thread
        def run_event_loop(loop: asyncio.AbstractEventLoop) -> None:
            """Run the event loop in a background thread."""
            asyncio.set_event_loop(loop)
            try:
                loop.run_forever()
            finally:
                pending_tasks = asyncio.all_tasks(loop)
                for task in pending_tasks:
                    task.cancel()
                
                loop.run_until_complete(asyncio.gather(*pending_tasks, return_exceptions=True))
                loop.run_until_complete(loop.shutdown_asyncgens())
                loop.close()
                cls._running = False
                logger.debug("Event loop stopped and closed")
        
        # Start the background thread
        cls._thread = threading.Thread(target=run_event_loop, args=(cls._loop,), daemon=True)
        cls._thread.start()
        cls._running = True
        
        logger.debug("Started event loop in background thread")
        return cls._loop
    
    @classmethod
    def run(cls, coro: Coroutine[Any, Any, T]) -> T:
        """
        Run a coroutine in the background event loop and return the result.
        
        Args:
            coro (Coroutine): The coroutine to run.
            
        Returns:
            Any: The result of the coroutine.
            
        Raises:
            AsyncOperationError: If there's an error running the coroutine.
        """
        loop = cls.ensure_event_loop()
        
        # Create a Future to get the result
        future = asyncio.run_coroutine_threadsafe(coro, loop)
        
        try:
            # Wait for the result with a timeout
            return future.result()
        except Exception as e:
            logger.error(f"Error in async operation: {e}")
            logger.debug(traceback.format_exc())
            raise AsyncOperationError(f"Error in async operation: {str(e)}")
    
    @classmethod
    def stop(cls) -> None:
        """Stop the background event loop."""
        if cls._loop is not None and cls._running:
            cls._loop.call_soon_threadsafe(cls._loop.stop)
            if cls._thread is not None and cls._thread.is_alive():
                cls._thread.join(timeout=5)
            cls._running = False
            logger.debug("Stopped background event loop")

def to_thread(func: Callable[..., T]) -> Callable[..., Coroutine[Any, Any, T]]:
    """
    Decorator to run a synchronous function in a thread pool.
    
    Args:
        func (Callable): The synchronous function to run in a thread.
        
    Returns:
        Callable: Async wrapper around the synchronous function.
    """
    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> T:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, lambda: func(*args, **kwargs)
        )
    
    return wrapper

def run_async(func: Callable[..., Coroutine[Any, Any, T]]) -> Callable[..., T]:
    """
    Decorator to run an async function from a synchronous context.
    
    Args:
        func (Callable): The async function to run.
        
    Returns:
        Callable: Synchronous wrapper around the async function.
    """
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> T:
        return AsyncRunner.run(func(*args, **kwargs))
    
    return wrapper

def run_async_in_thread(coro: Coroutine[Any, Any, T]) -> Future[T]:
    """
    Run a coroutine in the background thread and return a future.
    
    Args:
        coro (Coroutine): The coroutine to run.
        
    Returns:
        Future: Future representing the pending result.
    """
    loop = AsyncRunner.ensure_event_loop()
    return asyncio.run_coroutine_threadsafe(coro, loop)

class AsyncToSync:
    """Class decorator to convert all async methods to sync methods."""
    
    def __init__(self, cls):
        """
        Initialize the decorator.
        
        Args:
            cls: The class to modify.
        """
        self.cls = cls
        
        # Process all methods in the class
        for name, method in inspect.getmembers(cls, inspect.isfunction):
            if asyncio.iscoroutinefunction(method):
                # Replace the async method with a sync wrapper
                setattr(cls, name, run_async(method))
    
    def __call__(self, *args, **kwargs):
        """Create a new instance of the wrapped class."""
        return self.cls(*args, **kwargs)