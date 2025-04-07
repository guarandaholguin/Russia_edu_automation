"""
Data models for student information.
"""

import dataclasses
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
import datetime

@dataclass
class StudentInput:
    """Data model for input student information from Excel."""
    reg_number: str
    email: str
    row_index: int
    
    def validate(self) -> List[str]:
        """
        Validate student input data.
        
        Returns:
            List[str]: List of validation error messages. Empty if valid.
        """
        errors = []
        
        if not self.reg_number or not isinstance(self.reg_number, str):
            errors.append(f"Invalid registration number: {self.reg_number}")
        
        if not self.email or not isinstance(self.email, str) or '@' not in self.email:
            errors.append(f"Invalid email address: {self.email}")
            
        return errors

@dataclass
class StudentResult:
    """Data model for student information extracted from the website."""
    # Input data
    reg_number: str
    email: str
    row_index: int
    
    # Extracted data
    full_name_cyrillic: Optional[str] = None
    full_name_latin: Optional[str] = None
    system_reg_number: Optional[str] = None
    country: Optional[str] = None
    status: Optional[str] = None
    status_message: Optional[str] = None
    education_level: Optional[str] = None
    education_program: Optional[str] = None
    preparatory_faculty: Optional[str] = None
    
    # Processing information
    query_timestamp: datetime.datetime = dataclasses.field(
        default_factory=lambda: datetime.datetime.now()
    )
    error: Optional[str] = None
    processed: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the student result to a dictionary.
        
        Returns:
            Dict[str, Any]: Dictionary representation of student result.
        """
        return dataclasses.asdict(self)
    
    def to_excel_row(self) -> List[Any]:
        """
        Convert the student result to a row for Excel export.
        
        Returns:
            List[Any]: List of values to write to Excel.
        """
        return [
            self.reg_number,
            self.email,
            self.full_name_cyrillic,
            self.full_name_latin,
            # self.system_reg_number,
            self.country,
            self.status,
            self.status_message,
            self.education_level,
            self.education_program,
            self.preparatory_faculty,
            self.query_timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            self.error
        ]
    
    @classmethod
    def from_student_input(cls, student_input: StudentInput) -> 'StudentResult':
        """
        Create a StudentResult object from a StudentInput object.
        
        Args:
            student_input (StudentInput): The input student data.
            
        Returns:
            StudentResult: A new StudentResult object.
        """
        return cls(
            reg_number=student_input.reg_number,
            email=student_input.email,
            row_index=student_input.row_index
        )