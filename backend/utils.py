import os
import base64
import io
from typing import Optional
import logging

logger = logging.getLogger(__name__)

def extract_text_from_pdf(pdf_content: bytes) -> Optional[str]:
    """
    Extract text from PDF content bytes.
    
    Args:
        pdf_content: The PDF file content as bytes
        
    Returns:
        The extracted text or None if extraction failed
    """
    try:
        # Import here to avoid dependency issues if PyPDF2 is not installed
        import PyPDF2
        
        # Create a file-like object from the bytes
        pdf_file = io.BytesIO(pdf_content)
        
        # Create a PDF reader object
        reader = PyPDF2.PdfReader(pdf_file)
        
        # Extract text from all pages
        text = ""
        for page_num in range(len(reader.pages)):
            page = reader.pages[page_num]
            text += page.extract_text() + "\n\n"
            
        if not text.strip():
            # If no text was extracted (e.g., scanned PDF), return a placeholder
            return "[PDF content could not be extracted - possibly a scanned document]"
            
        return text
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {str(e)}")
        return f"[Error extracting PDF content: {str(e)}]"
        
def encode_file_to_base64(file_path: str) -> Optional[str]:
    """
    Encode a file to base64 string.
    
    Args:
        file_path: The path to the file
        
    Returns:
        The base64 encoded string or None if encoding failed
    """
    try:
        with open(file_path, "rb") as file:
            return base64.b64encode(file.read()).decode("utf-8")
    except Exception as e:
        logger.error(f"Error encoding file to base64: {str(e)}")
        return None
