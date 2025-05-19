"""
AskHuman tool for requesting human assistance within the sandbox.
"""

from typing import Optional, Dict, Any

from agentpress.tool import ToolResult, openapi_schema, xml_schema
from sandbox.tool_base import SandboxToolsBase
from agentpress.thread_manager import ThreadManager
from utils.logger import logger

class AskHumanTool(SandboxToolsBase):
    """Tool for requesting human assistance."""

    def __init__(self, project_id: str, thread_id: str, thread_manager: ThreadManager):
        super().__init__(project_id, thread_manager)
        self.thread_id = thread_id
        self.thread_manager = thread_manager

    @openapi_schema({
        "type": "function",
        "function": {
            "name": "ask_human",
            "description": "Asks the human user for assistance with a specific question or task.",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "The question or request for the human user"
                    },
                    "context": {
                        "type": "string",
                        "description": "Additional context or information to help the human understand the request"
                    },
                    "options": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        },
                        "description": "Optional list of predefined options for the human to choose from"
                    },
                    "importance": {
                        "type": "string",
                        "description": "Importance level of the request",
                        "enum": ["low", "medium", "high", "critical"],
                        "default": "medium"
                    },
                    "timeout_seconds": {
                        "type": "integer",
                        "description": "Optional timeout in seconds after which the agent should proceed without human input",
                        "default": 300
                    }
                },
                "required": ["question"]
            }
        }
    })
    @xml_schema(
        tag_name="ask-human",
        mappings=[
            {"param_name": "question", "node_type": "text", "path": "question"},
            {"param_name": "context", "node_type": "text", "path": "context"},
            {"param_name": "options", "node_type": "text", "path": "options"},
            {"param_name": "importance", "node_type": "attribute", "path": "."},
            {"param_name": "timeout_seconds", "node_type": "attribute", "path": "."}
        ],
        example='''
        <!-- Example: Ask the human for input on a design decision -->
        <ask-human importance="high" timeout_seconds="600">
            <question>Which color scheme should I use for the website?</question>
            <context>I'm designing the main landing page and need to choose between different color palettes.</context>
            <options>["Blue and white", "Green and gray", "Purple and gold", "Monochrome"]</options>
        </ask-human>
        '''
    )
    async def ask_human(self, 
                       question: str, 
                       context: Optional[str] = None,
                       options: Optional[list] = None,
                       importance: str = "medium",
                       timeout_seconds: int = 300) -> ToolResult:
        """Asks the human user for assistance with a specific question or task."""
        try:
            # Ensure sandbox is initialized
            await self._ensure_sandbox()
            
            # Format the request message
            message = {
                "type": "human_assistance_request",
                "question": question,
                "context": context,
                "options": options,
                "importance": importance,
                "timeout_seconds": timeout_seconds
            }
            
            # Add the request to the thread
            request_message_id = await self.thread_manager.add_message(
                thread_id=self.thread_id,
                type="human_assistance_request",
                content=message,
                is_llm_message=False
            )
            
            # Wait for human response
            # In a real implementation, this would use a proper async waiting mechanism
            # For now, we'll simulate it by adding a placeholder response
            
            # Add a placeholder response (in a real implementation, this would be the actual human response)
            response_message = {
                "type": "human_assistance_response",
                "request_id": request_message_id,
                "response": "This is a simulated human response. In a real implementation, this would be the actual response from the human user.",
                "response_time": self._get_timestamp()
            }
            
            # Add the response to the thread
            await self.thread_manager.add_message(
                thread_id=self.thread_id,
                type="human_assistance_response",
                content=response_message,
                is_llm_message=False
            )
            
            # Return success with the response
            return self.success_response(f"Human assistance request sent. Response: {response_message['response']}")
            
        except Exception as e:
            logger.error(f"Error asking human for assistance: {str(e)}", exc_info=True)
            return self.fail_response(f"Failed to ask human for assistance: {str(e)}")
    
    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        import datetime
        return datetime.datetime.now().isoformat()
    
    def success_response(self, message: str) -> ToolResult:
        """Create a success response."""
        return ToolResult(output=message)
    
    def fail_response(self, error: str) -> ToolResult:
        """Create a failure response."""
        return ToolResult(error=error)
