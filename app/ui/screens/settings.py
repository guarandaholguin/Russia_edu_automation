"""
Settings screen for the Russia-Edu Status Checker application.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
from typing import Dict, Any, Optional, Callable

import customtkinter as ctk

from app.utils.logger import get_logger
from app.config import DEFAULT_BROWSER, BROWSER_HEADLESS, REQUEST_DELAY, MAX_RETRY_ATTEMPTS, TWO_CAPTCHA_API_KEY

logger = get_logger()

class SettingsScreen(ctk.CTkToplevel):
    """Settings screen for configuring application parameters."""
    
    def __init__(self, master, settings: Dict[str, Any], on_save: Callable[[Dict[str, Any]], None]):
        """
        Initialize the settings screen.
        
        Args:
            master: Parent widget.
            settings (Dict[str, Any]): Current settings.
            on_save (Callable): Callback function called when settings are saved.
        """
        super().__init__(master)
        self.title("Settings")
        self.geometry("500x600")
        self.resizable(True, True)
        self.transient(master)
        self.grab_set()
        
        # Store parameters
        self.master = master
        self.settings = settings.copy()
        self.on_save = on_save
        
        # Variables
        self.browser_var = tk.StringVar(value=settings.get("browser_type", DEFAULT_BROWSER))
        self.headless_var = tk.BooleanVar(value=settings.get("headless", BROWSER_HEADLESS))
        self.delay_var = tk.DoubleVar(value=settings.get("request_delay", REQUEST_DELAY))
        self.retries_var = tk.IntVar(value=settings.get("max_retries", MAX_RETRY_ATTEMPTS))
        self.tesseract_path_var = tk.StringVar(value=settings.get("tesseract_path", ""))
        self.log_level_var = tk.StringVar(value=settings.get("log_level", "INFO"))
        
      
        # Create UI
        self._create_widgets()
        
        # Center window
        self._center_window()
    
    def _create_widgets(self):
        """Create widgets for the settings screen."""
        # Main frame
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Create notebook (tabbed interface)
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill="both", expand=True, padx=5, pady=5)
        
        # General settings tab
        general_tab = ctk.CTkFrame(notebook)
        notebook.add(general_tab, text="General")
        
        general_frame = ctk.CTkFrame(general_tab)
        general_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Browser settings
        browser_frame = ctk.CTkFrame(general_frame)
        browser_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(browser_frame, text="Browser Settings", font=("", 14, "bold")).pack(anchor="w", padx=5, pady=5)
        
        # Browser type
        browser_frame_inner = ctk.CTkFrame(browser_frame)
        browser_frame_inner.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(browser_frame_inner, text="Browser type:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        
        browser_options = ["chromium", "firefox", "webkit"]
        browser_dropdown = ctk.CTkOptionMenu(browser_frame_inner, variable=self.browser_var, values=browser_options)
        browser_dropdown.grid(row=0, column=1, sticky="w", padx=5, pady=5)
        
        # Headless mode
        ctk.CTkCheckBox(
            browser_frame_inner, text="Run in headless mode (no browser window)", 
            variable=self.headless_var
        ).grid(row=1, column=0, columnspan=2, sticky="w", padx=5, pady=5)
        
        # Request settings
        request_frame = ctk.CTkFrame(general_frame)
        request_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(request_frame, text="Request Settings", font=("", 14, "bold")).pack(anchor="w", padx=5, pady=5)
        
        request_frame_inner = ctk.CTkFrame(request_frame)
        request_frame_inner.pack(fill="x", padx=5, pady=5)
        
        # Request delay
        ctk.CTkLabel(request_frame_inner, text="Delay between requests (seconds):").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        delay_slider = ctk.CTkSlider(
            request_frame_inner, from_=0.5, to=5.0, number_of_steps=45, variable=self.delay_var
        )
        delay_slider.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        
        delay_label = ctk.CTkLabel(request_frame_inner, text=f"{self.delay_var.get():.1f}")
        delay_label.grid(row=0, column=2, padx=5, pady=5)

        
        # Update label when slider changes
        def update_delay_label(*args):
            delay_label.configure(text=f"{self.delay_var.get():.1f}")
        
        self.delay_var.trace_add("write", update_delay_label)
        
        # Max retries
        ctk.CTkLabel(request_frame_inner, text="Maximum retry attempts:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        
        retries_frame = ctk.CTkFrame(request_frame_inner)
        retries_frame.grid(row=1, column=1, sticky="ew", padx=5, pady=5)
        
        for i, value in enumerate([1, 2, 3, 5, 10]):
            ctk.CTkRadioButton(
                retries_frame, text=str(value), value=value, variable=self.retries_var
            ).pack(side="left", padx=5)
        
        # CAPTCHA settings tab
        captcha_tab = ctk.CTkFrame(notebook)
        notebook.add(captcha_tab, text="CAPTCHA")
        
        captcha_frame = ctk.CTkFrame(captcha_tab)
        captcha_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        ctk.CTkLabel(captcha_frame, text="Configuración de CAPTCHA", font=("", 14, "bold")).pack(anchor="w", padx=5, pady=5)
        
        # 2Captcha settings
        two_captcha_frame = ctk.CTkFrame(captcha_frame)
        two_captcha_frame.pack(fill="x", padx=5, pady=5)
        
        # 2Captcha API key
        self.use_2captcha_var = tk.BooleanVar(value=bool(self.settings.get("two_captcha_api_key", "")))
        self.two_captcha_api_key_var = tk.StringVar(value=self.settings.get("two_captcha_api_key", TWO_CAPTCHA_API_KEY))

        
        use_2captcha_checkbox = ctk.CTkCheckBox(
            two_captcha_frame, 
            text="Usar API de 2Captcha",
            variable=self.use_2captcha_var,
            command=self._toggle_2captcha_fields
        )
        use_2captcha_checkbox.pack(anchor="w", padx=5, pady=5)
        
        # API key input
        self.two_captcha_api_key_frame = ctk.CTkFrame(two_captcha_frame)
        self.two_captcha_api_key_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(self.two_captcha_api_key_frame, text="Clave API de 2Captcha:").pack(anchor="w", padx=5, pady=5)
        
        api_key_entry = ctk.CTkEntry(self.two_captcha_api_key_frame, textvariable=self.two_captcha_api_key_var, width=300)
        api_key_entry.pack(fill="x", padx=5, pady=5)
        
        # Manual CAPTCHA options
        manual_captcha_frame = ctk.CTkFrame(captcha_frame)
        manual_captcha_frame.pack(fill="x", padx=5, pady=10)
        
        # Enable manual input
        self.enable_manual_captcha_var = tk.BooleanVar(value=self.settings.get("enable_manual_captcha", True))
        ctk.CTkCheckBox(
            manual_captcha_frame, 
            text="Habilitar entrada manual de CAPTCHA cuando los métodos automáticos fallan", 
            variable=self.enable_manual_captcha_var
        ).pack(anchor="w", padx=5, pady=5)
        
        # Always use manual input
        self.always_manual_captcha_var = tk.BooleanVar(value=self.settings.get("always_manual_captcha", False))

        ctk.CTkCheckBox(
            manual_captcha_frame, 
            text="Siempre usar entrada manual de CAPTCHA (omitir métodos automáticos)", 
            variable=self.always_manual_captcha_var
        ).pack(anchor="w", padx=5, pady=5)
        
        # Help text
        ctk.CTkLabel(
            captcha_frame, 
            text="2Captcha es un servicio de pago que resuelve CAPTCHAs automáticamente. Necesitas tener una cuenta y crédito.",
            wraplength=400, 
            font=("", 10)
        ).pack(fill="x", padx=5, pady=5)
        
        # Initial state
        self._toggle_2captcha_fields()
        
        # OCR settings tab
        ocr_tab = ctk.CTkFrame(notebook)
        notebook.add(ocr_tab, text="OCR")
        
        ocr_frame = ctk.CTkFrame(ocr_tab)
        ocr_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        ctk.CTkLabel(ocr_frame, text="OCR Settings", font=("", 14, "bold")).pack(anchor="w", padx=5, pady=5)
        
        # Tesseract path
        tesseract_frame = ctk.CTkFrame(ocr_frame)
        tesseract_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(tesseract_frame, text="Tesseract OCR executable path:").pack(anchor="w", padx=5, pady=5)
        
        tesseract_entry_frame = ctk.CTkFrame(tesseract_frame)
        tesseract_entry_frame.pack(fill="x", padx=5, pady=5)
        
        tesseract_entry = ctk.CTkEntry(tesseract_entry_frame, textvariable=self.tesseract_path_var)
        tesseract_entry.pack(side="left", fill="x", expand=True, padx=5, pady=5)
        
        browse_button = ctk.CTkButton(
            tesseract_entry_frame, text="Browse", command=self._browse_tesseract_path, width=100
        )
        browse_button.pack(side="right", padx=5, pady=5)
        
        # Help text
        tesseract_help_text = (
            "If Tesseract OCR is installed in a non-standard location, provide the path to the executable. "
            "Leave empty to use the default installation path."
        )
        ctk.CTkLabel(
            tesseract_frame, text=tesseract_help_text, wraplength=400, font=("", 10)
        ).pack(fill="x", padx=5, pady=5)
        
        # Advanced settings tab
        advanced_tab = ctk.CTkFrame(notebook)
        notebook.add(advanced_tab, text="Advanced")
        
        advanced_frame = ctk.CTkFrame(advanced_tab)
        advanced_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        ctk.CTkLabel(advanced_frame, text="Advanced Settings", font=("", 14, "bold")).pack(anchor="w", padx=5, pady=5)
        
        # Logging level
        log_frame = ctk.CTkFrame(advanced_frame)
        log_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(log_frame, text="Logging level:").pack(anchor="w", padx=5, pady=5)
        
        log_level_frame = ctk.CTkFrame(log_frame)
        log_level_frame.pack(fill="x", padx=5, pady=5)
        
        log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        
        for level in log_levels:
            ctk.CTkRadioButton(
                log_level_frame, text=level, value=level, variable=self.log_level_var
            ).pack(side="left", padx=5)
        
        # Button frame
        button_frame = ctk.CTkFrame(self)
        button_frame.pack(fill="x", padx=10, pady=10)
        
        # Save button
        save_button = ctk.CTkButton(
            button_frame, text="Save", command=self._save_settings, fg_color="green", hover_color="darkgreen"
        )
        save_button.pack(side="left", padx=10, pady=5, expand=True)
        
        # Cancel button
        cancel_button = ctk.CTkButton(
            button_frame, text="Cancel", command=self.destroy
        )
        cancel_button.pack(side="right", padx=10, pady=5, expand=True)
    
    def _toggle_2captcha_fields(self):
        """Enable or disable 2Captcha fields based on checkbox state."""
        if self.use_2captcha_var.get():
            for widget in self.two_captcha_api_key_frame.winfo_children():
                if isinstance(widget, ctk.CTkEntry):
                    widget.configure(state="normal")
        else:
            for widget in self.two_captcha_api_key_frame.winfo_children():
                if isinstance(widget, ctk.CTkEntry):
                    widget.configure(state="disabled")
    
    def _browse_tesseract_path(self):
        """Open file dialog to select Tesseract OCR executable."""
        file_path = filedialog.askopenfilename(
            title="Select Tesseract OCR Executable",
            filetypes=[
                ("Executable Files", "*.exe") if os.name == "nt" else ("All Files", "*")
            ]
        )
        
        if file_path:
            self.tesseract_path_var.set(file_path)
    
    def _save_settings(self):
        """Save settings and close the dialog."""
        try:
            # Update settings
            self.settings["browser_type"] = self.browser_var.get()
            self.settings["headless"] = self.headless_var.get()
            self.settings["request_delay"] = self.delay_var.get()
            self.settings["max_retries"] = self.retries_var.get()
            self.settings["tesseract_path"] = self.tesseract_path_var.get()
            self.settings["log_level"] = self.log_level_var.get()
            self.settings["enable_manual_captcha"] = self.enable_manual_captcha_var.get()
            self.settings["always_manual_captcha"] = self.always_manual_captcha_var.get()
            self.settings["two_captcha_api_key"] = self.two_captcha_api_key_var.get() if self.use_2captcha_var.get() else ""

            # Call the save callback
            if self.on_save:
                self.on_save(self.settings)
            
            # Close the dialog
            self.destroy()
            
        except Exception as e:
            logger.error(f"Error saving settings: {e}")
            messagebox.showerror("Error", f"Failed to save settings: {str(e)}")
    
    def _center_window(self):
        """Center the window on the parent."""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = self.master.winfo_rootx() + (self.master.winfo_width() // 2) - (width // 2)
        y = self.master.winfo_rooty() + (self.master.winfo_height() // 2) - (height // 2)
        self.geometry(f"+{x}+{y}")