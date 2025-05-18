"""
Anthropic browser-use tool for interacting with web pages using Anthropic's Claude API.
"""

import json
import traceback
from typing import Optional, Dict, Any, List

from agentpress.tool import ToolResult, openapi_schema, xml_schema
from agentpress.thread_manager import ThreadManager
from sandbox.tool_base import SandboxToolsBase
from utils.logger import logger

import anthropic

class AnthropicBrowserTool(SandboxToolsBase):
    """Tool for browser automation using Anthropic's Claude API capabilities."""
    
    def __init__(self, project_id: str, thread_id: str, thread_manager: ThreadManager):
        super().__init__(project_id, thread_manager)
        self.thread_id = thread_id
        self.thread_manager = thread_manager
        self.anthropic_client = None
        self.current_url = None
        self.current_page_content = None
        self.current_page_title = None
        self.session_id = None
        
    async def _ensure_anthropic_client(self):
        """Ensure Anthropic client is initialized."""
        if self.anthropic_client is None:
            # Get API key from environment
            try:
                # Ensure sandbox is initialized
                await self._ensure_sandbox()
                
                # Get API key from environment
                result = self.sandbox.process.exec("echo $ANTHROPIC_API_KEY", timeout=5)
                api_key = result.result.strip()
                
                if not api_key:
                    # Try to get from config
                    from utils.config import config
                    api_key = config.ANTHROPIC_API_KEY
                
                if not api_key:
                    return self.fail_response("Anthropic API key not found. Please set ANTHROPIC_API_KEY environment variable.")
                
                # Initialize Anthropic client
                self.anthropic_client = anthropic.Anthropic(api_key=api_key)
                
                # Initialize session ID
                import uuid
                self.session_id = str(uuid.uuid4())
                
                return self.success_response("Anthropic client initialized successfully.")
            except Exception as e:
                logger.error(f"Error initializing Anthropic client: {str(e)}", exc_info=True)
                return self.fail_response(f"Failed to initialize Anthropic client: {str(e)}")
        
        return self.success_response("Anthropic client already initialized.")
    
    async def _execute_browser_action(self, action: str, params: Dict[str, Any] = None) -> ToolResult:
        """Execute a browser action using Anthropic's Claude API."""
        try:
            # Ensure Anthropic client is initialized
            client_result = await self._ensure_anthropic_client()
            if client_result.error:
                return client_result
            
            # Ensure sandbox is initialized
            await self._ensure_sandbox()
            
            # Prepare system prompt
            system_prompt = f"""You are a browser automation assistant that helps users interact with web pages.
Current action: {action}
Session ID: {self.session_id}
"""
            if self.current_url:
                system_prompt += f"Current URL: {self.current_url}\n"
            if self.current_page_title:
                system_prompt += f"Current page title: {self.current_page_title}\n"
            
            # Prepare user message
            user_message = f"Please perform the following browser action: {action}"
            if params:
                user_message += f"\nParameters: {json.dumps(params)}"
            if self.current_page_content:
                user_message += f"\n\nCurrent page content:\n{self.current_page_content}"
            
            # Call Anthropic API
            response = self.anthropic_client.messages.create(
                model="claude-3-opus-20240229",
                max_tokens=1024,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_message}
                ],
                temperature=0
            )
            
            # Process response
            result = {
                "action": action,
                "success": True,
                "message": response.content[0].text,
                "session_id": self.session_id
            }
            
            # Update state based on action
            if action == "navigate_to" and params and "url" in params:
                self.current_url = params["url"]
                # Fetch page content using existing browser tool
                browser_result = await self._execute_browser_action_via_sandbox("navigate_to", params)
                if browser_result.error:
                    return browser_result
                
                # Update page content and title
                self.current_page_content = browser_result.output.get("content", "")
                self.current_page_title = browser_result.output.get("title", "")
                
                # Add to result
                result["url"] = self.current_url
                result["title"] = self.current_page_title
            
            # Add message to thread
            await self.thread_manager.add_message(
                thread_id=self.thread_id,
                type="anthropic_browser_state",
                content=result,
                is_llm_message=False
            )
            
            return self.success_response(result)
            
        except Exception as e:
            logger.error(f"Error executing Anthropic browser action: {str(e)}", exc_info=True)
            return self.fail_response(f"Failed to execute Anthropic browser action: {str(e)}")
    
    async def _execute_browser_action_via_sandbox(self, endpoint: str, params: dict = None) -> ToolResult:
        """Execute a browser automation action through the sandbox API."""
        try:
            # Ensure sandbox is initialized
            await self._ensure_sandbox()
            
            # Build the curl command
            url = f"http://localhost:8002/api/automation/{endpoint}"
            
            if params:
                json_data = json.dumps(params)
                curl_cmd = f"curl -s -X POST '{url}' -H 'Content-Type: application/json' -d '{json_data}'"
            else:
                curl_cmd = f"curl -s -X POST '{url}' -H 'Content-Type: application/json'"
            
            logger.debug(f"Executing curl command: {curl_cmd}")
            
            response = self.sandbox.process.exec(curl_cmd, timeout=30)
            
            if response.exit_code == 0:
                try:
                    result = json.loads(response.result)
                    return self.success_response(result)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse response JSON: {response.result} {e}")
                    return self.fail_response(f"Failed to parse response JSON: {response.result} {e}")
            else:
                logger.error(f"Browser automation request failed: {response}")
                return self.fail_response(f"Browser automation request failed: {response}")
                
        except Exception as e:
            logger.error(f"Error executing browser action via sandbox: {str(e)}", exc_info=True)
            return self.fail_response(f"Error executing browser action via sandbox: {str(e)}")
    
    @openapi_schema({
        "type": "function",
        "function": {
            "name": "anthropic_navigate_to",
            "description": "Navigate to a specific URL using Anthropic's browser capabilities",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The URL to navigate to"
                    }
                },
                "required": ["url"]
            }
        }
    })
    @xml_schema(
        tag_name="anthropic-navigate-to",
        mappings=[
            {"param_name": "url", "node_type": "content", "path": "."}
        ],
        example='''
        <anthropic-navigate-to>
        https://example.com
        </anthropic-navigate-to>
        '''
    )
    async def anthropic_navigate_to(self, url: str) -> ToolResult:
        """Navigate to a specific URL using Anthropic's browser capabilities.
        
        Args:
            url (str): The URL to navigate to
            
        Returns:
            ToolResult: Result of the execution
        """
        return await self._execute_browser_action("navigate_to", {"url": url})
    
    @openapi_schema({
        "type": "function",
        "function": {
            "name": "anthropic_click_element",
            "description": "Click on an element on the current page using Anthropic's browser capabilities",
            "parameters": {
                "type": "object",
                "properties": {
                    "element_description": {
                        "type": "string",
                        "description": "Description of the element to click (e.g., 'Submit button', 'Login link')"
                    }
                },
                "required": ["element_description"]
            }
        }
    })
    @xml_schema(
        tag_name="anthropic-click-element",
        mappings=[
            {"param_name": "element_description", "node_type": "content", "path": "."}
        ],
        example='''
        <anthropic-click-element>
        Submit button
        </anthropic-click-element>
        '''
    )
    async def anthropic_click_element(self, element_description: str) -> ToolResult:
        """Click on an element on the current page using Anthropic's browser capabilities.
        
        Args:
            element_description (str): Description of the element to click
            
        Returns:
            ToolResult: Result of the execution
        """
        return await self._execute_browser_action("click_element", {"element_description": element_description})
    
    @openapi_schema({
        "type": "function",
        "function": {
            "name": "anthropic_input_text",
            "description": "Input text into a form field using Anthropic's browser capabilities",
            "parameters": {
                "type": "object",
                "properties": {
                    "field_description": {
                        "type": "string",
                        "description": "Description of the field to input text into (e.g., 'Username field', 'Search box')"
                    },
                    "text": {
                        "type": "string",
                        "description": "The text to input"
                    }
                },
                "required": ["field_description", "text"]
            }
        }
    })
    @xml_schema(
        tag_name="anthropic-input-text",
        mappings=[
            {"param_name": "field_description", "node_type": "attribute", "path": "."},
            {"param_name": "text", "node_type": "content", "path": "."}
        ],
        example='''
        <anthropic-input-text field_description="Username field">
        johndoe
        </anthropic-input-text>
        '''
    )
    async def anthropic_input_text(self, field_description: str, text: str) -> ToolResult:
        """Input text into a form field using Anthropic's browser capabilities.
        
        Args:
            field_description (str): Description of the field to input text into
            text (str): The text to input
            
        Returns:
            ToolResult: Result of the execution
        """
        return await self._execute_browser_action("input_text", {"field_description": field_description, "text": text})
    
    @openapi_schema({
        "type": "function",
        "function": {
            "name": "anthropic_extract_data",
            "description": "Extract structured data from the current page using Anthropic's capabilities",
            "parameters": {
                "type": "object",
                "properties": {
                    "data_description": {
                        "type": "string",
                        "description": "Description of the data to extract (e.g., 'Product prices', 'Article headings')"
                    },
                    "format": {
                        "type": "string",
                        "description": "Format for the extracted data",
                        "enum": ["json", "markdown", "text"],
                        "default": "json"
                    }
                },
                "required": ["data_description"]
            }
        }
    })
    @xml_schema(
        tag_name="anthropic-extract-data",
        mappings=[
            {"param_name": "data_description", "node_type": "content", "path": "."},
            {"param_name": "format", "node_type": "attribute", "path": "."}
        ],
        example='''
        <anthropic-extract-data format="json">
        Product prices and names
        </anthropic-extract-data>
        '''
    )
    async def anthropic_extract_data(self, data_description: str, format: str = "json") -> ToolResult:
        """Extract structured data from the current page using Anthropic's capabilities.
        
        Args:
            data_description (str): Description of the data to extract
            format (str, optional): Format for the extracted data. Defaults to "json".
            
        Returns:
            ToolResult: Result of the execution
        """
        return await self._execute_browser_action("extract_data", {"data_description": data_description, "format": format})
    
    @openapi_schema({
        "type": "function",
        "function": {
            "name": "anthropic_summarize_page",
            "description": "Summarize the content of the current page using Anthropic's capabilities",
            "parameters": {
                "type": "object",
                "properties": {
                    "focus": {
                        "type": "string",
                        "description": "Specific aspect to focus on in the summary (optional)"
                    },
                    "max_length": {
                        "type": "integer",
                        "description": "Maximum length of the summary in words",
                        "default": 200
                    }
                }
            }
        }
    })
    @xml_schema(
        tag_name="anthropic-summarize-page",
        mappings=[
            {"param_name": "focus", "node_type": "attribute", "path": "."},
            {"param_name": "max_length", "node_type": "attribute", "path": "."}
        ],
        example='''
        <anthropic-summarize-page focus="technical details" max_length="150">
        </anthropic-summarize-page>
        '''
    )
    async def anthropic_summarize_page(self, focus: Optional[str] = None, max_length: int = 200) -> ToolResult:
        """Summarize the content of the current page using Anthropic's capabilities.
        
        Args:
            focus (str, optional): Specific aspect to focus on in the summary. Defaults to None.
            max_length (int, optional): Maximum length of the summary in words. Defaults to 200.
            
        Returns:
            ToolResult: Result of the execution
        """
        params = {"max_length": max_length}
        if focus:
            params["focus"] = focus
        return await self._execute_browser_action("summarize_page", params)
    
    def success_response(self, output: Any) -> ToolResult:
        """Create a success response."""
        return ToolResult(output=output)
    
    def fail_response(self, error: str) -> ToolResult:
        """Create a failure response."""
        return ToolResult(error=error)
