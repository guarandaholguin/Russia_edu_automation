"""
Main window of the Russia-Edu Status Checker application.
"""

import os
import time
import asyncio
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from typing import List, Dict, Any, Optional, Callable, Tuple
from pathlib import Path
import traceback
from datetime import datetime

import customtkinter as ctk
from PIL import Image, ImageTk

from app.core.scraper import RussiaEduScraper
from app.data.student import StudentInput, StudentResult
from app.data.excel_reader import ExcelReader
from app.data.excel_writer import ExcelWriter
from app.utils.logger import get_logger
from app.utils.exceptions import (
    BaseAppException, ScraperError, ExcelReadError, ExcelWriteError,
    get_user_friendly_message
)
from app.utils.async_utils import AsyncRunner, run_async
from app.utils.validators import (
    validate_excel_file, validate_output_path, sanitize_filename
)
from app.config import (
    APP_NAME, APP_VERSION, THEME_MODE, DEFAULT_WINDOW_SIZE,
    DEFAULT_DOWNLOAD_PATH, DEFAULT_EXCEL_FILENAME, ROOT_DIR, TWO_CAPTCHA_API_KEY
)
from app.ui.components.student_table import StudentTable
from app.ui.components.progress_bar import ProgressFrame
from app.ui.styles.theme import apply_theme
from app.ui.screens.settings import SettingsScreen
from app.ui.screens.results import ResultsScreen

logger = get_logger()

