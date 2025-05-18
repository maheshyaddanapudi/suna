"""
Agent runtime for Suna AI.
"""
import json
import os
import re
import time
import uuid
from datetime import datetime
from typing import AsyncGenerator, Dict, List, Optional, Union

import anthropic
import litellm
from dotenv import load_dotenv
from fastapi import HTTPException
from loguru import logger

from agentpress.thread_manager import ThreadManager
from config import config
from services.billing import check_billing_status
from agent.tools.sb_vision_tool import SandboxVisionTool

# Import all new tools directly
from agent.tools.sb_visualization_tool import SandboxVisualizationTool
from agent.tools.planning_tool import PlanningTool
from agent.tools.ask_human_tool import AskHumanTool
from agent.tools.chat_completion_tool import ChatCompletionTool
from agent.tools.ocr_tool import OCRTool
from agent.tools.speech_to_text_tool import SpeechToTextTool
from agent.tools.document_processing_tool import DocumentProcessingTool
from agent.tools.system_info_tool import SystemInfoTool
from agent.tools.anthropic_browser_tool import AnthropicBrowserTool
from agent.tools.code_interpreter_tool import CodeInterpreterTool

load_dotenv()

async def run_agent(
    project_id: str,
    thread_id: str,
    message: str,
    model_name: str = "claude-3-opus-20240229",
    system_prompt: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
    native_max_auto_continues: int = 0,
    enable_thinking: bool = False,
    reasoning_effort: str = "medium",
    enable_context_manager: bool = True,
    sandbox_id: Optional[str] = None,
    user_id: Optional[str] = None,
    metadata: Optional[Dict] = None,
) -> AsyncGenerator[Dict, None]:
    """
    Run the agent with the given message.
    """
    # Check if the user has enough credits
    if user_id:
        billing_status = await check_billing_status(user_id)
        if not billing_status["has_credits"]:
            yield {
                "type": "status",
                "status": "error",
                "message": "You don't have enough credits to run the agent. Please upgrade your plan."
            }
            return

    # Initialize thread manager
    thread_manager = ThreadManager()

    # Add tools
    thread_manager.add_tool(SandboxVisionTool)
    
    # Register all new tools in all environments
    # Register visualization tool
    visualization_tool = SandboxVisualizationTool(project_id, thread_id, thread_manager)
    thread_manager.tool_registry.register_tool(visualization_tool)
    
    # Register planning tool
    planning_tool = PlanningTool(project_id, thread_id, thread_manager)
    thread_manager.tool_registry.register_tool(planning_tool)
    
    # Register ask human tool
    ask_human_tool = AskHumanTool(project_id, thread_id, thread_manager)
    thread_manager.tool_registry.register_tool(ask_human_tool)
    
    # Register chat completion tool
    chat_completion_tool = ChatCompletionTool(project_id, thread_id, thread_manager)
    thread_manager.tool_registry.register_tool(chat_completion_tool)
    
    # Register OCR tool
    ocr_tool = OCRTool(project_id, thread_id, thread_manager)
    thread_manager.tool_registry.register_tool(ocr_tool)
    
    # Register speech-to-text tool
    speech_to_text_tool = SpeechToTextTool(project_id, thread_id, thread_manager)
    thread_manager.tool_registry.register_tool(speech_to_text_tool)
    
    # Register document processing tool
    document_processing_tool = DocumentProcessingTool(project_id, thread_id, thread_manager)
    thread_manager.tool_registry.register_tool(document_processing_tool)
    
    # Register system info tool
    system_info_tool = SystemInfoTool(project_id, thread_id, thread_manager)
    thread_manager.tool_registry.register_tool(system_info_tool)
    
    # Register Anthropic browser tool
    anthropic_browser_tool = AnthropicBrowserTool(project_id, thread_id, thread_manager)
    thread_manager.tool_registry.register_tool(anthropic_browser_tool)
    
    # Register code interpreter tool
    code_interpreter_tool = CodeInterpreterTool(project_id, thread_id, thread_manager)
    thread_manager.tool_registry.register_tool(code_interpreter_tool)
    
    if config.RAPID_API_KEY:
        thread_manager.add_tool(DataProvidersTool)

    # Only include sample response if the model name does not contain "anthropic"
    if "anthropic" not in model_name.lower():
        thread_manager.include_sample_response = True

    # Set sandbox ID
    thread_manager.sandbox_id = sandbox_id

    # Set metadata
    thread_manager.metadata = metadata or {}

    # Set the original sandbox ID for potential cleanup later
    original_sandbox_id = sandbox_id

    # Run the thread
    continue_execution = True
    while continue_execution:
        try:
            # Run the thread
            response = await thread_manager.run_thread(
                project_id=project_id,
                thread_id=thread_id,
                message=message,
                model_name=model_name,
                system_prompt=system_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                tool_config=anthropic.ToolConfig(
                    execute_tools=True,
                    execute_on_stream=True,
                    tool_execution_strategy="parallel",
                    xml_adding_strategy="user_message"
                ),
                native_max_auto_continues=native_max_auto_continues,
                include_xml_examples=True,
                enable_thinking=enable_thinking,
                reasoning_effort=reasoning_effort,
                enable_context_manager=enable_context_manager
            )
            if isinstance(response, dict) and "status" in response and response["status"] == "error":
                logger.error(f"Error response from run_thread: {response.get('message', 'Unknown error')}")
                yield response
                break
            # Track if we see ask, complete, or web-browser-takeover tool calls
            last_tool_call = None
            # Process the response
            error_detected = False
            try:
                async for chunk in response:
                    # If we receive an error chunk, we should stop after this iteration
                    if isinstance(chunk, dict) and chunk.get('type') == 'status' and chunk.get('status') == 'error':
                        logger.error(f"Error chunk detected: {chunk.get('message', 'Unknown error')}")
                        error_detected = True
                        yield chunk  # Forward the error chunk
                        continue     # Continue processing other chunks but don't break yet
                        
                    # Check for XML versions like <ask>, <complete>, or <web-browser-takeover> in assistant content chunks
                    if chunk.get('type') == 'assistant' and 'content' in chunk:
                        try:
                            # The content field might be a JSON string or object
                            content = chunk.get('content', '{}')
                            if isinstance(content, str):
                                assistant_content_json = json.loads(content)
                            else:
                                assistant_content_json = content
                            # The actual text content is nested within
                            assistant_text = assistant_content_json.get('content', '')
                            if isinstance(assistant_text, str): # Ensure it's a string
                                 # Check for the closing tags as they signal the end of the tool usage
                                if '</ask>' in assistant_text or '</complete>' in assistant_text or '</web-browser-takeover>' in assistant_text:
                                   if '</ask>' in assistant_text:
                                       xml_tool = 'ask'
                                   elif '</complete>' in assistant_text:
                                       xml_tool = 'complete'
                                   elif '</web-browser-takeover>' in assistant_text:
                                       xml_tool = 'web-browser-takeover'
                                   last_tool_call = xml_tool
                                   logger.info(f"Agent used XML tool: {xml_tool}")
                        except json.JSONDecodeError:
                            # Handle cases where content might not be valid JSON
                            logger.warning(f"Warning: Could not parse assistant content JSON: {chunk.get('content')}")
                        except Exception as e:
                            logger.error(f"Error processing assistant chunk: {e}")
                    yield chunk
                # Check if we should stop based on the last tool call or error
                if error_detected:
                    logger.info(f"Stopping due to error detected in response")
                    break
                    
                if last_tool_call in ['ask', 'complete', 'web-browser-takeover']:
                    logger.info(f"Agent decided to stop with tool: {last_tool_call}")
                    continue_execution = False
            except Exception as e:
                # Just log the error and re-raise to stop all iterations
                error_msg = f"Error during response streaming: {str(e)}"
                logger.error(f"Error: {error_msg}")
                yield {
                    "type": "status",
                    "status": "error",
                    "message": error_msg
                }
                # Stop execution immediately on any error
                break
                
        except Exception as e:
            # Just log the error and re-raise to stop all iterations
            error_msg = f"Error running thread: {str(e)}"
            logger.error(f"Error: {error_msg}")
            yield {
                "type": "status",
                "status": "error",
                "message": error_msg
            }
            # Stop execution immediately on any error
            break

# TESTING
async def test_agent():
    """Test function to run the agent with a sample query"""
    from agentpress.thread_manager import ThreadManager
    from services.supabase import DBConnection

    # Initialize ThreadManager
    thread_manager = ThreadManager()

    # Create a test thread directly with Postgres function
    client = await DBConnection().client

    try:
        # Get user's personal account
        account_result = await client.rpc('get_personal_account').execute()

        # if not account_result.data:
        #     print("Error: No personal account found")
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    import asyncio
    # Configure any environment variables or setup needed for testing
    load_dotenv()  # Ensure environment variables are loaded
    # Run the test function
    asyncio.run(test_agent())
