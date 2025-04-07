"""
Theme configuration for the Russia-Edu Status Checker application.
"""

import customtkinter as ctk
from tkinter import ttk
import tkinter as tk

def apply_theme():
    """Apply the application theme."""
    # Configure CustomTkinter theme
    ctk.set_default_color_theme("blue")
    
    # Configure ttk theme
    style = ttk.Style()
    
    # Use clam as base theme
    style.theme_use("clam")
    
    # Configure Treeview
    style.configure(
        "Treeview",
        background="#ffffff",
        foreground="#333333",
        rowheight=25,
        fieldbackground="#ffffff",
        borderwidth=0,
        relief="flat"
    )
    
    # Configure Treeview headings
    style.configure(
        "Treeview.Heading",
        background="#f0f0f0",
        foreground="#333333",
        relief="flat",
        borderwidth=1
    )
    
    # Configure Treeview rows
    style.map(
        "Treeview",
        background=[("selected", "#4a6984")],
        foreground=[("selected", "#ffffff")]
    )
    
    # Configure scrollbars
    style.configure(
        "TScrollbar",
        troughcolor="#f0f0f0",
        background="#999999",
        arrowcolor="#666666",
        borderwidth=0,
        relief="flat"
    )
    
    return style

def get_theme_settings():
    """
    Get theme settings dictionary.
    
    Returns:
        dict: Theme settings.
    """
    return {
        # Main colors
        "primary": "#1f538d",
        "secondary": "#4a6984",
        "accent": "#3a7ebf",
        "success": "#28a745",
        "warning": "#ffc107",
        "error": "#dc3545",
        "info": "#17a2b8",
        
        # Background colors
        "bg_primary": "#ffffff",
        "bg_secondary": "#f8f9fa",
        "bg_tertiary": "#f0f0f0",
        
        # Text colors
        "text_primary": "#333333",
        "text_secondary": "#6c757d",
        "text_light": "#ffffff",
        
        # Border colors
        "border_light": "#dee2e6",
        "border_dark": "#ced4da",
        
        # Component specific colors
        "button_bg": "#1f538d",
        "button_hover": "#3a7ebf",
        "button_pressed": "#164170",
        
        "input_bg": "#ffffff",
        "input_border": "#ced4da",
        "input_focus": "#80bdff",
        
        # Status colors
        "status_success": "#d4edda",
        "status_warning": "#fff3cd",
        "status_error": "#f8d7da",
        "status_info": "#d1ecf1",
        
        # Table row colors
        "row_even": "#ffffff",
        "row_odd": "#f8f9fa",
        "row_selected": "#4a6984",
        "row_hover": "#e9ecef",
        
        # Other settings
        "border_radius": 6,
        "shadow": "0 4px 6px rgba(0, 0, 0, 0.1)",
    }