"""
Document Processing tool for extracting structured data from documents within the sandbox.
"""

import io
import base64
import tempfile
import os
import json
from typing import Optional, Dict, Any, List

from agentpress.tool import ToolResult, openapi_schema, xml_schema
from sandbox.tool_base import SandboxToolsBase
from agentpress.thread_manager import ThreadManager
from utils.logger import logger

class SandboxDocumentProcessingTool(SandboxToolsBase):
    """Tool for extracting structured data from documents within the sandbox."""

    def __init__(self, project_id: str, thread_id: str, thread_manager: ThreadManager):
        super().__init__(project_id, thread_manager)
        self.thread_id = thread_id
        self.thread_manager = thread_manager

    @openapi_schema({
        "type": "function",
        "function": {
            "name": "extract_document_data",
            "description": "Extracts structured data from documents (PDF, images, etc.) using document processing techniques.",
            "parameters": {
                "type": "object",
                "properties": {
                    "document_path": {
                        "type": "string",
                        "description": "Path to the document file within the workspace"
                    },
                    "extraction_type": {
                        "type": "string",
                        "description": "Type of extraction to perform",
                        "enum": ["text", "tables", "forms", "entities", "full"],
                        "default": "full"
                    },
                    "output_format": {
                        "type": "string",
                        "description": "Format for the extracted data",
                        "enum": ["json", "csv", "txt", "markdown"],
                        "default": "json"
                    },
                    "output_path": {
                        "type": "string",
                        "description": "Optional path to save the extracted data to a file"
                    },
                    "page_range": {
                        "type": "string",
                        "description": "Optional page range to process (e.g., '1-5', '1,3,5')",
                        "default": "all"
                    }
                },
                "required": ["document_path"]
            }
        }
    })
    @xml_schema(
        tag_name="extract-document-data",
        mappings=[
            {"param_name": "document_path", "node_type": "attribute", "path": "."},
            {"param_name": "extraction_type", "node_type": "attribute", "path": "."},
            {"param_name": "output_format", "node_type": "attribute", "path": "."},
            {"param_name": "output_path", "node_type": "attribute", "path": "."},
            {"param_name": "page_range", "node_type": "attribute", "path": "."}
        ],
        example='''
        <!-- Example: Extract data from an invoice PDF -->
        <extract-document-data document_path="invoices/invoice_123.pdf" extraction_type="forms" output_format="json" output_path="processed/invoice_123.json"></extract-document-data>
        '''
    )
    async def extract_document_data(self, 
                                  document_path: str, 
                                  extraction_type: str = "full",
                                  output_format: str = "json",
                                  output_path: Optional[str] = None,
                                  page_range: str = "all") -> ToolResult:
        """Extracts structured data from documents."""
        try:
            # Ensure sandbox is initialized
            await self._ensure_sandbox()
            
            # Install required packages if not already installed
            await self._ensure_document_processing_packages()
            
            # Clean and construct full path
            cleaned_path = self.clean_path(document_path)
            full_path = f"{self.workspace_path}/{cleaned_path}"
            
            # Check if file exists
            try:
                file_info = self.sandbox.fs.get_file_info(full_path)
                if file_info.is_dir:
                    return self.fail_response(f"Path '{cleaned_path}' is a directory, not a document file.")
            except Exception as e:
                return self.fail_response(f"Document file not found at path: '{cleaned_path}'")
            
            # Create Python script for document processing
            script_content = self._generate_document_processing_script(
                document_path=full_path,
                extraction_type=extraction_type,
                output_format=output_format,
                page_range=page_range,
                output_path=output_path
            )
            
            # Save script to temporary file
            script_path = "/tmp/document_processing_script.py"
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
                return self.fail_response(f"Failed to process document: {error_output}")
            
            # Get the output
            output = await result.get_output()
            
            # If output path was specified, read the saved file
            if output_path:
                cleaned_output_path = self.clean_path(output_path)
                full_output_path = f"{self.workspace_path}/{cleaned_output_path}"
                
                try:
                    extracted_data = self.sandbox.fs.download_file(full_output_path).decode('utf-8')
                    
                    # Format the response based on the output format
                    if output_format == "json":
                        # Pretty-print JSON for better readability
                        try:
                            data = json.loads(extracted_data)
                            extracted_data = json.dumps(data, indent=2)
                        except:
                            pass
                    
                    return self.success_response(f"Document data extracted and saved to {cleaned_output_path}:\n\n{extracted_data}")
                except Exception as e:
                    return self.fail_response(f"Failed to read extracted data from {cleaned_output_path}: {str(e)}")
            else:
                # Parse the output to get the extracted data
                extracted_data = output.strip()
                return self.success_response(extracted_data)
            
        except Exception as e:
            logger.error(f"Error processing document: {str(e)}", exc_info=True)
            return self.fail_response(f"Failed to process document: {str(e)}")
    
    async def _ensure_document_processing_packages(self):
        """Ensure required document processing packages are installed."""
        packages = ["pdfplumber", "pytesseract", "pillow", "pandas", "tabula-py", "spacy"]
        
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
        
        # Install Java for tabula-py if not already installed
        result = await self.sandbox.exec.start(
            command="which java >/dev/null 2>&1 && echo 'installed' || echo 'not installed'"
        )
        await result.wait()
        output = await result.get_output()
        
        if "not installed" in output:
            # Install Java
            install_result = await self.sandbox.exec.start(
                command="apt-get update && apt-get install -y default-jre"
            )
            await install_result.wait()
            
            if install_result.exit_code != 0:
                install_error = await install_result.get_output()
                logger.warning(f"Failed to install Java: {install_error}")
        
        # Download spaCy model if not already installed
        result = await self.sandbox.exec.start(
            command="python3 -c 'import spacy; spacy.load(\"en_core_web_sm\")' 2>/dev/null && echo 'installed' || echo 'not installed'"
        )
        await result.wait()
        output = await result.get_output()
        
        if "not installed" in output:
            # Install spaCy model
            install_result = await self.sandbox.exec.start(
                command="python3 -m spacy download en_core_web_sm"
            )
            await install_result.wait()
            
            if install_result.exit_code != 0:
                install_error = await install_result.get_output()
                logger.warning(f"Failed to install spaCy model: {install_error}")
    
    def _generate_document_processing_script(self, 
                                           document_path: str, 
                                           extraction_type: str,
                                           output_format: str,
                                           page_range: str,
                                           output_path: Optional[str] = None) -> str:
        """Generate Python script for document processing."""
        script = f"""
import pdfplumber
import pytesseract
from PIL import Image
import pandas as pd
import tabula
import spacy
import os
import json
import re
import io
import sys
from pathlib import Path

# Path to the document
document_path = "{document_path}"
extraction_type = "{extraction_type}"
output_format = "{output_format}"
page_range = "{page_range}"

# Parse page range
pages = None
if page_range != "all":
    try:
        if "-" in page_range:
            start, end = map(int, page_range.split("-"))
            pages = list(range(start - 1, end))  # Convert to 0-based indexing
        elif "," in page_range:
            pages = [int(p) - 1 for p in page_range.split(",")]  # Convert to 0-based indexing
        else:
            pages = [int(page_range) - 1]  # Convert to 0-based indexing
    except ValueError:
        print(f"Invalid page range: {{page_range}}")
        sys.exit(1)

# Check file extension
file_ext = Path(document_path).suffix.lower()
is_pdf = file_ext == ".pdf"
is_image = file_ext in [".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp"]

# Initialize result dictionary
result = {{
    "metadata": {{
        "filename": os.path.basename(document_path),
        "extraction_type": extraction_type,
        "page_range": page_range
    }},
    "content": {{}}
}}

# Process based on file type and extraction type
try:
    if is_pdf:
        # Process PDF
        with pdfplumber.open(document_path) as pdf:
            # Get total pages
            total_pages = len(pdf.pages)
            result["metadata"]["total_pages"] = total_pages
            
            # Determine which pages to process
            if pages is None:
                pages = list(range(total_pages))
            
            # Extract based on extraction type
            if extraction_type in ["text", "full"]:
                # Extract text
                text_content = []
                for i in pages:
                    if i < total_pages:
                        page = pdf.pages[i]
                        text_content.append({{
                            "page": i + 1,
                            "text": page.extract_text() or ""
                        }})
                result["content"]["text"] = text_content
            
            if extraction_type in ["tables", "full"]:
                # Extract tables using tabula
                tables = tabula.read_pdf(document_path, pages=page_range if page_range != "all" else "all")
                table_content = []
                for i, table in enumerate(tables):
                    table_content.append({{
                        "table_id": i + 1,
                        "data": table.to_dict(orient="records")
                    }})
                result["content"]["tables"] = table_content
            
            if extraction_type in ["forms", "full"]:
                # Extract form fields
                form_content = []
                for i in pages:
                    if i < total_pages:
                        page = pdf.pages[i]
                        fields = []
                        # Look for form-like structures
                        text = page.extract_text() or ""
                        # Simple heuristic: look for lines with ":" or similar patterns
                        for line in text.split("\\n"):
                            if ":" in line:
                                key, value = line.split(":", 1)
                                fields.append({{
                                    "field": key.strip(),
                                    "value": value.strip()
                                }})
                        form_content.append({{
                            "page": i + 1,
                            "fields": fields
                        }})
                result["content"]["forms"] = form_content
    
    elif is_image:
        # Process image
        image = Image.open(document_path)
        
        if extraction_type in ["text", "full"]:
            # Extract text using OCR
            text = pytesseract.image_to_string(image)
            result["content"]["text"] = [{{
                "page": 1,
                "text": text
            }}]
        
        if extraction_type in ["entities", "full"]:
            # Extract entities using spaCy
            nlp = spacy.load("en_core_web_sm")
            text = pytesseract.image_to_string(image)
            doc = nlp(text)
            entities = []
            for ent in doc.ents:
                entities.append({{
                    "text": ent.text,
                    "label": ent.label_,
                    "start": ent.start_char,
                    "end": ent.end_char
                }})
            result["content"]["entities"] = entities
    
    else:
        # Unsupported file type
        print(f"Unsupported file type: {{file_ext}}")
        sys.exit(1)
    
    # Add entity extraction for PDFs if requested
    if is_pdf and extraction_type in ["entities", "full"]:
        # Extract entities using spaCy
        nlp = spacy.load("en_core_web_sm")
        all_text = ""
        if "text" in result["content"]:
            for page in result["content"]["text"]:
                all_text += page["text"] + "\\n"
        else:
            with pdfplumber.open(document_path) as pdf:
                for i in pages:
                    if i < len(pdf.pages):
                        page = pdf.pages[i]
                        all_text += (page.extract_text() or "") + "\\n"
        
        doc = nlp(all_text)
        entities = []
        for ent in doc.ents:
            entities.append({{
                "text": ent.text,
                "label": ent.label_,
                "start": ent.start_char,
                "end": ent.end_char
            }})
        result["content"]["entities"] = entities
    
    # Format output based on requested format
    if output_format == "json":
        output_data = json.dumps(result, indent=2)
    elif output_format == "csv":
        # Convert to CSV (only works well for tables)
        if "tables" in result["content"] and result["content"]["tables"]:
            dfs = []
            for table in result["content"]["tables"]:
                df = pd.DataFrame(table["data"])
                dfs.append(df)
            if dfs:
                output_data = pd.concat(dfs).to_csv(index=False)
            else:
                output_data = "No table data found"
        elif "forms" in result["content"] and result["content"]["forms"]:
            # Convert forms to CSV
            rows = []
            for page in result["content"]["forms"]:
                for field in page["fields"]:
                    rows.append({{
                        "page": page["page"],
                        "field": field["field"],
                        "value": field["value"]
                    }})
            if rows:
                output_data = pd.DataFrame(rows).to_csv(index=False)
            else:
                output_data = "No form data found"
        else:
            output_data = "No suitable data for CSV format"
    elif output_format == "markdown":
        # Convert to Markdown
        md_parts = []
        md_parts.append(f"# Document: {{result['metadata']['filename']}}\\n")
        
        if "text" in result["content"]:
            md_parts.append("## Text Content\\n")
            for page in result["content"]["text"]:
                md_parts.append(f"### Page {{page['page']}}\\n")
                md_parts.append(page["text"] + "\\n\\n")
        
        if "tables" in result["content"] and result["content"]["tables"]:
            md_parts.append("## Tables\\n")
            for table in result["content"]["tables"]:
                md_parts.append(f"### Table {{table['table_id']}}\\n")
                df = pd.DataFrame(table["data"])
                md_parts.append(df.to_markdown() + "\\n\\n")
        
        if "forms" in result["content"] and result["content"]["forms"]:
            md_parts.append("## Form Fields\\n")
            for page in result["content"]["forms"]:
                md_parts.append(f"### Page {{page['page']}}\\n")
                for field in page["fields"]:
                    md_parts.append(f"- **{{field['field']}}**: {{field['value']}}\\n")
                md_parts.append("\\n")
        
        if "entities" in result["content"] and result["content"]["entities"]:
            md_parts.append("## Entities\\n")
            for entity in result["content"]["entities"]:
                md_parts.append(f"- **{{entity['text']}}** ({{entity['label']}})\\n")
        
        output_data = "".join(md_parts)
    else:  # txt
        # Convert to plain text
        txt_parts = []
        txt_parts.append(f"Document: {{result['metadata']['filename']}}\\n")
        txt_parts.append(f"Extraction Type: {{result['metadata']['extraction_type']}}\\n")
        txt_parts.append(f"Page Range: {{result['metadata']['page_range']}}\\n\\n")
        
        if "text" in result["content"]:
            txt_parts.append("TEXT CONTENT:\\n")
            for page in result["content"]["text"]:
                txt_parts.append(f"Page {{page['page']}}:\\n")
                txt_parts.append(page["text"] + "\\n\\n")
        
        if "tables" in result["content"] and result["content"]["tables"]:
            txt_parts.append("TABLES:\\n")
            for table in result["content"]["tables"]:
                txt_parts.append(f"Table {{table['table_id']}}:\\n")
                df = pd.DataFrame(table["data"])
                txt_parts.append(df.to_string() + "\\n\\n")
        
        if "forms" in result["content"] and result["content"]["forms"]:
            txt_parts.append("FORM FIELDS:\\n")
            for page in result["content"]["forms"]:
                txt_parts.append(f"Page {{page['page']}}:\\n")
                for field in page["fields"]:
                    txt_parts.append(f"{{field['field']}}: {{field['value']}}\\n")
                txt_parts.append("\\n")
        
        if "entities" in result["content"] and result["content"]["entities"]:
            txt_parts.append("ENTITIES:\\n")
            for entity in result["content"]["entities"]:
                txt_parts.append(f"{{entity['text']}} ({{entity['label']}})\\n")
        
        output_data = "".join(txt_parts)
    
    # Print the output
    print(output_data)
    
    # Save to file if output path is specified
"""
        
        if output_path:
            script += f"""
# Create directory if it doesn't exist
os.makedirs(os.path.dirname("{output_path}"), exist_ok=True)

# Save extracted data to file
with open("{output_path}", "w") as f:
    f.write(output_data)
"""
        
        script += """
except Exception as e:
    print(f"Error processing document: {str(e)}")
    sys.exit(1)
"""
        
        return script
    
    def success_response(self, message: str) -> ToolResult:
        """Create a success response."""
        return ToolResult(output=message)
    
    def fail_response(self, error: str) -> ToolResult:
        """Create a failure response."""
        return ToolResult(error=error)
