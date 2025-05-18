"""
Speech-to-Text tool for converting audio to text within the sandbox.
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

class SandboxSpeechToTextTool(SandboxToolsBase):
    """Tool for converting speech to text within the sandbox."""

    def __init__(self, project_id: str, thread_id: str, thread_manager: ThreadManager):
        super().__init__(project_id, thread_manager)
        self.thread_id = thread_id
        self.thread_manager = thread_manager

    @openapi_schema({
        "type": "function",
        "function": {
            "name": "transcribe_audio",
            "description": "Transcribes speech from an audio file to text using Whisper ASR.",
            "parameters": {
                "type": "object",
                "properties": {
                    "audio_path": {
                        "type": "string",
                        "description": "Path to the audio file within the workspace"
                    },
                    "model_size": {
                        "type": "string",
                        "description": "Size of the Whisper model to use",
                        "enum": ["tiny", "base", "small", "medium", "large"],
                        "default": "base"
                    },
                    "language": {
                        "type": "string",
                        "description": "Language code (optional, auto-detected if not specified)"
                    },
                    "output_path": {
                        "type": "string",
                        "description": "Optional path to save the transcription to a file"
                    },
                    "translate": {
                        "type": "boolean",
                        "description": "Whether to translate non-English speech to English",
                        "default": false
                    }
                },
                "required": ["audio_path"]
            }
        }
    })
    @xml_schema(
        tag_name="transcribe-audio",
        mappings=[
            {"param_name": "audio_path", "node_type": "attribute", "path": "."},
            {"param_name": "model_size", "node_type": "attribute", "path": "."},
            {"param_name": "language", "node_type": "attribute", "path": "."},
            {"param_name": "output_path", "node_type": "attribute", "path": "."},
            {"param_name": "translate", "node_type": "attribute", "path": "."}
        ],
        example='''
        <!-- Example: Transcribe a podcast episode -->
        <transcribe-audio audio_path="audio/podcast_episode.mp3" model_size="small" output_path="transcripts/podcast_episode.txt"></transcribe-audio>
        '''
    )
    async def transcribe_audio(self, 
                              audio_path: str, 
                              model_size: str = "base",
                              language: Optional[str] = None,
                              output_path: Optional[str] = None,
                              translate: bool = False) -> ToolResult:
        """Transcribes speech from an audio file to text."""
        try:
            # Ensure sandbox is initialized
            await self._ensure_sandbox()
            
            # Install required packages if not already installed
            await self._ensure_speech_to_text_packages()
            
            # Clean and construct full path
            cleaned_path = self.clean_path(audio_path)
            full_path = f"{self.workspace_path}/{cleaned_path}"
            
            # Check if file exists
            try:
                file_info = self.sandbox.fs.get_file_info(full_path)
                if file_info.is_dir:
                    return self.fail_response(f"Path '{cleaned_path}' is a directory, not an audio file.")
            except Exception as e:
                return self.fail_response(f"Audio file not found at path: '{cleaned_path}'")
            
            # Create Python script for transcription
            script_content = self._generate_transcription_script(
                audio_path=full_path,
                model_size=model_size,
                language=language,
                translate=translate,
                output_path=output_path
            )
            
            # Save script to temporary file
            script_path = "/tmp/transcription_script.py"
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
                return self.fail_response(f"Failed to transcribe audio: {error_output}")
            
            # Get the output
            output = await result.get_output()
            
            # If output path was specified, read the saved file
            if output_path:
                cleaned_output_path = self.clean_path(output_path)
                full_output_path = f"{self.workspace_path}/{cleaned_output_path}"
                
                try:
                    transcription = self.sandbox.fs.download_file(full_output_path).decode('utf-8')
                    return self.success_response(f"Audio transcribed and saved to {cleaned_output_path}:\n\n{transcription}")
                except Exception as e:
                    return self.fail_response(f"Failed to read transcription from {cleaned_output_path}: {str(e)}")
            else:
                # Parse the output to get the transcription
                transcription = output.strip()
                return self.success_response(transcription)
            
        except Exception as e:
            logger.error(f"Error transcribing audio: {str(e)}", exc_info=True)
            return self.fail_response(f"Failed to transcribe audio: {str(e)}")
    
    async def _ensure_speech_to_text_packages(self):
        """Ensure required speech-to-text packages are installed."""
        packages = ["openai-whisper", "torch", "ffmpeg-python"]
        
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
        
        # Install ffmpeg if not already installed
        result = await self.sandbox.exec.start(
            command="which ffmpeg >/dev/null 2>&1 && echo 'installed' || echo 'not installed'"
        )
        await result.wait()
        output = await result.get_output()
        
        if "not installed" in output:
            # Install ffmpeg
            install_result = await self.sandbox.exec.start(
                command="apt-get update && apt-get install -y ffmpeg"
            )
            await install_result.wait()
            
            if install_result.exit_code != 0:
                install_error = await install_result.get_output()
                logger.warning(f"Failed to install ffmpeg: {install_error}")
    
    def _generate_transcription_script(self, 
                                      audio_path: str, 
                                      model_size: str,
                                      language: Optional[str],
                                      translate: bool,
                                      output_path: Optional[str] = None) -> str:
        """Generate Python script for transcription."""
        script = f"""
import whisper
import os
import torch

# Check if CUDA is available
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using device: {{device}}")

# Path to the audio file
audio_path = "{audio_path}"

# Load the model
print("Loading Whisper model...")
model = whisper.load_model("{model_size}", device=device)
print(f"Model loaded: {model_size}")

# Prepare transcription options
options = {{
    "task": "translate" if {str(translate).lower()} else "transcribe",
}}

# Add language if specified
"""
        
        if language:
            script += f'options["language"] = "{language}"\n'
        
        script += """
# Perform transcription
print("Transcribing audio...")
result = model.transcribe(audio_path, **options)
transcription = result["text"]
print("Transcription complete")

# Print the transcription
print(transcription)
"""
        
        if output_path:
            script += f"""
# Create directory if it doesn't exist
os.makedirs(os.path.dirname("{output_path}"), exist_ok=True)

# Save transcription to file
with open("{output_path}", "w") as f:
    f.write(transcription)
"""
        
        return script
    
    def success_response(self, message: str) -> ToolResult:
        """Create a success response."""
        return ToolResult(output=message)
    
    def fail_response(self, error: str) -> ToolResult:
        """Create a failure response."""
        return ToolResult(error=error)
