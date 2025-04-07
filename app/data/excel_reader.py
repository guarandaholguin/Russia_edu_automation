"""
Module to read student data from Excel files.
"""

import os
from typing import List, Optional, Tuple, Dict, Any
import pandas as pd
import numpy as np
from pathlib import Path

from app.data.student import StudentInput
from app.utils.logger import get_logger
from app.utils.exceptions import ExcelReadError

logger = get_logger()

class ExcelReader:
    """Class to read and parse Excel files with student data."""
    
    def __init__(self, file_path: str):
        """
        Initialize the ExcelReader with a file path.
        
        Args:
            file_path (str): Path to the Excel file.
        
        Raises:
            ExcelReadError: If the file does not exist or is not an Excel file.
        """
        self.file_path = Path(file_path)
        self._validate_file()
    
    def _validate_file(self) -> None:
        """
        Validate that the file exists and is an Excel file.
        
        Raises:
            ExcelReadError: If the file does not exist or is not an Excel file.
        """
        if not self.file_path.exists():
            raise ExcelReadError(f"File does not exist: {self.file_path}")
        
        valid_extensions = ['.xlsx', '.xls', '.xlsm', '.xlsb']
        if self.file_path.suffix.lower() not in valid_extensions:
            raise ExcelReadError(
                f"Invalid file extension: {self.file_path.suffix}. "
                f"Expected one of {valid_extensions}"
            )
    
    def get_sheet_names(self) -> List[str]:
        """
        Get the names of all sheets in the Excel file.
        
        Returns:
            List[str]: List of sheet names.
            
        Raises:
            ExcelReadError: If there's an error reading the Excel file.
        """
        try:
            return pd.ExcelFile(self.file_path).sheet_names
        except Exception as e:
            logger.error(f"Error reading Excel file: {e}")
            raise ExcelReadError(f"Error reading Excel file: {str(e)}")
    
    def read_students(self, 
                      sheet_name: Optional[str] = None, 
                      reg_number_col: str = "№ SOLICITUD", 
                      email_col: str = "CORREO RUSO") -> List[StudentInput]:
        """
        Read student data from the Excel file.
        
        Args:
            sheet_name (str, optional): Name of the sheet to read from. 
                                        If None, reads the first sheet.
            reg_number_col (str): Column name for registration number.
            email_col (str): Column name for email address.
            
        Returns:
            List[StudentInput]: List of StudentInput objects.
            
        Raises:
            ExcelReadError: If there's an error reading the Excel file or 
                            the required columns are not found.
        """
        try:
            # Try to read the Excel file
            if sheet_name:
                df = pd.read_excel(self.file_path, sheet_name=sheet_name)
            else:
                df = pd.read_excel(self.file_path)
            
            # Check if the required columns exist
            if reg_number_col not in df.columns:
                raise ExcelReadError(f"Missing registration number column: {reg_number_col}")
            
            if email_col not in df.columns:
                raise ExcelReadError(f"Missing email column: {email_col}")
            
            # Extract student data
            students = []
            
            for idx, row in df.iterrows():
                # Skip rows with missing data
                if pd.isna(row[reg_number_col]) or pd.isna(row[email_col]):
                    logger.warning(f"Skipping row {idx+2} due to missing data")
                    continue
                
                # Create StudentInput object
                reg_number = str(row[reg_number_col]).strip()
                email = str(row[email_col]).strip()
                
                student = StudentInput(reg_number=reg_number, email=email, row_index=idx)
                
                # Validate student data
                validation_errors = student.validate()
                if validation_errors:
                    logger.warning(f"Invalid student data at row {idx+2}: {validation_errors}")
                    continue
                
                students.append(student)
            
            logger.info(f"Successfully read {len(students)} students from {self.file_path}")
            return students
            
        except ExcelReadError:
            # Re-raise ExcelReadError
            raise
        except Exception as e:
            logger.error(f"Error reading student data: {e}")
            raise ExcelReadError(f"Error reading student data: {str(e)}")
    
    def get_preview_data(self, 
                        sheet_name: Optional[str] = None, 
                        max_rows: int = 10) -> Tuple[List[str], List[List[Any]]]:
        """
        Get a preview of the data in the Excel file.
        
        Args:
            sheet_name (str, optional): Name of the sheet to preview.
            max_rows (int): Maximum number of rows to include in the preview.
            
        Returns:
            Tuple[List[str], List[List[Any]]]: Tuple of column names and data rows.
            
        Raises:
            ExcelReadError: If there's an error reading the Excel file.
        """
        try:
            if sheet_name:
                df = pd.read_excel(self.file_path, sheet_name=sheet_name, nrows=max_rows)
            else:
                df = pd.read_excel(self.file_path, nrows=max_rows)
            
            # Convert columns to list of strings
            columns = list(df.columns)
            
            # Convert data to list of lists, replacing NaN with None
            data = []
            for idx, row in df.iterrows():
                row_data = []
                for col in columns:
                    value = row[col]
                    if pd.isna(value):
                        row_data.append(None)
                    else:
                        row_data.append(value)
                data.append(row_data)
            
            return columns, data
            
        except Exception as e:
            logger.error(f"Error getting preview data: {e}")
            raise ExcelReadError(f"Error getting preview data: {str(e)}")