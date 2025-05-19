"""
CreateChatCompletion tool for creating nested LLM completions within the sandbox.
"""

from typing import Optional, Dict, Any, List
import json
import uuid

from agentpress.tool import ToolResult, openapi_schema, xml_schema
from sandbox.tool_base import SandboxToolsBase
from agentpress.thread_manager import ThreadManager
from utils.logger import logger
from utils.config import config

class CreateChatCompletionTool(SandboxToolsBase):
    """Tool for creating nested LLM completions."""

    def __init__(self, project_id: str, thread_manager: ThreadManager):
        super().__init__(project_id, thread_manager)
        self.thread_manager = thread_manager

    @openapi_schema({
        "type": "function",
        "function": {
            "name": "create_chat_completion",
            "description": "Creates a chat completion using the LLM with the provided messages.",
            "parameters": {
                "type": "object",
                "properties": {
                    "messages": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "role": {
                                    "type": "string",
                                    "enum": ["system", "user", "assistant"]
                                },
                                "content": {
                                    "type": "string"
                                }
                            },
                            "required": ["role", "content"]
                        },
                        "description": "The messages to send to the LLM"
                    },
                    "model": {
                        "type": "string",
                        "description": "The model to use for the completion (defaults to the configured model)"
                    },
                    "temperature": {
                        "type": "number",
                        "description": "The temperature to use for the completion",
                        "default": 0.7
                    },
                    "max_tokens": {
                        "type": "integer",
                        "description": "The maximum number of tokens to generate",
                        "default": 1000
                    },
                    "save_to_file": {
                        "type": "string",
                        "description": "Optional path to save the completion result"
                    }
                },
                "required": ["messages"]
            }
        }
    })
    @xml_schema(
        tag_name="create-chat-completion",
        mappings=[
            {"param_name": "messages", "node_type": "text", "path": "messages"},
            {"param_name": "model", "node_type": "attribute", "path": "."},
            {"param_name": "temperature", "node_type": "attribute", "path": "."},
            {"param_name": "max_tokens", "node_type": "attribute", "path": "."},
            {"param_name": "save_to_file", "node_type": "attribute", "path": "."}
        ],
        example='''
        <!-- Example: Create a chat completion for summarizing text -->
        <create-chat-completion model="anthropic/claude-3-7-sonnet-latest" temperature="0.3" max_tokens="500" save_to_file="summaries/article_summary.txt">
            <messages>[
                {"role": "system", "content": "You are a helpful assistant that summarizes text concisely."},
                {"role": "user", "content": "Please summarize the following article: [article text here]"}
            ]</messages>
        </create-chat-completion>
        '''
    )
    async def create_chat_completion(self, 
                                   messages: List[Dict[str, str]], 
                                   model: Optional[str] = None,
                                   temperature: float = 0.7,
                                   max_tokens: int = 1000,
                                   save_to_file: Optional[str] = None) -> ToolResult:
        """Creates a chat completion using the LLM with the provided messages."""
        try:
            # Ensure sandbox is initialized
            await self._ensure_sandbox()
            
            # Use configured model if not specified
            if not model:
                model = config.MODEL_TO_USE
            
            # Validate messages
            if not messages or not isinstance(messages, list):
                return self.fail_response("Messages must be a non-empty list")
            
            for msg in messages:
                if not isinstance(msg, dict) or 'role' not in msg or 'content' not in msg:
                    return self.fail_response("Each message must be a dictionary with 'role' and 'content' keys")
                if msg['role'] not in ['system', 'user', 'assistant']:
                    return self.fail_response(f"Invalid role: {msg['role']}. Must be one of: system, user, assistant")
            
            # Get database client
            client = await self.thread_manager.db.client
            
            # Create a temporary thread for the completion
            temp_thread_id = str(uuid.uuid4())
            
            # Insert the temporary thread into the database
            await client.table('threads').insert({
                'thread_id': temp_thread_id,
                'account_id': self.project_id,  # Use project_id as account_id for temporary thread
                'name': f"Temp Thread {temp_thread_id[:8]}",
                'created_at': self._get_timestamp(),
                'is_temporary': True
            }).execute()
            
            # Add messages to the temporary thread
            for msg in messages:
                await client.table('messages').insert({
                    'message_id': str(uuid.uuid4()),
                    'thread_id': temp_thread_id,
                    'role': msg['role'],
                    'content': msg['content'],
                    'created_at': self._get_timestamp()
                }).execute()
            
            # Create completion request
            completion_request = {
                'model': model,
                'temperature': temperature,
                'max_tokens': max_tokens,
                'messages': messages
            }
            
            # Get the LLM client from thread manager
            llm_client = self.thread_manager.llm_client
            
            # Create the completion
            completion_response = await llm_client.create_chat_completion(completion_request)
            
            # Extract the completion text
            completion_text = completion_response['choices'][0]['message']['content']
            
            # Save to file if requested
            if save_to_file:
                cleaned_path = self.clean_path(save_to_file)
                full_path = f"{self.workspace_path}/{cleaned_path}"
                
                # Create directory if it doesn't exist
                dir_path = "/".join(full_path.split("/")[:-1])
                await self.sandbox.exec.start(
                    command=f"mkdir -p {dir_path}"
                )
                
                # Save the completion to file
                self.sandbox.fs.upload_file(full_path, completion_text.encode('utf-8'))
            
            # Clean up the temporary thread
            await client.table('messages').delete().eq('thread_id', temp_thread_id).execute()
            await client.table('threads').delete().eq('thread_id', temp_thread_id).execute()
            
            return self.success_response(completion_text)
            
        except Exception as e:
            logger.error(f"Error creating chat completion: {str(e)}", exc_info=True)
            return self.fail_response(f"Failed to create chat completion: {str(e)}")
    
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
