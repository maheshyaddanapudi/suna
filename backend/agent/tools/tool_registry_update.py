"""
Tool registry update to include new tools in Suna AI.
"""

from agentpress.thread_manager import ThreadManager
from agentpress.tool_registry import ToolRegistry

def register_tools(tool_registry: ToolRegistry, project_id: str, thread_id: str, thread_manager: ThreadManager):
    """
    Register all new tools with the tool registry.
    
    Args:
        tool_registry: The tool registry to register tools with
        project_id: The project ID
        thread_id: The thread ID
        thread_manager: The thread manager
    """
    # Import tools
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
    
    # Register visualization tool
    visualization_tool = SandboxVisualizationTool(project_id, thread_id, thread_manager)
    tool_registry.register_tool(visualization_tool)
    
    # Register planning tool
    planning_tool = PlanningTool(project_id, thread_id, thread_manager)
    tool_registry.register_tool(planning_tool)
    
    # Register ask human tool
    ask_human_tool = AskHumanTool(project_id, thread_id, thread_manager)
    tool_registry.register_tool(ask_human_tool)
    
    # Register chat completion tool
    chat_completion_tool = ChatCompletionTool(project_id, thread_id, thread_manager)
    tool_registry.register_tool(chat_completion_tool)
    
    # Register OCR tool
    ocr_tool = OCRTool(project_id, thread_id, thread_manager)
    tool_registry.register_tool(ocr_tool)
    
    # Register speech-to-text tool
    speech_to_text_tool = SpeechToTextTool(project_id, thread_id, thread_manager)
    tool_registry.register_tool(speech_to_text_tool)
    
    # Register document processing tool
    document_processing_tool = DocumentProcessingTool(project_id, thread_id, thread_manager)
    tool_registry.register_tool(document_processing_tool)
    
    # Register system info tool
    system_info_tool = SystemInfoTool(project_id, thread_id, thread_manager)
    tool_registry.register_tool(system_info_tool)
    
    # Register Anthropic browser tool
    anthropic_browser_tool = AnthropicBrowserTool(project_id, thread_id, thread_manager)
    tool_registry.register_tool(anthropic_browser_tool)
    
    # Register code interpreter tool
    code_interpreter_tool = CodeInterpreterTool(project_id, thread_id, thread_manager)
    tool_registry.register_tool(code_interpreter_tool)
