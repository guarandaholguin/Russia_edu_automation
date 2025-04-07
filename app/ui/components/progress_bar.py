"""
Progress bar component for tracking processing progress.
"""

import tkinter as tk
from typing import Optional

import customtkinter as ctk

class ProgressFrame(ctk.CTkFrame):
    """Frame containing a progress bar and status labels."""
    
    def __init__(self, master, **kwargs):
        """
        Initialize the ProgressFrame.
        
        Args:
            master: Parent widget.
            **kwargs: Additional arguments for the frame.
        """
        super().__init__(master, **kwargs)
        
        # Progress variables
        self.progress_value = tk.DoubleVar(value=0)
        self.progress_max = tk.IntVar(value=100)
        self.progress_text = tk.StringVar(value="0 / 0")
        self.progress_percent = tk.StringVar(value="0%")
        
        # Create widgets
        self._create_widgets()
        
        # Configure grid
        self._configure_grid()
    
    def _create_widgets(self):
        """Create progress bar widgets."""
        # Progress label
        self.progress_label = ctk.CTkLabel(self, text="Progress:")
        self.progress_label.grid(row=0, column=0, sticky="w", padx=5, pady=5)
        
        # Progress counter
        self.counter_label = ctk.CTkLabel(self, textvariable=self.progress_text)
        self.counter_label.grid(row=0, column=1, sticky="w", padx=5, pady=5)
        
        # Progress percentage
        self.percent_label = ctk.CTkLabel(self, textvariable=self.progress_percent)
        self.percent_label.grid(row=0, column=2, sticky="e", padx=5, pady=5)
        
        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(self, variable=self.progress_value)
        self.progress_bar.grid(row=1, column=0, columnspan=3, sticky="ew", padx=5, pady=5)
        
        # Set initial state
        self.progress_bar.set(0)
    
    def _configure_grid(self):
        """Configure grid layout."""
        self.grid_columnconfigure(1, weight=1)
    
    def set_max(self, max_value: int):
        """
        Set the maximum value for the progress bar.
        
        Args:
            max_value (int): Maximum value.
        """
        if max_value <= 0:
            max_value = 1
        
        self.progress_max.set(max_value)
        self.progress_text.set(f"0 / {max_value}")
        self.progress_percent.set("0%")
        self.progress_bar.set(0)
    
    def update_progress(self, current: int, total: Optional[int] = None):
        """
        Update progress bar.
        
        Args:
            current (int): Current progress value.
            total (int, optional): Total items. If None, uses the previously set max value.
        """
        # Update max if total is provided
        if total is not None:
            self.set_max(total)
        
        # Get max value
        max_value = self.progress_max.get()
        
        # Calculate progress
        progress = min(current, max_value) / max_value
        
        # Update variables
        self.progress_value.set(progress)
        self.progress_text.set(f"{current} / {max_value}")
        self.progress_percent.set(f"{int(progress * 100)}%")
        
        # Update progress bar
        self.progress_bar.set(progress)
        
        # Update UI
        self.update_idletasks()
    
    def reset(self):
        """Reset progress bar to zero."""
        self.progress_value.set(0)
        self.progress_text.set("0 / 0")
        self.progress_percent.set("0%")
        self.progress_bar.set(0)
        self.update_idletasks()