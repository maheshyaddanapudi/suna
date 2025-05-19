"""
OCR tool for extracting text from images within the sandbox.
"""

import io
import base64
import tempfile
import os
from typing import Optional, Dict, Any

from agentpress.tool import ToolResult, openapi_schema, xml_schema
from sandbox.tool_base import SandboxToolsBase
from agentpress.thread_manager import ThreadManager
from utils.logger import logger

class SandboxOCRTool(SandboxToolsBase):
    """Tool for performing OCR on images within the sandbox."""

    def __init__(self, project_id: str, thread_id: str, thread_manager: ThreadManager):
        super().__init__(project_id, thread_manager)
        self.thread_id = thread_id
        self.thread_manager = thread_manager

    @openapi_schema({
        "type": "function",
        "function": {
            "name": "extract_text_from_image",
            "description": "Extracts text from an image using OCR (Optical Character Recognition).",
            "parameters": {
                "type": "object",
                "properties": {
                    "image_path": {
                        "type": "string",
                        "description": "Path to the image file within the workspace"
                    },
                    "language": {
                        "type": "string",
                        "description": "Language code for OCR (e.g., 'eng' for English, 'fra' for French)",
                        "default": "eng"
                    },
                    "output_path": {
                        "type": "string",
                        "description": "Optional path to save the extracted text to a file"
                    },
                    "preprocessing": {
                        "type": "string",
                        "description": "Preprocessing options: none, grayscale, threshold, adaptive",
                        "enum": ["none", "grayscale", "threshold", "adaptive"],
                        "default": "none"
                    }
                },
                "required": ["image_path"]
            }
        }
    })
    @xml_schema(
        tag_name="extract-text-from-image",
        mappings=[
            {"param_name": "image_path", "node_type": "attribute", "path": "."},
            {"param_name": "language", "node_type": "attribute", "path": "."},
            {"param_name": "output_path", "node_type": "attribute", "path": "."},
            {"param_name": "preprocessing", "node_type": "attribute", "path": "."}
        ],
        example='''
        <!-- Example: Extract text from a scanned document -->
        <extract-text-from-image image_path="documents/scan.jpg" language="eng" output_path="documents/scan_text.txt" preprocessing="adaptive"></extract-text-from-image>
        '''
    )
    async def extract_text_from_image(self, 
                                     image_path: str, 
                                     language: str = "eng",
                                     output_path: Optional[str] = None,
                                     preprocessing: str = "none") -> ToolResult:
        """Extracts text from an image using OCR."""
        try:
            # Ensure sandbox is initialized
            await self._ensure_sandbox()
            
            # Install required packages if not already installed
            await self._ensure_ocr_packages()
            
            # Clean and construct full path
            cleaned_path = self.clean_path(image_path)
            full_path = f"{self.workspace_path}/{cleaned_path}"
            
            # Check if file exists
            try:
                file_info = self.sandbox.fs.get_file_info(full_path)
                if file_info.is_dir:
                    return self.fail_response(f"Path '{cleaned_path}' is a directory, not an image file.")
            except Exception as e:
                return self.fail_response(f"Image file not found at path: '{cleaned_path}'")
            
            # Create Python script for OCR
            script_content = self._generate_ocr_script(
                image_path=full_path,
                language=language,
                preprocessing=preprocessing,
                output_path=output_path
            )
            
            # Save script to temporary file
            script_path = "/tmp/ocr_script.py"
            self.sandbox.fs.upload_file(script_path, script_content.encode('utf-8'))
            
            # Execute the script
            result = await self.sandbox.exec.start(
                command=f"python3 {script_path}"
            )
            
            # Wait for completion
            await result.wait()
            
            # Check if execution was successful
            if result.exit_code != 0:
                error_output = await result.get_output()
                return self.fail_response(f"Failed to perform OCR: {error_output}")
            
            # Get the output
            output = await result.get_output()
            
            # If output path was specified, read the saved file
            if output_path:
                cleaned_output_path = self.clean_path(output_path)
                full_output_path = f"{self.workspace_path}/{cleaned_output_path}"
                
                try:
                    extracted_text = self.sandbox.fs.download_file(full_output_path).decode('utf-8')
                    return self.success_response(f"Text extracted and saved to {cleaned_output_path}:\n\n{extracted_text}")
                except Exception as e:
                    return self.fail_response(f"Failed to read extracted text from {cleaned_output_path}: {str(e)}")
            else:
                # Parse the output to get the extracted text
                extracted_text = output.strip()
                return self.success_response(extracted_text)
            
        except Exception as e:
            logger.error(f"Error performing OCR: {str(e)}", exc_info=True)
            return self.fail_response(f"Failed to perform OCR: {str(e)}")
    
    async def _ensure_ocr_packages(self):
        """Ensure required OCR packages are installed."""
        packages = ["pytesseract", "pillow", "numpy", "opencv-python"]
        
        # Check if packages are already installed
        for package in packages:
            result = await self.sandbox.exec.start(
                command=f"python3 -c 'import {package.replace('-', '_')}' 2>/dev/null && echo 'installed' || echo 'not installed'"
            )
            await result.wait()
            output = await result.get_output()
            
            if "not installed" in output:
                # Install the package
                install_result = await self.sandbox.exec.start(
                    command=f"pip install {package} --quiet"
                )
                await install_result.wait()
                
                if install_result.exit_code != 0:
                    install_error = await install_result.get_output()
                    logger.warning(f"Failed to install {package}: {install_error}")
        
        # Install tesseract-ocr if not already installed
        result = await self.sandbox.exec.start(
            command="which tesseract >/dev/null 2>&1 && echo 'installed' || echo 'not installed'"
        )
        await result.wait()
        output = await result.get_output()
        
        if "not installed" in output:
            # Install tesseract-ocr
            install_result = await self.sandbox.exec.start(
                command="apt-get update && apt-get install -y tesseract-ocr"
            )
            await install_result.wait()
            
            if install_result.exit_code != 0:
                install_error = await install_result.get_output()
                logger.warning(f"Failed to install tesseract-ocr: {install_error}")
    
    def _generate_ocr_script(self, 
                            image_path: str, 
                            language: str,
                            preprocessing: str,
                            output_path: Optional[str] = None) -> str:
        """Generate Python script for OCR."""
        script = f"""
import pytesseract
from PIL import Image
import cv2
import numpy as np
import os

# Path to the image
image_path = "{image_path}"

# Load the image
image = cv2.imread(image_path)
if image is None:
    print(f"Failed to load image: {{image_path}}")
    exit(1)

# Preprocess the image
if "{preprocessing}" == "grayscale":
    # Convert to grayscale
    image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
elif "{preprocessing}" == "threshold":
    # Convert to grayscale and apply threshold
    image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    _, image = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
elif "{preprocessing}" == "adaptive":
    # Convert to grayscale and apply adaptive threshold
    image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    image = cv2.adaptiveThreshold(image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)

# Save preprocessed image temporarily
cv2.imwrite("/tmp/preprocessed_image.png", image)

# Perform OCR
extracted_text = pytesseract.image_to_string(Image.open("/tmp/preprocessed_image.png"), lang="{language}")

# Print the extracted text
print(extracted_text)

# Save to file if output path is specified
"""
        
        if output_path:
            script += f"""
# Create directory if it doesn't exist
os.makedirs(os.path.dirname("{output_path}"), exist_ok=True)

# Save extracted text to file
with open("{output_path}", "w") as f:
    f.write(extracted_text)
"""
        
        return script
    
    def success_response(self, message: str) -> ToolResult:
        """Create a success response."""
        return ToolResult(output=message)
    
    def fail_response(self, error: str) -> ToolResult:
        """Create a failure response."""
        return ToolResult(error=error)
