"""
Results screen for displaying and analyzing processing results.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import os
from typing import List, Dict, Any, Optional, Callable
import json
from datetime import datetime
import webbrowser

import customtkinter as ctk
import pandas as pd
from PIL import Image, ImageTk

from app.data.student import StudentResult
from app.utils.logger import get_logger
from app.ui.components.student_table import StudentTable
from app.ui.components.custom_widgets import ScrollableFrame, IconButton, HyperlinkLabel

logger = get_logger()

class ResultsScreen(ctk.CTkToplevel):
    """Screen for displaying and analyzing processing results."""
    
    def __init__(self, master, results: List[StudentResult], export_path: Optional[str] = None):
        """
        Initialize the results screen.
        
        Args:
            master: Parent widget.
            results (List[StudentResult]): List of student results.
            export_path (Optional[str]): Path to the exported Excel file.
        """
        super().__init__(master)
        self.title("Processing Results")
        self.geometry("800x600")
        self.resizable(True, True)
        
        # Store parameters
        self.master = master
        self.results = results
        self.export_path = export_path
        
        # Initialize variables
        self.status_filter = tk.StringVar(value="All")
        self.error_only = tk.BooleanVar(value=False)
        self.search_text = tk.StringVar(value="")
        
        # Create UI
        self._create_widgets()
        
        # Populate data
        self._populate_data()
        
        # Center window
        self._center_window()
    
    def _create_widgets(self):
        """Create widgets for the results screen."""
        # Main frame
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Top section - Summary
        self.summary_frame = ctk.CTkFrame(self.main_frame)
        self.summary_frame.pack(fill="x", padx=10, pady=10)
        
        # Summary header
        ctk.CTkLabel(self.summary_frame, text="Summary", font=("", 16, "bold")).pack(anchor="w", padx=5, pady=5)
        
        # Summary grid
        self.summary_grid = ctk.CTkFrame(self.summary_frame)
        self.summary_grid.pack(fill="x", padx=5, pady=5)
        
        # Stats will be populated later
        self.stat_labels = {}
        
        # Filter section
        self.filter_frame = ctk.CTkFrame(self.main_frame)
        self.filter_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        filter_inner_frame = ctk.CTkFrame(self.filter_frame)
        filter_inner_frame.pack(fill="x", padx=5, pady=5)
        
        # Status filter
        ctk.CTkLabel(filter_inner_frame, text="Filter by status:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        
        # Status dropdown - will be populated with actual statuses
        self.status_dropdown = ctk.CTkOptionMenu(
            filter_inner_frame, variable=self.status_filter, 
            values=["All", "Анкета введена", "На рассмотрении вуза", "Распределен", "Направлен", "Зачислен", "Error"],
            command=self._apply_filters
        )
        self.status_dropdown.grid(row=0, column=1, sticky="w", padx=5, pady=5)
        
        # Error only checkbox
        ctk.CTkCheckBox(
            filter_inner_frame, text="Show errors only", variable=self.error_only, 
            command=self._apply_filters
        ).grid(row=0, column=2, sticky="w", padx=20, pady=5)
        
        # Search
        ctk.CTkLabel(filter_inner_frame, text="Search:").grid(row=0, column=3, sticky="w", padx=(20, 5), pady=5)
        
        search_entry = ctk.CTkEntry(filter_inner_frame, textvariable=self.search_text, width=150)
        search_entry.grid(row=0, column=4, sticky="w", padx=5, pady=5)
        search_entry.bind("<Return>", lambda e: self._apply_filters())
        
        ctk.CTkButton(
            filter_inner_frame, text="Search", command=self._apply_filters, width=80
        ).grid(row=0, column=5, sticky="w", padx=5, pady=5)
        
        # Configure filter grid
        filter_inner_frame.grid_columnconfigure(6, weight=1)
        
        # Table section
        self.table_frame = ctk.CTkFrame(self.main_frame)
        self.table_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        # Create table
        self.table = StudentTable(self.table_frame)
        self.table.pack(fill="both", expand=True)
        
        # Bottom section - Actions
        self.actions_frame = ctk.CTkFrame(self.main_frame)
        self.actions_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        # Export info
        if self.export_path and os.path.exists(self.export_path):
            export_info_frame = ctk.CTkFrame(self.actions_frame)
            export_info_frame.pack(fill="x", padx=5, pady=5)
            
            ctk.CTkLabel(export_info_frame, text="Results exported to:").pack(side="left", padx=5, pady=5)
            
            file_path = os.path.abspath(self.export_path)
            file_link = HyperlinkLabel(
                export_info_frame, text=file_path, url=f"file://{file_path}"
            )
            file_link.pack(side="left", padx=5, pady=5)
            
            # Open folder button
            def open_folder():
                folder_path = os.path.dirname(file_path)
                if os.path.exists(folder_path):
                    if os.name == 'nt':  # Windows
                        os.startfile(folder_path)
                    else:  # macOS and Linux
                        webbrowser.open(f"file://{folder_path}")
            
            ctk.CTkButton(
                export_info_frame, text="Open Folder", command=open_folder, width=100
            ).pack(side="right", padx=5, pady=5)
        
        # Buttons
        button_frame = ctk.CTkFrame(self.actions_frame)
        button_frame.pack(fill="x", padx=5, pady=5)
        
        # Close button
        ctk.CTkButton(
            button_frame, text="Close", command=self.destroy, width=100
        ).pack(side="right", padx=5, pady=5)
        
        # Export button
        ctk.CTkButton(
            button_frame, text="Export Filtered Results", command=self._export_filtered, width=150
        ).pack(side="right", padx=5, pady=5)
    
    def _populate_data(self):
        """Populate data in the UI."""
        if not self.results:
            ctk.CTkLabel(
                self.main_frame, text="No results available", font=("", 14, "bold")
            ).pack(pady=20)
            return
        
        # Calculate summary statistics
        stats = self._calculate_stats()
        
        # Create grid for stats
        row = 0
        col = 0
        max_cols = 3
        
        for stat_name, stat_value in stats.items():
            frame = ctk.CTkFrame(self.summary_grid)
            frame.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
            
            label = ctk.CTkLabel(frame, text=stat_name, font=("", 12))
            label.pack(anchor="w", padx=5, pady=(5, 0))
            
            value = ctk.CTkLabel(frame, text=str(stat_value), font=("", 16, "bold"))
            value.pack(anchor="w", padx=5, pady=(0, 5))
            
            self.stat_labels[stat_name] = value
            
            col += 1
            if col >= max_cols:
                col = 0
                row += 1
        
        # Configure grid
        for i in range(max_cols):
            self.summary_grid.grid_columnconfigure(i, weight=1)
        
        # Setup table columns
        columns = [
            "Reg Number", "Email", "Status", "Name (Cyrillic)", "Name (Latin)",
            "Country", "Education Level", "Program", "Preparatory Faculty", "Error"
        ]
        
        self.table.set_columns(columns)
        
        # Apply initial filters to populate table
        self._apply_filters()
        
        # Update status dropdown with actual statuses
        statuses = self._get_unique_statuses()
        status_values = ["All"] + sorted(statuses) + ["Error"]
        self.status_dropdown.configure(values=status_values)
    
    def _calculate_stats(self) -> Dict[str, Any]:
        """
        Calculate statistics from results.
        
        Returns:
            Dict[str, Any]: Statistics dictionary.
        """
        total = len(self.results)
        processed = sum(1 for r in self.results if r.processed)
        errors = sum(1 for r in self.results if r.error)
        
        # Count by status
        status_counts = {}
        for result in self.results:
            if result.status:
                status = result.status
                status_counts[status] = status_counts.get(status, 0) + 1
        
        # Calculate success rate
        success_rate = (processed / total) * 100 if total > 0 else 0
        
        # Get timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        return {
            "Total Students": total,
            "Successfully Processed": processed,
            "Errors": errors,
            "Success Rate": f"{success_rate:.1f}%",
            "Timestamp": timestamp,
            **{f"Status: {k}": v for k, v in status_counts.items()}
        }
    
    def _apply_filters(self, *args):
        """Apply filters to the results table."""
        filtered_results = self._filter_results()
        
        # Convert to table format
        data = []
        for result in filtered_results:
            row = [
                result.reg_number,
                result.email,
                result.status or "N/A",
                result.full_name_cyrillic or "N/A",
                result.full_name_latin or "N/A",
                result.country or "N/A",
                result.education_level or "N/A",
                result.education_program or "N/A",
                result.preparatory_faculty or "N/A",
                result.error or ""
            ]
            data.append(row)
        
        # Update table
        self.table.set_data(data)
    
    def _filter_results(self) -> List[StudentResult]:
        """
        Filter results based on current filter settings.
        
        Returns:
            List[StudentResult]: Filtered results.
        """
        filtered = []
        
        status_filter = self.status_filter.get()
        error_only = self.error_only.get()
        search_text = self.search_text.get().lower()
        
        for result in self.results:
            # Apply status filter
            if status_filter != "All":
                if status_filter == "Error":
                    if not result.error:
                        continue
                elif result.status != status_filter:
                    continue
            
            # Apply error filter
            if error_only and not result.error:
                continue
            
            # Apply search filter
            if search_text:
                # Check if search text is in any of the result fields
                search_fields = [
                    result.reg_number,
                    result.email,
                    result.full_name_cyrillic,
                    result.full_name_latin,
                    result.status,
                    result.country,
                    result.education_level,
                    result.education_program,
                    result.preparatory_faculty,
                    result.error
                ]
                
                if not any(search_text in str(field).lower() for field in search_fields if field):
                    continue
            
            filtered.append(result)
        
        return filtered
    
    def _get_unique_statuses(self) -> List[str]:
        """
        Get unique status values from results.
        
        Returns:
            List[str]: List of unique status values.
        """
        statuses = set()
        for result in self.results:
            if result.status:
                statuses.add(result.status)
        
        return list(statuses)
    
    def _export_filtered(self):
        """Export filtered results to Excel."""
        filtered_results = self._filter_results()
        
        if not filtered_results:
            messagebox.showinfo("Export", "No results to export after filtering.")
            return
        
        try:
            # Ask for save location
            from tkinter import filedialog
            file_path = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel Files", "*.xlsx")],
                initialfile="filtered_results.xlsx"
            )
            
            if not file_path:
                return
            
            # Convert to DataFrame
            data = []
            for result in filtered_results:
                data.append({
                    "Reg Number": result.reg_number,
                    "Email": result.email,
                    "Status": result.status,
                    "Name (Cyrillic)": result.full_name_cyrillic,
                    "Name (Latin)": result.full_name_latin,
                    "Country": result.country,
                    "Education Level": result.education_level,
                    "Education Program": result.education_program,
                    "Preparatory Faculty": result.preparatory_faculty,
                    "Error": result.error,
                    "Timestamp": result.query_timestamp.strftime("%Y-%m-%d %H:%M:%S") if result.query_timestamp else ""
                })
            
            df = pd.DataFrame(data)
            
            # Export to Excel
            df.to_excel(file_path, index=False)
            
            messagebox.showinfo("Export Successful", f"Filtered results exported to {file_path}")
            
            # Open the file
            if messagebox.askyesno("Open File", "Do you want to open the exported file?"):
                if os.path.exists(file_path):
                    if os.name == 'nt':  # Windows
                        os.startfile(file_path)
                    else:  # macOS and Linux
                        webbrowser.open(f"file://{file_path}")
            
        except Exception as e:
            logger.error(f"Error exporting filtered results: {e}")
            messagebox.showerror("Export Error", f"Failed to export results: {str(e)}")
    
    def _center_window(self):
        """Center the window on the parent."""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = self.master.winfo_rootx() + (self.master.winfo_width() // 2) - (width // 2)
        y = self.master.winfo_rooty() + (self.master.winfo_height() // 2) - (height // 2)
        self.geometry(f"+{x}+{y}")