class MainApplication(ctk.CTk):
    """Main application window for Russia-Edu Status Checker."""
    
    def __init__(self):
        super().__init__()
        
        # Configurar ventana
        self.title(f"{APP_NAME} v{APP_VERSION}")
        self.geometry(f"{DEFAULT_WINDOW_SIZE[0]}x{DEFAULT_WINDOW_SIZE[1]}")
        self.minsize(800, 600)
        
        # Aplicar tema
        ctk.set_appearance_mode(THEME_MODE)
        apply_theme()
        
        # Inicializar variables
        self.input_file_path = tk.StringVar()
        self.output_directory = tk.StringVar(value=str(DEFAULT_DOWNLOAD_PATH))
        self.output_filename = tk.StringVar(value=DEFAULT_EXCEL_FILENAME)
        self.headless_mode = tk.BooleanVar(value=True)
        self.status_text = tk.StringVar(value="Ready")
        self.is_running = False
        
        # Inicializar configuraciones
        self.settings = {
            "headless": True,
            "browser_type": "chromium",
            "request_delay": 1.5,
            "max_retries": 3,
            "tesseract_path": "",
            "log_level": "INFO",
            "enable_manual_captcha": True,
            "always_manual_captcha": False,
            "two_captcha_api_key": TWO_CAPTCHA_API_KEY
        }
        
        # Inicializar datos
        self.students = []
        self.results = []
        
        # Inicializar scraper
        self.scraper = RussiaEduScraper()
        
        # Crear elementos de la UI
        self._create_widgets()
        self._create_menu()
        
        # Configurar grid
        self._configure_grid()
        
        # Vincular eventos
        self._bind_events()
        
        # Centrar ventana
        self._center_window()
        
        # Iniciar AsyncRunner
        AsyncRunner.ensure_event_loop()
        
        logger.info("Application initialized")
    
    def _create_widgets(self):
        """Create UI widgets."""
        # Create frames
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        # Input section
        self.input_frame = ctk.CTkFrame(self.main_frame)
        self.input_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        
        # Input file
        ctk.CTkLabel(self.input_frame, text="Input Excel File:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.input_file_entry = ctk.CTkEntry(self.input_frame, textvariable=self.input_file_path, width=400)
        self.input_file_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        
        browse_input_btn = ctk.CTkButton(
            self.input_frame, text="Browse", command=self._browse_input_file, width=100
        )
        browse_input_btn.grid(row=0, column=2, padx=5, pady=5)
        
        # Output directory
        ctk.CTkLabel(self.input_frame, text="Output Directory:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        output_dir_entry = ctk.CTkEntry(self.input_frame, textvariable=self.output_directory, width=400)
        output_dir_entry.grid(row=1, column=1, sticky="ew", padx=5, pady=5)
        
        browse_output_btn = ctk.CTkButton(
            self.input_frame, text="Browse", command=self._browse_output_directory, width=100
        )
        browse_output_btn.grid(row=1, column=2, padx=5, pady=5)
        
        # Output filename
        ctk.CTkLabel(self.input_frame, text="Output Filename:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        output_file_entry = ctk.CTkEntry(self.input_frame, textvariable=self.output_filename, width=400)
        output_file_entry.grid(row=2, column=1, sticky="ew", padx=5, pady=5)
        
        # Headless mode
        headless_checkbox = ctk.CTkCheckBox(
            self.input_frame, text="Run in headless mode (no browser window)",
            variable=self.headless_mode
        )
        headless_checkbox.grid(row=3, column=0, columnspan=3, sticky="w", padx=5, pady=5)
        
        # Table for preview/results
        self.table_frame = ctk.CTkFrame(self.main_frame)
        self.table_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        
        self.table = StudentTable(self.table_frame)
        self.table.pack(fill=tk.BOTH, expand=True)
        
        # Progress bar and status
        self.progress_frame = ProgressFrame(self.main_frame)
        self.progress_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=10)
        
        # Status bar
        self.status_bar = ctk.CTkLabel(self, textvariable=self.status_text, anchor="w")
        self.status_bar.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 5))
        
        # Button frame
        self.button_frame = ctk.CTkFrame(self.main_frame)
        self.button_frame.grid(row=3, column=0, sticky="ew", padx=10, pady=10)

        
        self.preview_btn = ctk.CTkButton(
            self.button_frame, text="Preview Excel", command=self._preview_excel
        )
        self.preview_btn.grid(row=0, column=0, padx=5, pady=5)
        
        self.start_btn = ctk.CTkButton(
            self.button_frame, text="Start Processing", command=self._start_processing
        )
        self.start_btn.grid(row=0, column=1, padx=5, pady=5)
        
        self.stop_btn = ctk.CTkButton(
            self.button_frame, text="Stop", command=self._stop_processing, state="disabled",
            fg_color="darkred", hover_color="red"
        )
        self.stop_btn.grid(row=0, column=2, padx=5, pady=5)
        
        self.export_btn = ctk.CTkButton(
            self.button_frame, text="Export Results", command=self._export_results, state="disabled"
        )
        self.export_btn.grid(row=0, column=3, padx=5, pady=5)
    
    def _create_menu(self):
        """Create application menu."""
        # Create menu
        self.menu = tk.Menu(self)
        self.config(menu=self.menu)
        
        # File menu
        file_menu = tk.Menu(self.menu, tearoff=0)
        self.menu.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Open Excel File", command=self._browse_input_file)
        file_menu.add_command(label="Change Output Directory", command=self._browse_output_directory)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.quit)
        
        # Process menu
        process_menu = tk.Menu(self.menu, tearoff=0)
        self.menu.add_cascade(label="Process", menu=process_menu)
        process_menu.add_command(label="Start Processing", command=self._start_processing)
        process_menu.add_command(label="Stop Processing", command=self._stop_processing)
        process_menu.add_separator()
        process_menu.add_command(label="Export Results", command=self._export_results)
        
        # Settings menu
        settings_menu = tk.Menu(self.menu, tearoff=0)
        self.menu.add_cascade(label="Settings", menu=settings_menu)
        settings_menu.add_command(label="Application Settings", command=self._show_settings)
        
        # Help menu
        help_menu = tk.Menu(self.menu, tearoff=0)
        self.menu.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self._show_about)
    
    def _configure_grid(self):
        """Configure grid layout."""
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        self.main_frame.grid_rowconfigure(1, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)
        
        self.input_frame.grid_columnconfigure(1, weight=1)
        
        self.button_frame.grid_columnconfigure(0, weight=1)
        self.button_frame.grid_columnconfigure(1, weight=1)
        self.button_frame.grid_columnconfigure(2, weight=1)
        self.button_frame.grid_columnconfigure(3, weight=1)
    
    def _bind_events(self):
        """Bind widget events."""
        self.protocol("WM_DELETE_WINDOW", self._on_close)
    
    def _center_window(self):
        """Center the window on the screen."""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"+{x}+{y}")
    
    def _browse_input_file(self):
        """Open file dialog to select input Excel file."""
        file_path = filedialog.askopenfilename(
            title="Select Excel File",
            filetypes=[("Excel Files", "*.xlsx *.xls *.xlsm *.xlsb"), ("All Files", "*.*")]
        )
        
        if file_path:
            self.input_file_path.set(file_path)
            self._preview_excel()
    
    def _browse_output_directory(self):
        """Open directory dialog to select output directory."""
        directory = filedialog.askdirectory(
            title="Select Output Directory",
            initialdir=self.output_directory.get()
        )
        
        if directory:
            self.output_directory.set(directory)
    
    def _preview_excel(self):
        """Preview the Excel file content."""
        file_path = self.input_file_path.get()
        
        # Validate file
        is_valid, error_msg = validate_excel_file(file_path)
        if not is_valid:
            messagebox.showerror("Invalid File", error_msg)
            return
        
        try:
            # Read Excel file
            excel_reader = ExcelReader(file_path)
            sheet_names = excel_reader.get_sheet_names()
            
            # If multiple sheets, ask user to select one
            selected_sheet = None
            if len(sheet_names) > 1:
                selected_sheet = self._select_sheet_dialog(sheet_names)
                if not selected_sheet:  # User cancelled
                    return
            
            # Get preview data
            columns, data = excel_reader.get_preview_data(selected_sheet)
            
            # Update table with preview data
            self.table.set_columns(columns)
            self.table.set_data(data)
            
            # Load students
            self.students = excel_reader.read_students(selected_sheet)
            
            # Update status
            self.status_text.set(f"Loaded {len(self.students)} students from {os.path.basename(file_path)}")
            
            # Enable/disable buttons
            self._update_button_states()
            
        except ExcelReadError as e:
            messagebox.showerror("Excel Read Error", str(e))
        except Exception as e:
            logger.error(f"Error previewing Excel: {e}")
            logger.debug(traceback.format_exc())
            messagebox.showerror("Error", f"Failed to preview Excel: {str(e)}")
    
    def _select_sheet_dialog(self, sheet_names: List[str]) -> Optional[str]:
        """
        Show dialog to select a sheet from the Excel file.
        
        Args:
            sheet_names (List[str]): List of sheet names.
            
        Returns:
            Optional[str]: Selected sheet name or None if cancelled.
        """
        dialog = ctk.CTkToplevel(self)
        dialog.title("Select Sheet")
        dialog.geometry("300x200")
        dialog.transient(self)
        dialog.grab_set()
        
        # Center the dialog
        dialog.update_idletasks()
        width = dialog.winfo_width()
        height = dialog.winfo_height()
        x = self.winfo_x() + (self.winfo_width() // 2) - (width // 2)
        y = self.winfo_y() + (self.winfo_height() // 2) - (height // 2)
        dialog.geometry(f"+{x}+{y}")
        
        # Dialog content
        ctk.CTkLabel(dialog, text="Select a sheet from the Excel file:").pack(pady=10)
        
        # Sheet selection
        selected_sheet = tk.StringVar(value=sheet_names[0])
        for sheet_name in sheet_names:
            ctk.CTkRadioButton(
                dialog, text=sheet_name, variable=selected_sheet, value=sheet_name
            ).pack(anchor="w", padx=20, pady=5)
        
        # Buttons
        result = [None]  # Use a list to store the result
        
        def on_ok():
            result[0] = selected_sheet.get()
            dialog.destroy()
        
        def on_cancel():
            dialog.destroy()
        
        button_frame = ctk.CTkFrame(dialog)
        button_frame.pack(fill="x", pady=10)
        
        ctk.CTkButton(button_frame, text="OK", command=on_ok).pack(side="left", padx=10, expand=True)
        ctk.CTkButton(button_frame, text="Cancel", command=on_cancel).pack(side="right", padx=10, expand=True)
        
        # Wait for the dialog to close
        self.wait_window(dialog)
        
        return result[0]
    
    def _show_settings(self):
        """Show settings dialog."""
        settings_screen = SettingsScreen(self, self.settings, self._on_settings_save)
        settings_screen.grab_set()  # Make it modal
        self.wait_window(settings_screen)
    
    def _on_settings_save(self, settings: Dict[str, Any]):
        """
        Handle settings save.
        
        Args:
            settings (Dict[str, Any]): New settings.
        """
        self.settings = settings
        
        # Apply immediate settings
        self.headless_mode.set(settings.get("headless", True))
        
        # Log settings change
        logger.info("Settings updated")
    
    async def _process_students_async(self):
        """Process students asynchronously."""
        try:
            # Inicializar scraper con configuraciones actuales
            self.scraper = RussiaEduScraper(
                headless=self.headless_mode.get(),
                browser_type=self.settings.get("browser_type", "chromium"),
                max_retries=self.settings.get("max_retries", 3),
                request_delay=self.settings.get("request_delay", 1.5),
                enable_manual_captcha=self.settings.get("enable_manual_captcha", True),
                always_manual_captcha=self.settings.get("always_manual_captcha", False),
                two_captcha_api_key=self.settings.get("two_captcha_api_key", TWO_CAPTCHA_API_KEY)
            )
            self.scraper.set_progress_callback(self._update_progress)
            
            # Inicializar scraper
            await self.scraper.initialize()
            
            # Procesar estudiantes
            self.results = await self.scraper.process_students(self.students)
            
            # Actualizar tabla con resultados
            self._display_results()
            
            # Exportar resultados
            await self._export_results_async()
            
            # Actualizar estado
            self.status_text.set(f"Processing completed: {len(self.results)} students processed")
            
        except Exception as e:
            logger.error(f"Error processing students: {e}")
            logger.debug(traceback.format_exc())
            self.status_text.set(f"Error: {str(e)}")
            
            # Mostrar mensaje de error
            error_msg = get_user_friendly_message(e)
            messagebox.showerror("Processing Error", error_msg)
            
        finally:
            # Cerrar scraper
            await self.scraper.shutdown()
            
            # Reiniciar UI
            self.is_running = False
            self._update_button_states()
            self.progress_frame.reset()
    
    def _start_processing(self):
        """Start processing students."""
        if not self.students:
            messagebox.showwarning("No Data", "Please load an Excel file with student data first.")
            return
        
        if self.is_running:
            messagebox.showinfo("Already Running", "Processing is already in progress.")
            return
        
        # Validate output path
        output_dir = self.output_directory.get()
        output_filename = self.output_filename.get()
        
        is_valid, error_msg = validate_output_path(output_dir, output_filename)
        if not is_valid:
            messagebox.showerror("Invalid Output Path", error_msg)
            return
        
        # Update UI
        self.is_running = True
        self._update_button_states()
        self.progress_frame.reset()
        self.progress_frame.set_max(len(self.students))
        self.status_text.set("Processing started...")
        
        # Start processing in background
        from app.utils.async_utils import run_async_in_thread
        processing_task = run_async_in_thread(self._process_students_async())
    
    def _stop_processing(self):
        """Stop processing students."""
        if not self.is_running:
            return
        
        if messagebox.askyesno("Confirm Stop", "Are you sure you want to stop processing?"):
            self.status_text.set("Stopping... Please wait.")
            self.scraper.stop()
    
    def _update_progress(self, current: int, total: int, result: Optional[StudentResult]):
        """
        Update progress bar and table.
        
        Args:
            current (int): Current progress.
            total (int): Total items.
            result (Optional[StudentResult]): Result of the current item.
        """
        # Update progress bar
        self.progress_frame.update_progress(current, total)
        
        # Update status text
        self.status_text.set(f"Processing {current}/{total} students...")
        
        # Update table if result is available
        if result and result.processed:
            self._add_result_to_table(result)
        
        # Progress callback if set
        if hasattr(self, 'progress_callback') and self.progress_callback:
            try:
                self.progress_callback(current, total, result)
            except Exception as callback_error:
                logger.error(f"Error in progress callback: {callback_error}")
    
    def _add_result_to_table(self, result: StudentResult):
        """
        Add a result to the table.
        
        Args:
            result (StudentResult): Student result to add.
        """
        # Convert result to row
        row = [
            result.reg_number,
            result.email,
            result.status or "N/A",
            result.full_name_cyrillic or "N/A",
            result.education_program or "N/A",
            result.error or ""
        ]
        
        # Add row to table
        self.table.add_row(row)
    
    def _display_results(self):
        """Display processing results in the table."""
        if not self.results:
            return
        
        # Define columns
        columns = [
            "Reg Number", "Email", "Status", "Name", "Program", "Error"
        ]
        
        # Prepare data
        data = []
        for result in self.results:
            row = [
                result.reg_number,
                result.email,
                result.status or "N/A",
                result.full_name_cyrillic or "N/A",
                result.education_program or "N/A",
                result.error or ""
            ]
            data.append(row)
        
        # Update table
        self.table.set_columns(columns)
        self.table.set_data(data)
        
        # Show results screen
        self._show_results()
    
    def _show_results(self):
        """Show results screen."""
        if not self.results:
            return
        
        try:
            output_dir = self.output_directory.get()
            output_filename = self.output_filename.get()
            output_path = os.path.join(output_dir, sanitize_filename(output_filename))
            
            results_screen = ResultsScreen(self, self.results, export_path=output_path)
            results_screen.grab_set()  # Make it modal
        except Exception as e:
            logger.error(f"Error showing results screen: {e}")
            logger.debug(traceback.format_exc())
    
    async def _export_results_async(self) -> bool:
        """
        Export results to Excel file asynchronously.
        
        Returns:
            bool: True if export was successful, False otherwise.
        """
        if not self.results:
            return False
        
        try:
            output_dir = self.output_directory.get()
            output_filename = self.output_filename.get()
            
            # Sanitize filename
            output_filename = sanitize_filename(output_filename)
            
            # Create full path
            output_path = os.path.join(output_dir, output_filename)
            
            # Write results to Excel
            excel_writer = ExcelWriter(output_path)
            output_file = excel_writer.write_results(self.results)
            
            # Update status
            self.status_text.set(f"Results exported to {output_file}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error exporting results: {e}")
            logger.debug(traceback.format_exc())
            self.status_text.set(f"Export error: {str(e)}")
            
            return False
    
    def _export_results(self):
        """Export results to Excel file."""
        if not self.results:
            messagebox.showwarning("No Results", "No results to export.")
            return
        
        # Validate output path
        output_dir = self.output_directory.get()
        output_filename = self.output_filename.get()
        
        is_valid, error_msg = validate_output_path(output_dir, output_filename)
        if not is_valid:
            messagebox.showerror("Invalid Output Path", error_msg)
            return
        
        # Export results directly (no async)
        try:
            # Update status
            self.status_text.set("Exporting results...")
            self.update_idletasks()  # Force UI update
            
            # Sanitize filename
            output_filename = sanitize_filename(output_filename)
            
            # Create full path
            output_path = os.path.join(output_dir, output_filename)
            
            # Write results to Excel
            excel_writer = ExcelWriter(output_path)
            output_file = excel_writer.write_results(self.results)
            
            # Update status
            self.status_text.set(f"Results exported to {output_file}")
            
            # Show success message
            messagebox.showinfo(
                "Export Successful",
                f"Results exported to {output_path}"
            )
            
            # Show results screen
            self._show_results()
            
        except Exception as e:
            logger.error(f"Error exporting results: {e}")
            logger.debug(traceback.format_exc())
            
            # Show error message
            messagebox.showerror("Export Error", f"Failed to export results: {str(e)}")
            
            # Update status
            self.status_text.set(f"Export error: {str(e)}")
    
    def _show_about(self):
        """Show about dialog."""
        about_dialog = ctk.CTkToplevel(self)
        about_dialog.title("About")
        about_dialog.geometry("400x300")
        about_dialog.transient(self)
        about_dialog.grab_set()
        
        # Center the dialog
        about_dialog.update_idletasks()
        width = about_dialog.winfo_width()
        height = about_dialog.winfo_height()
        x = self.winfo_x() + (self.winfo_width() // 2) - (width // 2)
        y = self.winfo_y() + (self.winfo_height() // 2) - (height // 2)
        about_dialog.geometry(f"+{x}+{y}")
        
        # Content
        frame = ctk.CTkFrame(about_dialog)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # App name and version
        ctk.CTkLabel(
            frame, text=APP_NAME, font=("", 20, "bold")
        ).pack(pady=(10, 0))
        
        ctk.CTkLabel(
            frame, text=f"Version {APP_VERSION}"
        ).pack(pady=(0, 10))
        
        # Description
        description = (
            "This application automates checking the status of student applications "
            "on the Russia-Edu website. It reads student data from an Excel file, "
            "queries the website for each student, and exports the results."
        )
        
        ctk.CTkLabel(
            frame, text=description, wraplength=350, justify="center"
        ).pack(pady=10)
        
        # Copyright
        ctk.CTkLabel(
            frame, text=f"© {datetime.now().year}", font=("", 10)
        ).pack(pady=10)
        
        # Close button
        ctk.CTkButton(
            frame, text="Close", command=about_dialog.destroy, width=100
        ).pack(pady=10)
    
    def _update_button_states(self):
        """Update button states based on current application state."""
        if self.is_running:
            self.preview_btn.configure(state="disabled")
            self.start_btn.configure(state="disabled")
            self.stop_btn.configure(state="normal")
            self.export_btn.configure(state="disabled")
        else:
            self.preview_btn.configure(state="normal")
            
            if self.students:
                self.start_btn.configure(state="normal")
            else:
                self.start_btn.configure(state="disabled")
            
            self.stop_btn.configure(state="disabled")
            
            if self.results:
                self.export_btn.configure(state="normal")
            else:
                self.export_btn.configure(state="disabled")
    
    def _on_close(self):
        """Handle window close event."""
        if self.is_running:
            if not messagebox.askyesno(
                "Confirm Exit",
                "Processing is in progress. Are you sure you want to exit?"
            ):
                return
        
        # Stop processing if running
        if self.is_running:
            self.scraper.stop()
        
        # Stop AsyncRunner
        AsyncRunner.stop()
        
        # Destroy window
        self.destroy()