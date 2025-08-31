"""
PDF processing utilities
"""
import tempfile
import os
from typing import List
import pdfplumber
from ..utils.exceptions import PDFProcessingError, FileSizeError, InvalidFileError


class PDFProcessor:
    """Handles PDF text extraction and validation"""
    
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    
    @classmethod
    def extract_text_from_pdf(cls, pdf_file) -> List[str]:
        """
        Extract text lines from PDF file
        
        Args:
            pdf_file: Streamlit uploaded file object
            
        Returns:
            List of text lines from the PDF
            
        Raises:
            FileSizeError: If file exceeds size limit
            InvalidFileError: If file is corrupted or empty
            PDFProcessingError: For other processing errors
        """
        if pdf_file.size > cls.MAX_FILE_SIZE:
            raise FileSizeError("File too large. Maximum size is 50MB.")
        
        lines = []
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(pdf_file.getvalue())
            tmp_path = tmp_file.name
        
        try:
            with pdfplumber.open(tmp_path) as pdf:
                if not pdf.pages:
                    raise InvalidFileError("PDF file appears to be empty or corrupted.")
                
                for page_num, page in enumerate(pdf.pages, 1):
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            lines.extend(page_text.split("\n"))
                    except Exception as e:
                        # Log warning but continue processing other pages
                        print(f"Warning: Could not extract text from page {page_num}: {e}")
                        continue
                        
        except Exception as e:
            raise PDFProcessingError(f"Error reading PDF file: {e}")
        finally:
            # Clean up temporary file
            try:
                os.unlink(tmp_path)
            except OSError:
                pass  # File might already be deleted
        
        if not lines:
            raise InvalidFileError("No text could be extracted from the PDF.")
        
        return lines
    
    @staticmethod
    def validate_pdf_structure(lines: List[str]) -> None:
        """
        Validate that PDF has the expected structure
        
        Args:
            lines: List of text lines from PDF
            
        Raises:
            InvalidFileError: If PDF structure is invalid
        """
        if len(lines) < 3:
            raise InvalidFileError("PDF doesn't contain enough data. Expected at least 3 lines.")
        
        # Basic validation - could be extended
        if not any("C/I" in line or "C/O" in line for line in lines):
            raise InvalidFileError("PDF doesn't appear to be a valid roster file. Missing C/I or C/O markers.")