"""
Student table component for displaying student data.
"""

import tkinter as tk
from tkinter import ttk
from typing import List, Any, Optional, Dict, Tuple

import customtkinter as ctk

from app.utils.logger import get_logger

logger = get_logger()

class StudentTable(ctk.CTkFrame):
    """Table component for displaying student data."""
    
    def __init__(self, master, **kwargs):
        """
        Initialize the StudentTable.
        
        Args:
            master: Parent widget.
            **kwargs: Additional arguments for the frame.
        """
        super().__init__(master, **kwargs)
        
        # Create a frame to contain the treeview and scrollbars
        self.tree_frame = ctk.CTkFrame(self)
        self.tree_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create the treeview widget
        self.tree = ttk.Treeview(self.tree_frame, columns=(), show="headings")
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Add vertical scrollbar
        self.vsb = ttk.Scrollbar(self.tree_frame, orient="vertical", command=self.tree.yview)
        self.vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=self.vsb.set)
        
        # Add horizontal scrollbar
        self.hsb = ttk.Scrollbar(self, orient="horizontal", command=self.tree.xview)
        self.hsb.pack(side=tk.BOTTOM, fill=tk.X)
        self.tree.configure(xscrollcommand=self.hsb.set)
        
        # Configure row colors
        self.tree.tag_configure('odd', background='#f5f5f5')
        self.tree.tag_configure('even', background='#ffffff')
        self.tree.tag_configure('error', background='#ffe6e6')
        
        # Configure style
        self._configure_style()
    
    def _configure_style(self):
        """Configure the treeview style."""
        style = ttk.Style()
        
        # Configure the treeview
        style.configure("Treeview", font=('Arial', 10), rowheight=25)
        style.configure("Treeview.Heading", font=('Arial', 10, 'bold'))
        
        # Remove borders
        style.layout("Treeview", [
            ('Treeview.treearea', {'sticky': 'nswe'})
        ])
    
    def set_columns(self, columns: List[str]):
        """
        Set the columns of the table.
        
        Args:
            columns (List[str]): List of column names.
        """
        # Delete existing items and columns
        self.tree.delete(*self.tree.get_children())
        self.tree["columns"] = tuple(columns)
        
        # Configure column headings
        for i, col in enumerate(columns):
            self.tree.heading(i, text=col)
            
            # Set default column width based on content
            self.tree.column(i, width=max(100, len(col) * 10))
    
    def set_data(self, data: List[List[Any]]):
        """
        Set the data in the table.
        
        Args:
            data (List[List[Any]]): List of rows, where each row is a list of values.
        """
        # Delete existing items
        self.tree.delete(*self.tree.get_children())
        
        # Insert new data
        for i, row in enumerate(data):
            values = []
            for value in row:
                if value is None:
                    values.append("")
                else:
                    values.append(value)
            
            # Determine row tag
            if any(str(value).startswith("Error") for value in values):
                tag = 'error'
            elif i % 2 == 0:
                tag = 'even'
            else:
                tag = 'odd'
            
            self.tree.insert("", tk.END, values=values, tags=(tag,))
    
    def add_row(self, row: List[Any]):
        """
        Add a single row to the table.
        
        Args:
            row (List[Any]): List of values for the row.
        """
        # Process values
        values = []
        for value in row:
            if value is None:
                values.append("")
            else:
                values.append(value)
        
        # Get current number of rows
        children = self.tree.get_children()
        row_index = len(children)
        
        # Determine row tag
        if any(str(value).startswith("Error") for value in values):
            tag = 'error'
        elif row_index % 2 == 0:
            tag = 'even'
        else:
            tag = 'odd'
        
        # Insert the row
        item_id = self.tree.insert("", tk.END, values=values, tags=(tag,))
        
        # Scroll to the new row
        self.tree.see(item_id)
    
    def clear(self):
        """Clear all data from the table."""
        self.tree.delete(*self.tree.get_children())
    
    def get_selected_item(self) -> Optional[Dict[str, Any]]:
        """
        Get the selected item from the table.
        
        Returns:
            Optional[Dict[str, Any]]: Dictionary with column names as keys and values, or None if no item is selected.
        """
        selected_items = self.tree.selection()
        if not selected_items:
            return None
        
        # Get the first selected item
        item_id = selected_items[0]
        values = self.tree.item(item_id, "values")
        
        # Get column names
        columns = self.tree["columns"]
        
        # Create dictionary
        result = {}
        for i, col in enumerate(columns):
            if i < len(values):
                result[col] = values[i]
            else:
                result[col] = None
        
        return result