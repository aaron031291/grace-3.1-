"""
File handler for extracting text from various file types.
Supports TXT, MD, PDF, DOCX, XLSX, and other text-based formats.
"""

import os
import logging
from pathlib import Path
from typing import Tuple, Optional
import mimetypes

logger = logging.getLogger(__name__)


class FileHandler:
    """Handles extraction of text from different file types."""
    
    SUPPORTED_TYPES = {
        '.txt': 'text/plain',
        '.md': 'text/markdown',
        '.pdf': 'application/pdf',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.doc': 'application/msword',
        '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        '.xls': 'application/vnd.ms-excel',
        '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        '.ppt': 'application/vnd.ms-powerpoint',
    }
    
    @staticmethod
    def get_file_type(file_path: str) -> Optional[str]:
        """Get file type from path."""
        ext = Path(file_path).suffix.lower()
        return FileHandler.SUPPORTED_TYPES.get(ext)
    
    @staticmethod
    def extract_text(file_path: str) -> Tuple[str, Optional[str]]:
        """
        Extract text from file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Tuple of (text_content, error_message)
            If successful, error_message is None
        """
        if not os.path.exists(file_path):
            return "", f"File not found: {file_path}"
        
        ext = Path(file_path).suffix.lower()
        
        if ext in ['.txt', '.md']:
            return FileHandler._extract_text_file(file_path)
        elif ext == '.pdf':
            return FileHandler._extract_pdf(file_path)
        elif ext in ['.docx', '.doc']:
            return FileHandler._extract_docx(file_path)
        elif ext in ['.xlsx', '.xls']:
            return FileHandler._extract_excel(file_path)
        elif ext in ['.pptx', '.ppt']:
            return FileHandler._extract_pptx(file_path)
        else:
            return "", f"Unsupported file type: {ext}"
    
    @staticmethod
    def _extract_text_file(file_path: str) -> Tuple[str, Optional[str]]:
        """Extract text from TXT or MD files."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return content, None
        except UnicodeDecodeError:
            try:
                with open(file_path, 'r', encoding='latin-1') as f:
                    content = f.read()
                return content, None
            except Exception as e:
                logger.error(f"Error reading text file {file_path}: {e}")
                return "", f"Error reading file: {str(e)}"
        except Exception as e:
            logger.error(f"Error reading text file {file_path}: {e}")
            return "", f"Error reading file: {str(e)}"
    
    @staticmethod
    def _extract_pdf(file_path: str) -> Tuple[str, Optional[str]]:
        """Extract text from PDF file."""
        try:
            import pdfplumber
            
            text_parts = []
            try:
                with pdfplumber.open(file_path) as pdf:
                    for page_num, page in enumerate(pdf.pages, 1):
                        text = page.extract_text()
                        if text:
                            # Add page marker for better chunking
                            text_parts.append(f"[Page {page_num}]\n{text}")
                        
                if not text_parts:
                    return "", "No text content found in PDF"
                
                return "\n\n".join(text_parts), None
            
            except Exception as e:
                logger.error(f"Error extracting PDF content: {e}")
                return "", f"Error extracting PDF: {str(e)}"
        
        except ImportError:
            logger.error("pdfplumber not installed")
            return "", "PDF support not available. Install pdfplumber."
        except Exception as e:
            logger.error(f"Error processing PDF {file_path}: {e}")
            return "", f"Error processing PDF: {str(e)}"

    @staticmethod
    def _extract_docx(file_path: str) -> Tuple[str, Optional[str]]:
        """Extract text from DOCX or DOC files."""
        try:
            from docx import Document
            
            doc = Document(file_path)
            text_parts = []
            
            for para in doc.paragraphs:
                if para.text.strip():
                    text_parts.append(para.text)
            
            # Also extract from tables if any
            for table in doc.tables:
                for row in table.rows:
                    row_text = []
                    for cell in row.cells:
                        row_text.append(cell.text)
                    if row_text:
                        text_parts.append(" | ".join(row_text))
            
            text = "\n\n".join(text_parts)
            
            if not text.strip():
                return "", "No text content found in DOCX"
            
            return text, None
        
        except ImportError:
            logger.error("python-docx not installed")
            return "", "DOCX support not available. Install python-docx."
        except Exception as e:
            logger.error(f"Error processing DOCX {file_path}: {e}")
            return "", f"Error processing DOCX: {str(e)}"

    @staticmethod
    def _extract_excel(file_path: str) -> Tuple[str, Optional[str]]:
        """Extract text from XLSX or XLS files."""
        try:
            import openpyxl
            
            wb = openpyxl.load_workbook(file_path, data_only=True)
            text_parts = []
            
            for sheet_name in wb.sheetnames:
                sheet = wb[sheet_name]
                text_parts.append(f"[Sheet: {sheet_name}]")
                
                for row in sheet.iter_rows(values_only=True):
                    row_text = []
                    for cell in row:
                        if cell is not None:
                            row_text.append(str(cell))
                    if row_text:
                        text_parts.append(" | ".join(row_text))
            
            text = "\n".join(text_parts)
            
            if not text.strip():
                return "", "No text content found in Excel file"
            
            return text, None
        
        except ImportError:
            logger.error("openpyxl not installed")
            return "", "Excel support not available. Install openpyxl."
        except Exception as e:
            logger.error(f"Error processing Excel {file_path}: {e}")
            return "", f"Error processing Excel: {str(e)}"

    @staticmethod
    def _extract_pptx(file_path: str) -> Tuple[str, Optional[str]]:
        """Extract text from PPTX or PPT files."""
        try:
            from pptx import Presentation
            
            prs = Presentation(file_path)
            text_parts = []
            
            for slide_num, slide in enumerate(prs.slides, 1):
                text_parts.append(f"[Slide {slide_num}]")
                
                for shape in slide.shapes:
                    if hasattr(shape, "text") and shape.text.strip():
                        text_parts.append(shape.text)
            
            text = "\n\n".join(text_parts)
            
            if not text.strip():
                return "", "No text content found in PowerPoint file"
            
            return text, None
        
        except ImportError:
            logger.error("python-pptx not installed")
            return "", "PowerPoint support not available. Install python-pptx."
        except Exception as e:
            logger.error(f"Error processing PowerPoint {file_path}: {e}")
            return "", f"Error processing PowerPoint: {str(e)}"


def extract_file_text(file_path: str) -> Tuple[str, Optional[str]]:
    """
    Extract text from a file.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Tuple of (text_content, error_message)
    """
    return FileHandler.extract_text(file_path)
