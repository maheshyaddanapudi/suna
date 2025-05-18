"""
Code Interpreter tool for executing Python code in a sandbox environment.
"""

import os
import json
import traceback
import tempfile
import uuid
from typing import Optional, Dict, Any, List

from agentpress.tool import ToolResult, openapi_schema, xml_schema
from agentpress.thread_manager import ThreadManager
from sandbox.tool_base import SandboxToolsBase
from utils.logger import logger

class CodeInterpreterTool(SandboxToolsBase):
    """Tool for executing Python code in a sandbox environment."""
    
    def __init__(self, project_id: str, thread_id: str, thread_manager: ThreadManager):
        super().__init__(project_id, thread_manager)
        self.thread_id = thread_id
        self.thread_manager = thread_manager
        self.workspace_path = "/workspace"
        self.temp_dir = "/tmp/code_interpreter"
        
    @openapi_schema({
        "type": "function",
        "function": {
            "name": "execute_python",
            "description": "Execute Python code in a sandbox environment. This tool allows you to run Python code for data analysis, visualization, processing, and other computational tasks.",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "Python code to execute. The code should be complete and runnable."
                    },
                    "save_output": {
                        "type": "boolean",
                        "description": "Whether to save the output to a file",
                        "default": False
                    },
                    "output_file": {
                        "type": "string",
                        "description": "Path to save the output file (relative to /workspace). If not provided, a temporary file will be used."
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Maximum execution time in seconds",
                        "default": 30
                    }
                },
                "required": ["code"]
            }
        }
    })
    @xml_schema(
        tag_name="execute-python",
        mappings=[
            {"param_name": "code", "node_type": "content", "path": "."},
            {"param_name": "save_output", "node_type": "attribute", "path": "."},
            {"param_name": "output_file", "node_type": "attribute", "path": "."},
            {"param_name": "timeout", "node_type": "attribute", "path": "."}
        ],
        example='''
        <execute-python save_output="true" output_file="analysis_results.txt" timeout="60">
        import pandas as pd
        import matplotlib.pyplot as plt
        
        # Load data
        data = pd.read_csv('/workspace/data.csv')
        
        # Analyze data
        summary = data.describe()
        print(summary)
        
        # Create visualization
        plt.figure(figsize=(10, 6))
        data.plot(kind='bar')
        plt.title('Data Analysis')
        plt.savefig('/workspace/plot.png')
        
        # Return results
        print("Analysis complete. Plot saved to /workspace/plot.png")
        </execute-python>
        '''
    )
    async def execute_python(self, 
                           code: str, 
                           save_output: bool = False, 
                           output_file: Optional[str] = None,
                           timeout: int = 30) -> ToolResult:
        """Execute Python code in a sandbox environment.
        
        Args:
            code (str): Python code to execute
            save_output (bool, optional): Whether to save the output to a file. Defaults to False.
            output_file (str, optional): Path to save the output file. Defaults to None.
            timeout (int, optional): Maximum execution time in seconds. Defaults to 30.
            
        Returns:
            ToolResult: Result of the execution
        """
        try:
            # Ensure sandbox is initialized
            await self._ensure_sandbox()
            
            # Create temp directory if it doesn't exist
            self.sandbox.process.exec(f"mkdir -p {self.temp_dir}", timeout=5)
            
            # Generate a unique ID for this execution
            execution_id = str(uuid.uuid4())
            
            # Create a temporary Python file
            temp_file = f"{self.temp_dir}/code_{execution_id}.py"
            
            # Create a file to capture output
            output_capture_file = f"{self.temp_dir}/output_{execution_id}.txt"
            
            # Write the code to the temporary file
            self.sandbox.fs.upload_file(temp_file, code.encode('utf-8'))
            
            # Execute the code with output redirection
            cmd = f"python3 {temp_file} > {output_capture_file} 2>&1"
            result = self.sandbox.process.exec(cmd, timeout=timeout)
            
            # Read the output
            output = ""
            if self._file_exists(output_capture_file):
                output = self.sandbox.fs.download_file(output_capture_file).decode('utf-8', errors='replace')
            
            # Save output to file if requested
            saved_file_path = None
            if save_output and output:
                if output_file:
                    # Clean and normalize the path
                    clean_output_file = self._clean_path(output_file)
                    full_output_path = f"{self.workspace_path}/{clean_output_file}"
                    
                    # Create directory if it doesn't exist
                    dir_path = os.path.dirname(full_output_path)
                    if dir_path:
                        self.sandbox.process.exec(f"mkdir -p {dir_path}", timeout=5)
                    
                    # Save the output
                    self.sandbox.fs.upload_file(full_output_path, output.encode('utf-8'))
                    saved_file_path = clean_output_file
                else:
                    # Use a default output file in the workspace
                    default_output_file = f"code_output_{execution_id}.txt"
                    full_output_path = f"{self.workspace_path}/{default_output_file}"
                    self.sandbox.fs.upload_file(full_output_path, output.encode('utf-8'))
                    saved_file_path = default_output_file
            
            # Clean up temporary files
            self.sandbox.process.exec(f"rm -f {temp_file} {output_capture_file}", timeout=5)
            
            # Prepare result
            execution_result = {
                "success": result.exit_code == 0,
                "output": output,
                "exit_code": result.exit_code
            }
            
            if saved_file_path:
                execution_result["saved_to"] = saved_file_path
            
            # Add message to thread
            await self.thread_manager.add_message(
                thread_id=self.thread_id,
                type="code_execution",
                content={
                    "code": code,
                    "result": execution_result
                },
                is_llm_message=False
            )
            
            if result.exit_code == 0:
                message = "Code executed successfully."
                if saved_file_path:
                    message += f" Output saved to {saved_file_path}"
                return self.success_response({
                    "message": message,
                    "output": output,
                    "saved_to": saved_file_path
                })
            else:
                return self.fail_response(f"Code execution failed with exit code {result.exit_code}. Output: {output}")
            
        except Exception as e:
            logger.error(f"Error executing Python code: {str(e)}", exc_info=True)
            return self.fail_response(f"Error executing Python code: {str(e)}")
    
    @openapi_schema({
        "type": "function",
        "function": {
            "name": "execute_python_with_files",
            "description": "Execute Python code that interacts with files in the workspace. This tool is useful for data processing, analysis, and visualization tasks that involve reading from or writing to files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "Python code to execute. The code should be complete and runnable."
                    },
                    "input_files": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        },
                        "description": "List of input files to use (paths relative to /workspace)"
                    },
                    "output_files": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        },
                        "description": "List of expected output files (paths relative to /workspace)"
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Maximum execution time in seconds",
                        "default": 60
                    }
                },
                "required": ["code"]
            }
        }
    })
    @xml_schema(
        tag_name="execute-python-with-files",
        mappings=[
            {"param_name": "code", "node_type": "content", "path": "."},
            {"param_name": "input_files", "node_type": "attribute", "path": "."},
            {"param_name": "output_files", "node_type": "attribute", "path": "."},
            {"param_name": "timeout", "node_type": "attribute", "path": "."}
        ],
        example='''
        <execute-python-with-files 
            input_files="['data.csv', 'config.json']" 
            output_files="['results.csv', 'plot.png']" 
            timeout="120">
        import pandas as pd
        import matplotlib.pyplot as plt
        import json
        
        # Load configuration
        with open('/workspace/config.json', 'r') as f:
            config = json.load(f)
        
        # Load data
        data = pd.read_csv('/workspace/data.csv')
        
        # Process data according to config
        processed_data = data[data['value'] > config['threshold']]
        
        # Save results
        processed_data.to_csv('/workspace/results.csv', index=False)
        
        # Create visualization
        plt.figure(figsize=(10, 6))
        processed_data.plot(kind='bar')
        plt.title(f"Data filtered by threshold {config['threshold']}")
        plt.savefig('/workspace/plot.png')
        
        print("Processing complete. Results saved to results.csv and plot.png")
        </execute-python-with-files>
        '''
    )
    async def execute_python_with_files(self, 
                                      code: str, 
                                      input_files: Optional[List[str]] = None,
                                      output_files: Optional[List[str]] = None,
                                      timeout: int = 60) -> ToolResult:
        """Execute Python code that interacts with files in the workspace.
        
        Args:
            code (str): Python code to execute
            input_files (List[str], optional): List of input files to use. Defaults to None.
            output_files (List[str], optional): List of expected output files. Defaults to None.
            timeout (int, optional): Maximum execution time in seconds. Defaults to 60.
            
        Returns:
            ToolResult: Result of the execution
        """
        try:
            # Ensure sandbox is initialized
            await self._ensure_sandbox()
            
            # Parse input_files and output_files if they're strings
            if isinstance(input_files, str):
                try:
                    input_files = json.loads(input_files.replace("'", '"'))
                except json.JSONDecodeError:
                    input_files = [f.strip() for f in input_files.strip('[]').split(',')]
            
            if isinstance(output_files, str):
                try:
                    output_files = json.loads(output_files.replace("'", '"'))
                except json.JSONDecodeError:
                    output_files = [f.strip() for f in output_files.strip('[]').split(',')]
            
            # Create temp directory if it doesn't exist
            self.sandbox.process.exec(f"mkdir -p {self.temp_dir}", timeout=5)
            
            # Generate a unique ID for this execution
            execution_id = str(uuid.uuid4())
            
            # Create a temporary Python file
            temp_file = f"{self.temp_dir}/code_{execution_id}.py"
            
            # Create a file to capture output
            output_capture_file = f"{self.temp_dir}/output_{execution_id}.txt"
            
            # Check if input files exist
            missing_files = []
            if input_files:
                for file_path in input_files:
                    clean_path = self._clean_path(file_path)
                    full_path = f"{self.workspace_path}/{clean_path}"
                    if not self._file_exists(full_path):
                        missing_files.append(clean_path)
            
            if missing_files:
                return self.fail_response(f"The following input files do not exist: {', '.join(missing_files)}")
            
            # Write the code to the temporary file
            self.sandbox.fs.upload_file(temp_file, code.encode('utf-8'))
            
            # Execute the code with output redirection
            cmd = f"cd {self.workspace_path} && python3 {temp_file} > {output_capture_file} 2>&1"
            result = self.sandbox.process.exec(cmd, timeout=timeout)
            
            # Read the output
            output = ""
            if self._file_exists(output_capture_file):
                output = self.sandbox.fs.download_file(output_capture_file).decode('utf-8', errors='replace')
            
            # Check if output files were created
            created_files = []
            missing_output_files = []
            if output_files:
                for file_path in output_files:
                    clean_path = self._clean_path(file_path)
                    full_path = f"{self.workspace_path}/{clean_path}"
                    if self._file_exists(full_path):
                        created_files.append(clean_path)
                    else:
                        missing_output_files.append(clean_path)
            
            # Clean up temporary files
            self.sandbox.process.exec(f"rm -f {temp_file} {output_capture_file}", timeout=5)
            
            # Prepare result
            execution_result = {
                "success": result.exit_code == 0,
                "output": output,
                "exit_code": result.exit_code,
                "created_files": created_files
            }
            
            if missing_output_files:
                execution_result["missing_output_files"] = missing_output_files
            
            # Add message to thread
            await self.thread_manager.add_message(
                thread_id=self.thread_id,
                type="code_execution",
                content={
                    "code": code,
                    "result": execution_result
                },
                is_llm_message=False
            )
            
            if result.exit_code == 0:
                message = "Code executed successfully."
                if created_files:
                    message += f" Created files: {', '.join(created_files)}"
                if missing_output_files:
                    message += f" Expected but missing files: {', '.join(missing_output_files)}"
                
                return self.success_response({
                    "message": message,
                    "output": output,
                    "created_files": created_files,
                    "missing_output_files": missing_output_files
                })
            else:
                return self.fail_response(f"Code execution failed with exit code {result.exit_code}. Output: {output}")
            
        except Exception as e:
            logger.error(f"Error executing Python code with files: {str(e)}", exc_info=True)
            return self.fail_response(f"Error executing Python code with files: {str(e)}")
    
    def _clean_path(self, path: str) -> str:
        """Clean and normalize a path to be relative to /workspace"""
        # Remove leading slash and workspace prefix
        path = path.lstrip('/')
        if path.startswith('workspace/'):
            path = path[len('workspace/'):]
        
        # Remove any attempts to navigate up directories
        path = path.replace('../', '')
        
        return path
    
    def _file_exists(self, path: str) -> bool:
        """Check if a file exists in the sandbox"""
        try:
            self.sandbox.fs.get_file_info(path)
            return True
        except Exception:
            return False
    
    def success_response(self, output: Any) -> ToolResult:
        """Create a success response."""
        return ToolResult(output=output)
    
    def fail_response(self, error: str) -> ToolResult:
        """Create a failure response."""
        return ToolResult(error=error)
