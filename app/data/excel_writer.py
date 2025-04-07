"""
Module to write student results to Excel files.
"""

import os
from typing import List, Dict, Any, Optional
import pandas as pd
from pathlib import Path
import datetime

from app.data.student import StudentResult
from app.utils.logger import get_logger
from app.utils.exceptions import ExcelWriteError
from app.config import EXCEL_COLUMNS

logger = get_logger()

class ExcelWriter:
    """Class to write student results to Excel files."""
    
    def __init__(self, file_path: str):
        """
        Initialize the ExcelWriter with a file path.
        
        Args:
            file_path (str): Path to the Excel file to write.
        """
        self.file_path = Path(file_path)
        self._ensure_directory()
    
    def _ensure_directory(self) -> None:
        """Ensure the directory for the output file exists."""
        directory = self.file_path.parent
        directory.mkdir(parents=True, exist_ok=True)
    
    def write_results(self, results: List[StudentResult]) -> str:
        """
        Write student results to an Excel file.
        
        Args:
            results (List[StudentResult]): List of student results to write.
            
        Returns:
            str: Path to the written Excel file.
            
        Raises:
            ExcelWriteError: If there's an error writing the Excel file.
        """
        try:
            # Convert results to rows
            rows = [result.to_excel_row() for result in results]
            
            # Create DataFrame
            df = pd.DataFrame(rows, columns=EXCEL_COLUMNS)
            
            # Write to Excel
            with pd.ExcelWriter(self.file_path, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Results')
                
                # Auto-adjust column widths
                worksheet = writer.sheets['Results']
                for idx, col in enumerate(df.columns):
                    column_width = max(
                        df[col].astype(str).map(len).max(),
                        len(col)
                    ) + 2
                    # Excel column width is in characters
                    worksheet.column_dimensions[worksheet.cell(1, idx+1).column_letter].width = column_width
            
            logger.info(f"Successfully wrote {len(results)} results to {self.file_path}")
            return str(self.file_path)
            
        except Exception as e:
            logger.error(f"Error writing Excel file: {e}")
            raise ExcelWriteError(f"Error writing Excel file: {str(e)}")
    
    def append_results(self, results: List[StudentResult]) -> str:
        """
        Append student results to an existing Excel file.
        If the file doesn't exist, create it.
        
        Args:
            results (List[StudentResult]): List of student results to append.
            
        Returns:
            str: Path to the updated Excel file.
            
        Raises:
            ExcelWriteError: If there's an error updating the Excel file.
        """
        try:
            # Convert results to rows
            new_rows = [result.to_excel_row() for result in results]
            
            # If file exists, read existing data and append new rows
            if self.file_path.exists():
                existing_df = pd.read_excel(self.file_path)
                
                # Check if columns match
                if list(existing_df.columns) != EXCEL_COLUMNS:
                    logger.warning("Existing file has different columns. Creating new file.")
                    return self.write_results(results)
                
                # Create DataFrame with new rows
                new_df = pd.DataFrame(new_rows, columns=EXCEL_COLUMNS)
                
                # Combine DataFrames
                combined_df = pd.concat([existing_df, new_df], ignore_index=True)
                
                # Write combined DataFrame
                combined_df.to_excel(self.file_path, index=False, sheet_name='Results')
                
                logger.info(f"Successfully appended {len(results)} results to {self.file_path}")
                return str(self.file_path)
            else:
                # File doesn't exist, create new file
                return self.write_results(results)
            
        except Exception as e:
            logger.error(f"Error appending to Excel file: {e}")
            raise ExcelWriteError(f"Error appending to Excel file: {str(e)}")
    
    @staticmethod
    def generate_default_filename() -> str:
        """
        Generate a default filename for the Excel file.
        
        Returns:
            str: Default filename with timestamp.
        """
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"student_status_results_{timestamp}.xlsx"