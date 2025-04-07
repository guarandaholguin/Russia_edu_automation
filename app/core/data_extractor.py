"""
Module for extracting student data from the Russia-Edu website.
"""

import re
from typing import Dict, Any, Optional, Match
from playwright.async_api import Page

from app.data.student import StudentInput, StudentResult
from app.utils.logger import get_logger
from app.utils.exceptions import DataExtractionError

logger = get_logger()

class DataExtractor:
    """Class to extract student data from the Russia-Edu website."""
    
    # Regular expressions for data extraction
    REG_NUMBER_PATTERN = r'[A-Z]{3}-\d+/\d+'  # Modificado para ser más general
    CYRILLIC_NAME_PATTERN = r'(?P<name>[А-Яа-яЁё\s]+)'
    LATIN_NAME_PATTERN = r'[A-Z\s]+'
    
    def __init__(self):
        """Initialize the DataExtractor."""
        pass
    
    async def extract_student_data(self, page: Page, student_input: StudentInput) -> StudentResult:
        """
        Extract student data from the tracking result page.
        
        Args:
            page (Page): Playwright page object with loaded tracking result.
            student_input (StudentInput): Input student data.
            
        Returns:
            StudentResult: Extracted student data.
            
        Raises:
            DataExtractionError: If data extraction fails.
        """
        result = StudentResult.from_student_input(student_input)
        
        try:
            # Check if the page contains error message
            error_element = await page.query_selector('.alert-error')
            if error_element:
                error_text = await error_element.inner_text()
                raise DataExtractionError(f"Error on tracking page: {error_text}")
            
            # Extract header information (name, reg number, country)
            header_text = await self._get_text(page, 'h3')
            if header_text:
                result = self._parse_header(header_text, result)
            
            # Extract status - versión corregida
            status_selector = '.span8:has(.icon-check, .icon-share, .icon-ok-sign, .icon-arrow-right, .icon-ok)'
            status_text = await self._get_text(page, status_selector)
            if status_text:
                result.status = status_text.strip()
            
            # Extract status message - Capturar todos los párrafos p dentro de divs span8 text-shadow-white
            status_messages = []
            message_elements = await page.query_selector_all('.span8.text-shadow-white p')
            for element in message_elements:
                message = await element.inner_text()
                if message and message.strip():
                    status_messages.append(message.strip())
            
            if status_messages:
                result.status_message = "\n".join(status_messages)
            
            # Extract Latin name from the span with class="color-gray text-shadow-white" after the first BR tag
            latin_name_selector = 'h3 span.color-gray.text-shadow-white:nth-of-type(2)'
            latin_name = await self._get_text(page, latin_name_selector)
            if latin_name:
                result.full_name_latin = latin_name.strip()
            
            # Extract education level
            education_selector = '.span4:has-text("Уровень образования:") + .span8'
            education_level = await self._get_text(page, education_selector)
            if education_level:
                result.education_level = education_level.strip()
            
            # Extract education program - incluyendo toda la información
            program_blocks = []
            program_title_selector = '.span4:has-text("Образовательная программа:") + .span8'
            program_title = await self._get_text(page, program_title_selector)
            if program_title:
                program_blocks.append(program_title.strip())
            
            # Buscar información adicional del programa educativo
            program_info_selector = '.span8:has-text("В 2026 году")'
            program_info = await self._get_text(page, program_info_selector)
            if program_info:
                program_blocks.append(program_info.strip())
            
            if program_blocks:
                result.education_program = "\n".join(program_blocks)
            
            # Extract preparatory faculty info - incluyendo toda la información
            prep_blocks = []
            prep_title_selector = '.span4:has-text("Подготовительный факультет:") + .span8'
            prep_title = await self._get_text(page, prep_title_selector)
            if prep_title:
                prep_blocks.append(prep_title.strip())
            
            # Buscar información adicional de la facultad preparatoria
            prep_info_selector = '.span8:has-text("В 2025 году")'
            prep_info = await self._get_text(page, prep_info_selector)
            if prep_info:
                prep_blocks.append(prep_info.strip())
            
            if prep_blocks:
                result.preparatory_faculty = "\n".join(prep_blocks)
            
            # Extract registration number from the system explicitly
            reg_number_selector = '.span8:has-text("Ваш регистрационный номер в Системе")'
            reg_number_text = await self._get_text(page, reg_number_selector)
            if reg_number_text:
                reg_number_match = re.search(r'[A-Z]{3}-\d+/\d+', reg_number_text)
                if reg_number_match:
                    result.system_reg_number = reg_number_match.group(0)
            
            # Extract country explicitly
            country = await self._extract_country(page, header_text)
            if country:
                result.country = country
            
            # Mark as processed
            result.processed = True
            logger.info(f"Successfully extracted data for student {result.reg_number}")
            
            return result
            
        except DataExtractionError:
            # Re-raise DataExtractionError
            raise
        except Exception as e:
            logger.error(f"Error extracting student data: {e}")
            result.error = f"Error extracting data: {str(e)}"
            return result
    
    async def _extract_country(self, page: Page, header_text: str) -> Optional[str]:
        """
        Extract country information using different methods.
        
        Args:
            page (Page): Playwright page object.
            header_text (str): Header text from the page.
            
        Returns:
            Optional[str]: Country name or None if not found.
        """
        # Método 1: Buscar en el texto del encabezado con una expresión regular más general
        # Primero encontramos el número de registro
        reg_match = re.search(r'([A-Z]{3}-\d+/\d+)', header_text)
        if reg_match:
            reg_number = reg_match.group(1)
            # Ahora buscamos el país que viene después del número de registro
            after_reg = header_text[header_text.index(reg_number) + len(reg_number):]
            country_match = re.search(r',\s*([^,\n]+)', after_reg)
            if country_match:
                return country_match.group(1).strip()
        
        # Método 2: Extraer desde el primer span.color-gray en h3 (el país suele estar aquí)
        span_selector = 'h3 span.color-gray.text-shadow-white:first-of-type'
        span_text = await self._get_text(page, span_selector)
        if span_text:
            # El texto suele ser algo como "ECU-10520/25, Эквадор"
            parts = span_text.split(',')
            if len(parts) > 1:
                return parts[1].strip()
        
        # Si no encontramos el país con ningún método, intentamos extraerlo del código de país
        # en el número de registro (por ejemplo, ECU para Ecuador)
        if reg_match:
            country_code = reg_match.group(1).split('-')[0]
            country_map = {
                # América del Sur
                'ARG': 'Аргентина',  # Argentina
                'BOL': 'Боливия',    # Bolivia
                'BRA': 'Бразилия',   # Brasil
                'CHL': 'Чили',       # Chile
                'COL': 'Колумбия',   # Colombia
                'ECU': 'Эквадор',    # Ecuador
                'GUY': 'Гайана',     # Guyana
                'PRY': 'Парагвай',   # Paraguay
                'PER': 'Перу',       # Perú
                'SUR': 'Суринам',    # Surinam
                'URY': 'Уругвай',    # Uruguay
                'VEN': 'Венесуэла',  # Venezuela
                
                # América Central
                'BLZ': 'Белиз',      # Belice
                'CRI': 'Коста-Рика', # Costa Rica
                'SLV': 'Сальвадор',  # El Salvador
                'GTM': 'Гватемала',  # Guatemala
                'HND': 'Гондурас',   # Honduras
                'NIC': 'Никарагуа',  # Nicaragua
                'PAN': 'Панама',     # Panamá
                
                # El Caribe
                'ATG': 'Антигуа и Барбуда',    # Antigua y Barbuda
                'BHS': 'Багамские Острова',    # Bahamas
                'BRB': 'Барбадос',            # Barbados
                'CUB': 'Куба',                # Cuba
                'DMA': 'Доминика',            # Dominica
                'DOM': 'Доминиканская Республика', # República Dominicana
                'GRD': 'Гренада',             # Grenada
                'HTI': 'Гаити',               # Haití
                'JAM': 'Ямайка',              # Jamaica
                'KNA': 'Сент-Китс и Невис',   # Saint Kitts and Nevis
                'LCA': 'Сент-Люсия',          # Saint Lucia
                'VCT': 'Сент-Винсент и Гренадины', # Saint Vincent and the Grenadines
                'TTO': 'Тринидад и Тобаго',   # Trinidad and Tobago
                
                # México (en América del Norte pero culturalmente parte de Latinoamérica)
                'MEX': 'Мексика'   # México
            }
            return country_map.get(country_code)
        
        return None
    
    def _parse_header(self, header_text: str, result: StudentResult) -> StudentResult:
        """
        Parse the header text to extract name, registration number, and country.
        
        Args:
            header_text (str): Header text from the page.
            result (StudentResult): Current student result.
            
        Returns:
            StudentResult: Updated student result.
        """
        try:
            # Extract full name in Cyrillic
            cyrillic_match = re.search(self.CYRILLIC_NAME_PATTERN, header_text)
            if cyrillic_match:
                result.full_name_cyrillic = cyrillic_match.group('name').strip()
            
            # Extract registration number
            reg_match = re.search(self.REG_NUMBER_PATTERN, header_text)
            if reg_match:
                result.system_reg_number = reg_match.group(0).strip()
            
            return result
        except Exception as e:
            logger.error(f"Error parsing header: {e}")
            return result
    
    async def _get_text(self, page: Page, selector: str) -> Optional[str]:
        """
        Get inner text of an element.
        
        Args:
            page (Page): Playwright page object.
            selector (str): CSS selector for the element.
            
        Returns:
            Optional[str]: Inner text of the element, or None if not found.
        """
        try:
            element = await page.query_selector(selector)
            if element:
                return await element.inner_text()
            return None
        except Exception as e:
            logger.debug(f"Error getting text for selector '{selector}': {e}")
            return None