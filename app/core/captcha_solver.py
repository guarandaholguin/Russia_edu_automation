"""
Módulo para resolver CAPTCHAs del sitio Russia-Edu utilizando OCR y 2Captcha API.
"""

import os
import io
import time
import asyncio
import base64
import json
import requests
from typing import Optional, Tuple, Dict, Any
import tempfile
from PIL import Image, ImageEnhance, ImageFilter
import pytesseract
from pathlib import Path
import cv2
import numpy as np
import tkinter as tk
from tkinter import simpledialog
from PIL import ImageTk

from app.utils.logger import get_logger
from app.utils.exceptions import CaptchaError
from app.config import CAPTCHA_TIMEOUT, TWO_CAPTCHA_API_KEY

logger = get_logger()

class TwoCaptchaSolver:
    """Clase para resolver CAPTCHAs usando la API de 2Captcha."""
    
    def __init__(self, api_key: str):
        """
        Inicializar el solucionador de 2Captcha.
        
        Args:
            api_key (str): Clave API para 2Captcha.
        """
        self.api_key = api_key
        self.base_url = "https://2captcha.com/in.php"
        self.result_url = "https://2captcha.com/res.php"
        logger.info("2Captcha solver inicializado con clave API")
    
    async def solve_image_captcha(self, image_bytes: bytes, options: Optional[Dict[str, Any]] = None) -> str:
        """
        Enviar CAPTCHA a 2Captcha y obtener la solución.
        
        Args:
            image_bytes (bytes): Datos de la imagen CAPTCHA.
            options (Dict[str, Any], optional): Opciones adicionales para 2Captcha.
            
        Returns:
            str: Texto del CAPTCHA resuelto.
            
        Raises:
            CaptchaError: Si ocurre un error durante la resolución del CAPTCHA.
        """
        try:
            # Codificar la imagen en base64
            encoded_image = base64.b64encode(image_bytes).decode('utf-8')
            
            # Parámetros por defecto
            params = {
                'key': self.api_key,
                'method': 'base64',
                'body': encoded_image,
                'json': 1  # Solicitar respuesta en formato JSON
            }
            
            # Añadir opciones adicionales si se proporcionan
            if options:
                params.update(options)
            
            # Enviar CAPTCHA a 2Captcha
            response = await self._make_request(self.base_url, params)
            
            if response.get('status') != 1:
                raise CaptchaError(f"Error enviando CAPTCHA a 2Captcha: {response.get('request')}")
            
            captcha_id = response.get('request')
            logger.info(f"CAPTCHA enviado a 2Captcha. ID: {captcha_id}")
            
            # Esperar la solución
            solution = await self._get_captcha_solution(captcha_id)
            logger.info(f"CAPTCHA resuelto: {solution}")
            
            return solution
        
        except Exception as e:
            logger.error(f"Error resolviendo CAPTCHA con 2Captcha: {e}")
            raise CaptchaError(f"Error con 2Captcha: {str(e)}")
    
    async def _make_request(self, url: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Realizar una solicitud HTTP a la API de 2Captcha.
        
        Args:
            url (str): URL de la API.
            params (Dict[str, Any]): Parámetros de la solicitud.
            
        Returns:
            Dict[str, Any]: Respuesta JSON de la API.
            
        Raises:
            CaptchaError: Si ocurre un error en la solicitud.
        """
        # Convertir la solicitud a una función asíncrona para no bloquear
        def _request():
            try:
                response = requests.post(url, data=params)
                response.raise_for_status()
                return response.json()
            except requests.RequestException as e:
                raise CaptchaError(f"Error de solicitud a 2Captcha: {str(e)}")
            except json.JSONDecodeError:
                raise CaptchaError("Error decodificando respuesta JSON de 2Captcha")
        
        # Ejecutar la solicitud en un thread
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, _request)
    
    async def _get_captcha_solution(self, captcha_id: str, max_attempts: int = 30, delay: int = 5) -> str:
        """
        Obtener la solución del CAPTCHA.
        
        Args:
            captcha_id (str): ID del CAPTCHA enviado.
            max_attempts (int, optional): Número máximo de intentos. Por defecto es 30.
            delay (int, optional): Retardo entre intentos en segundos. Por defecto es 5.
            
        Returns:
            str: Solución del CAPTCHA.
            
        Raises:
            CaptchaError: Si no se puede obtener la solución después de los intentos máximos.
        """
        params = {
            'key': self.api_key,
            'action': 'get',
            'id': captcha_id,
            'json': 1
        }
        
        for attempt in range(max_attempts):
            await asyncio.sleep(delay)
            
            response = await self._make_request(self.result_url, params)
            
            if response.get('status') == 1:
                return response.get('request')
            
            if response.get('request') != 'CAPCHA_NOT_READY':
                raise CaptchaError(f"Error obteniendo solución: {response.get('request')}")
            
            logger.debug(f"CAPTCHA no listo. Intento {attempt + 1}/{max_attempts}")
        
        raise CaptchaError(f"Tiempo de espera agotado después de {max_attempts} intentos")


class CaptchaSolver:
    """Clase para resolver CAPTCHAs del sitio web Russia-Edu."""
    
    def __init__(self, 
                 tesseract_path: Optional[str] = None, 
                 enable_manual_input: bool = True, 
                 always_manual: bool = False,
                 two_captcha_api_key: Optional[str] = None):
        """
        Inicializar el CaptchaSolver.
        
        Args:
            tesseract_path (str, optional): Ruta al ejecutable de Tesseract OCR.
                                           Si es None, usa la instalación por defecto.
            enable_manual_input (bool): Si se debe habilitar la entrada manual de CAPTCHA cuando falla OCR.
            always_manual (bool): Si siempre usar entrada manual de CAPTCHA, omitiendo OCR.
            two_captcha_api_key (str, optional): Clave API para 2Captcha.
        """
        self.enable_manual_input = enable_manual_input
        self.always_manual = always_manual
        self.manual_input_window = None
        self.captcha_cache = {}  # Cache para CAPTCHAs previamente resueltos
        
        # Inicializar solucionador de 2Captcha si se proporciona una clave API
        self.two_captcha_solver = None
        if two_captcha_api_key:
            self.two_captcha_solver = TwoCaptchaSolver(two_captcha_api_key)
            logger.info("2Captcha solver inicializado con clave API")
        
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
        
        # Comprobar si Tesseract está disponible
        try:
            pytesseract.get_tesseract_version()
            logger.info("Tesseract OCR está disponible.")
        except Exception as e:
            logger.warning(f"Tesseract OCR no encontrado: {e}. La resolución de CAPTCHA basada en OCR puede no funcionar.")
    
    async def solve_captcha(self, page) -> str:
        """
        Extraer y resolver el CAPTCHA de la página.
        
        Args:
            page: Objeto página de Playwright.
            
        Returns:
            str: Texto del CAPTCHA resuelto.
            
        Raises:
            CaptchaError: Si no se puede encontrar o resolver el CAPTCHA.
        """
        try:
            # Esperar a que la imagen del CAPTCHA sea visible
            captcha_selector = "#captcha_pic"
            await page.wait_for_selector(captcha_selector, state="visible", timeout=10000)
            
            # Obtener elemento de imagen CAPTCHA
            captcha_element = await page.query_selector(captcha_selector)
            if not captcha_element:
                raise CaptchaError("Elemento de imagen CAPTCHA no encontrado")
            
            # Tomar screenshot del CAPTCHA
            screenshot_bytes = await captcha_element.screenshot()
            
            # Guardar imagen CAPTCHA para análisis
            self._save_captcha_image(screenshot_bytes)
            
            # Verificar si tenemos este CAPTCHA en cache
            image_hash = hash(screenshot_bytes)
            if image_hash in self.captcha_cache:
                logger.info(f"CAPTCHA encontrado en cache: {self.captcha_cache[image_hash]}")
                return self.captcha_cache[image_hash]
            
            # Si always_manual está habilitado, ir directamente a entrada manual
            if self.always_manual and self.enable_manual_input:
                captcha_text = await self._get_manual_captcha_input(screenshot_bytes)
            else:
                # Intentar resolver con 2Captcha primero si está disponible
                captcha_text = ""
                if self.two_captcha_solver:
                    try:
                        logger.info("Intentando resolver CAPTCHA con 2Captcha")
                        captcha_text = await self.two_captcha_solver.solve_image_captcha(screenshot_bytes)
                    except CaptchaError as e:
                        logger.warning(f"2Captcha falló: {e}. Intentando métodos alternativos.")
                
                # Si 2Captcha falla o no está disponible, intentar OCR o entrada manual
                if not captcha_text or len(captcha_text) < 4:
                    if not self.always_manual:
                        # Intentar métodos automáticos de OCR
                        captcha_text = await self._try_multiple_processing_methods(screenshot_bytes)
                    
                    # Si los métodos automáticos fallan y la entrada manual está habilitada, preguntar al usuario
                    if (not captcha_text or len(captcha_text) < 4) and self.enable_manual_input:
                        captcha_text = await self._get_manual_captcha_input(screenshot_bytes)
            
            if not captcha_text or len(captcha_text) < 4:
                raise CaptchaError("Error resolviendo CAPTCHA: resultado vacío o demasiado corto")
            
            # Guardar en cache
            self.captcha_cache[image_hash] = captcha_text
            
            logger.info(f"CAPTCHA resuelto: {captcha_text}")
            return captcha_text
            
        except Exception as e:
            logger.error(f"Error resolviendo CAPTCHA: {e}")
            raise CaptchaError(f"Error resolviendo CAPTCHA: {str(e)}")
    
    def _save_captcha_image(self, image_bytes: bytes):
        """
        Guardar imagen CAPTCHA en disco para análisis.
        
        Args:
            image_bytes (bytes): Bytes de imagen raw.
        """
        try:
            # Crear directorio captcha si no existe
            captcha_dir = Path("captchas")
            captcha_dir.mkdir(exist_ok=True)
            
            # Generar nombre de archivo único con timestamp
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            random_suffix = os.urandom(4).hex()
            filename = f"captcha_{timestamp}_{random_suffix}.png"
            
            # Guardar imagen
            with open(captcha_dir / filename, "wb") as f:
                f.write(image_bytes)
            
            logger.info(f"Imagen CAPTCHA guardada en captchas/{filename}")
        except Exception as e:
            logger.error(f"Error guardando imagen CAPTCHA: {e}")
            # No lanzar la excepción para evitar bloquear el flujo principal
    
    async def _try_multiple_processing_methods(self, image_bytes: bytes) -> str:
        """
        Intentar múltiples métodos de procesamiento de imágenes para resolver el CAPTCHA.
        
        Args:
            image_bytes (bytes): Bytes de imagen raw.
            
        Returns:
            str: Mejor resultado OCR de todos los métodos.
        """
        # Generar un ID único para este captcha para guardar versiones procesadas
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        random_suffix = os.urandom(2).hex()
        captcha_id = f"{timestamp}_{random_suffix}"
        
        # Convertir bytes a imagen
        image = Image.open(io.BytesIO(image_bytes))
        
        # Probar diferentes métodos de procesamiento
        results = []
        
        # Método 1: Thresholding básico
        processed_image1 = self._preprocess_image_basic(np.array(image))
        text1 = self._apply_ocr(Image.fromarray(processed_image1))
        if text1 and len(text1) >= 4:
            results.append((text1, "basic"))
        self._save_processed_image(processed_image1, captcha_id, "basic")

        # Método 2: Thresholding adaptativo
        processed_image2 = self._preprocess_image_adaptive(np.array(image))
        text2 = self._apply_ocr(Image.fromarray(processed_image2))
        if text2 and len(text2) >= 4:
            results.append((text2, "adaptive"))
        self._save_processed_image(processed_image2, captcha_id, "adaptive")

        # Método 3: Contraste mejorado
        processed_image3 = self._preprocess_image_enhanced(image)
        text3 = self._apply_ocr(processed_image3)
        if text3 and len(text3) >= 4:
            results.append((text3, "enhanced"))
        self._save_processed_image(np.array(processed_image3), captcha_id, "enhanced")

        # Método 4: Reducción de ruido
        processed_image4 = self._preprocess_image_denoise(np.array(image))
        text4 = self._apply_ocr(Image.fromarray(processed_image4))
        if text4 and len(text4) >= 4:
            results.append((text4, "denoise"))
        self._save_processed_image(processed_image4, captcha_id, "denoise")
        
        # Probar diferentes configuraciones OCR
        ocr_configs = [
            ('--psm 7 --oem 3 -c tessedit_char_whitelist=abcdefghijklmnopqrstuvwxyz', 'psm7'),
            ('--psm 8 --oem 3 -c tessedit_char_whitelist=abcdefghijklmnopqrstuvwxyz', 'psm8'),
            ('--psm 6 --oem 3 -c tessedit_char_whitelist=abcdefghijklmnopqrstuvwxyz', 'psm6'),
            ('--psm 13 --oem 3 -c tessedit_char_whitelist=abcdefghijklmnopqrstuvwxyz', 'psm13')
        ]
        
        # Registrar todos los resultados para análisis
        all_results = []
        
        for config, config_name in ocr_configs:
            for img, img_type in [
                (processed_image1, "basic"), 
                (processed_image2, "adaptive"), 
                (processed_image3, "enhanced"), 
                (processed_image4, "denoise")
            ]:
                if isinstance(img, np.ndarray):
                    pil_img = Image.fromarray(img)
                else:
                    pil_img = img
                text = self._apply_ocr(pil_img, config)
                all_results.append((text, img_type, config_name))
                if text and len(text) >= 4:
                    results.append((text, f"{img_type}_{config_name}"))
        
        # Guardar resultados OCR en un archivo de registro
        self._log_ocr_results(captcha_id, all_results)
        
        # Elegir mejor resultado
        if results:
            # Priorizar resultados con longitud esperada (típicamente 5-6 caracteres)
            ideal_results = [r for r in results if 5 <= len(r[0]) <= 6]
            if ideal_results:
                logger.info(f"Resultado seleccionado: {ideal_results[0][0]} (método: {ideal_results[0][1]})")
                return ideal_results[0][0]
            
            logger.info(f"Resultado seleccionado: {results[0][0]} (método: {results[0][1]})")
            return results[0][0]
        
        return ""
    
    def _save_processed_image(self, image, captcha_id: str, method: str):
        """
        Guardar imagen CAPTCHA procesada para análisis.
        
        Args:
            image: Imagen procesada (array numpy o imagen PIL)
            captcha_id (str): ID único para este CAPTCHA
            method (str): Nombre del método de procesamiento
        """
        try:
            # Crear directorio si no existe
            captcha_dir = Path("captchas/processed")
            captcha_dir.mkdir(exist_ok=True, parents=True)
            
            # Convertir a PIL si es necesario
            if isinstance(image, np.ndarray):
                image_pil = Image.fromarray(image)
            else:
                image_pil = image
            
            # Guardar imagen
            filename = f"captcha_{captcha_id}_{method}.png"
            image_pil.save(captcha_dir / filename)
            
        except Exception as e:
            logger.error(f"Error guardando imagen CAPTCHA procesada: {e}")
    
    def _log_ocr_results(self, captcha_id: str, results):
        """
        Registrar resultados OCR para análisis.
        
        Args:
            captcha_id (str): ID único para este CAPTCHA
            results: Lista de tuplas (texto, método, config)
        """
        try:
            # Crear directorio si no existe
            log_dir = Path("captchas/logs")
            log_dir.mkdir(exist_ok=True, parents=True)
            
            # Crear archivo de registro
            filename = f"captcha_{captcha_id}_results.txt"
            with open(log_dir / filename, "w") as f:
                f.write(f"Resultados OCR para CAPTCHA {captcha_id}\n")
                f.write("=" * 50 + "\n\n")
                
                for text, method, config in results:
                    if text:
                        f.write(f"Método: {method} | Config: {config} | Resultado: {text}\n")
                    else:
                        f.write(f"Método: {method} | Config: {config} | Resultado: [VACÍO]\n")
        
        except Exception as e:
            logger.error(f"Error registrando resultados OCR: {e}")
    
    def _preprocess_image_basic(self, image):
        """
        Preprocesamiento básico de imagen.
        
        Args:
            image: Imagen OpenCV.
            
        Returns:
            Imagen OpenCV después del preprocesamiento.
        """
        # Convertir a escala de grises
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Aplicar umbral para obtener imagen en blanco y negro
        _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY_INV)
        
        # Eliminar ruido
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        opening = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=1)
        
        # Dilatar para conectar partes rotas
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        dilated = cv2.dilate(opening, kernel, iterations=1)
        
        # Invertir de vuelta para OCR
        result = cv2.bitwise_not(dilated)
        
        return result
    
    def _preprocess_image_adaptive(self, image):
        """
        Preprocesamiento con umbral adaptativo.
        
        Args:
            image: Imagen OpenCV.
            
        Returns:
            Imagen OpenCV después del preprocesamiento.
        """
        # Convertir a escala de grises
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Aplicar desenfoque gaussiano
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # Aplicar umbral adaptativo
        thresh = cv2.adaptiveThreshold(
            blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY_INV, 11, 2
        )
        
        # Eliminar ruido
        kernel = np.ones((1, 1), np.uint8)
        opening = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=1)
        
        # Dilatar para conectar partes rotas
        kernel = np.ones((2, 2), np.uint8)
        dilated = cv2.dilate(opening, kernel, iterations=1)
        
        # Invertir de vuelta para OCR
        result = cv2.bitwise_not(dilated)
        
        return result
    
    def _preprocess_image_enhanced(self, image):
        """
        Preprocesamiento con mejora de contraste.
        
        Args:
            image: Imagen PIL.
            
        Returns:
            Imagen PIL después del preprocesamiento.
        """
        # Convertir a escala de grises
        gray = image.convert('L')
        
        # Mejorar contraste
        enhancer = ImageEnhance.Contrast(gray)
        enhanced = enhancer.enhance(3.0)  # Aumenta el contraste
        
        # Mejorar nitidez
        enhancer = ImageEnhance.Sharpness(enhanced)
        sharpened = enhancer.enhance(3.0)  # Aumenta la nitidez
        
        # Aplicar filtro de mejora de bordes
        edge_enhanced = sharpened.filter(ImageFilter.EDGE_ENHANCE_MORE)  # Mayor mejora de bordes
        
        return edge_enhanced
    
    def _preprocess_image_denoise(self, image):
        """
        Preprocesamiento con reducción de ruido.
        
        Args:
            image: Imagen OpenCV.
            
        Returns:
            Imagen OpenCV después del preprocesamiento.
        """
        # Convertir a escala de grises
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Aplicar reducción de ruido
        denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
        
        # Aplicar umbral binario
        _, thresh = cv2.threshold(denoised, 127, 255, cv2.THRESH_BINARY_INV)
        
        # Dilatar para conectar partes rotas
        kernel = np.ones((2, 2), np.uint8)
        dilated = cv2.dilate(thresh, kernel, iterations=1)
        
        # Invertir de vuelta para OCR
        result = cv2.bitwise_not(dilated)
        
        return result
    
    def _apply_ocr(self, image, config='--psm 8 --oem 3 -c tessedit_char_whitelist=abcdefghijklmnopqrstuvwxyz'):
        """
        Aplicar OCR a la imagen.
        
        Args:
            image: Imagen PIL.
            config (str): Configuración de Tesseract.
            
        Returns:
            str: Texto extraído.
        """
        # Usar OCR para extraer texto
        try:
            text = pytesseract.image_to_string(image, config=config)
            
            # Limpiar texto
            cleaned = self._clean_text(text)
            return cleaned
        except Exception as e:
            logger.error(f"Error OCR: {e}")
            return ""
    
    def _clean_text(self, text: str) -> str:
        """
        Limpiar el resultado OCR.
        
        Args:
            text (str): Texto OCR sin procesar.
            
        Returns:
            str: Texto limpio.
        """
        # Eliminar espacios en blanco y caracteres especiales
        cleaned = ''.join(c for c in text if c.isalnum()).strip().lower()
        return cleaned
    
    async def _get_manual_captcha_input(self, image_bytes: bytes) -> str:
        """
        Mostrar imagen CAPTCHA al usuario y obtener entrada manual.
        
        Args:
            image_bytes (bytes): Bytes de la imagen CAPTCHA.
            
        Returns:
            str: Entrada de usuario para CAPTCHA.
        """
        # Crear un archivo temporal para la imagen
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp_file:
            tmp_file.write(image_bytes)
            tmp_file_path = tmp_file.name
        
        # Función para obtener entrada en el hilo principal
        def get_input_from_user():
            try:
                # Crear ventana root
                root = tk.Tk()
                root.withdraw()  # Ocultar la ventana root
                
                # Mostrar la imagen
                img = Image.open(tmp_file_path)
                img = img.resize((img.width * 2, img.height * 2), Image.Resampling.LANCZOS)  # Hacerla más grande
                
                # Crear una nueva ventana para mostrar la imagen
                img_window = tk.Toplevel(root)
                img_window.title("Se requiere entrada de CAPTCHA")
                img_window.resizable(False, False)
                
                # Convertir imagen PIL a Tkinter PhotoImage
                photo = ImageTk.PhotoImage(img)
                
                # Crear una etiqueta para la imagen
                img_label = tk.Label(img_window, image=photo)
                img_label.image = photo  # Mantener una referencia
                img_label.pack(padx=10, pady=10)
                
                # Crear una etiqueta con instrucciones
                instructions = tk.Label(
                    img_window, 
                    text="Por favor, introduce el texto de la imagen CAPTCHA.\nIntroduce el texto en minúsculas.",
                    font=("Arial", 10)
                )
                instructions.pack(padx=10, pady=(0, 10))
                
                # Crear entrada para input
                entry_var = tk.StringVar()
                entry = tk.Entry(img_window, textvariable=entry_var, font=("Arial", 12), width=15)
                entry.pack(padx=10, pady=(0, 10))
                entry.focus_set()
                
                # Variable de resultado
                result = [None]
                
                # Función para enviar entrada
                def submit_input():
                    result[0] = entry_var.get().lower()
                    img_window.destroy()
                    root.destroy()
                
                # Crear botón de envío
                submit_btn = tk.Button(img_window, text="Enviar", command=submit_input)
                submit_btn.pack(padx=10, pady=(0, 10))
                
                # Vincular tecla Enter para enviar
                entry.bind("<Return>", lambda event: submit_input())
                
                # Centrar la ventana
                img_window.update_idletasks()
                width = img_window.winfo_width()
                height = img_window.winfo_height()
                x = (img_window.winfo_screenwidth() // 2) - (width // 2)
                y = (img_window.winfo_screenheight() // 2) - (height // 2)
                img_window.geometry(f'+{x}+{y}')
                
                # Esperar entrada de usuario
                root.mainloop()
                
                return result[0]
                
            except Exception as e:
                logger.error(f"Error mostrando imagen CAPTCHA: {e}")
                return None
            finally:
                # Limpiar archivo temporal
                try:
                    os.unlink(tmp_file_path)
                except:
                    pass
        
        # Crear bucle de eventos y ejecutar get_input_from_user en el hilo principal
        loop = asyncio.get_running_loop()
        user_input = await loop.run_in_executor(None, get_input_from_user)
        
        if user_input:
            logger.info(f"Usuario introdujo CAPTCHA: {user_input}")
            return user_input
        
        return ""