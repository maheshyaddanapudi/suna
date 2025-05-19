"""
Visualization tool for creating charts and data visualizations within the sandbox.
"""

import io
import json
import base64
from typing import Dict, List, Any, Optional

from agentpress.tool import ToolResult, openapi_schema, xml_schema
from sandbox.tool_base import SandboxToolsBase
from agentpress.thread_manager import ThreadManager
from utils.logger import logger

class SandboxVisualizationTool(SandboxToolsBase):
    """Tool for creating data visualizations within the sandbox."""

    def __init__(self, project_id: str, thread_id: str, thread_manager: ThreadManager):
        super().__init__(project_id, thread_manager)
        self.thread_id = thread_id
        self.thread_manager = thread_manager

    @openapi_schema({
        "type": "function",
        "function": {
            "name": "create_chart",
            "description": "Creates a chart or visualization from data and saves it to a file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "chart_type": {
                        "type": "string",
                        "description": "Type of chart to create",
                        "enum": ["bar", "line", "scatter", "pie", "heatmap", "histogram", "boxplot"]
                    },
                    "data": {
                        "type": "object",
                        "description": "Data for the chart in a format compatible with pandas DataFrame. For simple charts, provide 'x' and 'y' arrays."
                    },
                    "title": {
                        "type": "string",
                        "description": "Title of the chart"
                    },
                    "x_label": {
                        "type": "string",
                        "description": "Label for the x-axis"
                    },
                    "y_label": {
                        "type": "string",
                        "description": "Label for the y-axis"
                    },
                    "output_path": {
                        "type": "string",
                        "description": "Path to save the chart image (e.g., 'charts/my_chart.png')"
                    },
                    "figsize": {
                        "type": "array",
                        "items": {
                            "type": "number"
                        },
                        "description": "Figure size as [width, height] in inches",
                        "default": [10, 6]
                    },
                    "show_grid": {
                        "type": "boolean",
                        "description": "Whether to show grid lines",
                        "default": true
                    },
                    "color_palette": {
                        "type": "string",
                        "description": "Color palette to use (e.g., 'viridis', 'plasma', 'inferno', 'magma', 'cividis')",
                        "default": "viridis"
                    }
                },
                "required": ["chart_type", "data", "output_path"]
            }
        }
    })
    @xml_schema(
        tag_name="create-chart",
        mappings=[
            {"param_name": "chart_type", "node_type": "attribute", "path": "."},
            {"param_name": "data", "node_type": "text", "path": "data"},
            {"param_name": "title", "node_type": "text", "path": "title"},
            {"param_name": "x_label", "node_type": "text", "path": "x-label"},
            {"param_name": "y_label", "node_type": "text", "path": "y-label"},
            {"param_name": "output_path", "node_type": "attribute", "path": "."},
            {"param_name": "figsize", "node_type": "text", "path": "figsize"},
            {"param_name": "show_grid", "node_type": "attribute", "path": "."},
            {"param_name": "color_palette", "node_type": "attribute", "path": "."}
        ],
        example='''
        <!-- Example: Create a bar chart and save it to charts/sales.png -->
        <create-chart chart_type="bar" output_path="charts/sales.png" show_grid="true" color_palette="viridis">
            <data>{"x": ["Jan", "Feb", "Mar", "Apr"], "y": [10, 15, 13, 17]}</data>
            <title>Monthly Sales</title>
            <x-label>Month</x-label>
            <y-label>Sales ($K)</y-label>
            <figsize>[12, 8]</figsize>
        </create-chart>
        '''
    )
    async def create_chart(self, 
                          chart_type: str, 
                          data: Dict, 
                          output_path: str,
                          title: Optional[str] = None, 
                          x_label: Optional[str] = None, 
                          y_label: Optional[str] = None, 
                          figsize: Optional[List[float]] = None,
                          show_grid: bool = True,
                          color_palette: str = "viridis") -> ToolResult:
        """Creates a chart or visualization from data and saves it to a file."""
        try:
            # Ensure sandbox is initialized
            await self._ensure_sandbox()
            
            # Install required packages if not already installed
            await self._ensure_visualization_packages()
            
            # Create Python script for visualization
            script_content = self._generate_visualization_script(
                chart_type, data, title, x_label, y_label, 
                figsize or [10, 6], show_grid, color_palette
            )
            
            # Save script to temporary file
            script_path = "/tmp/visualization_script.py"
            self.sandbox.fs.upload_file(script_path, script_content.encode('utf-8'))
            
            # Execute the script
            result = await self.sandbox.exec.start(
                command=f"python3 {script_path}",
                env={"MPLBACKEND": "Agg"}  # Non-interactive backend
            )
            
            # Wait for completion
            await result.wait()
            
            # Check if execution was successful
            if result.exit_code != 0:
                error_output = await result.get_output()
                return self.fail_response(f"Failed to create chart: {error_output}")
            
            # Clean output path
            cleaned_path = self.clean_path(output_path)
            full_output_path = f"{self.workspace_path}/{cleaned_path}"
            
            # Move the generated image to the requested location
            await self.sandbox.exec.start(
                command=f"mkdir -p $(dirname {full_output_path}) && mv /tmp/visualization.png {full_output_path}"
            )
            
            # Get image data for preview
            image_bytes = self.sandbox.fs.download_file(full_output_path)
            base64_image = base64.b64encode(image_bytes).decode('utf-8')
            
            # Add image to thread as a message for preview
            await self.thread_manager.add_message(
                thread_id=self.thread_id,
                type="image_context",
                content={
                    "mime_type": "image/png",
                    "base64": base64_image,
                    "file_path": cleaned_path
                },
                is_llm_message=False
            )
            
            return self.success_response(f"Chart created and saved to {cleaned_path}")
            
        except Exception as e:
            logger.error(f"Error creating chart: {str(e)}", exc_info=True)
            return self.fail_response(f"Failed to create chart: {str(e)}")
    
    async def _ensure_visualization_packages(self):
        """Ensure required visualization packages are installed."""
        packages = ["matplotlib", "seaborn", "pandas", "numpy"]
        
        # Check if packages are already installed
        for package in packages:
            result = await self.sandbox.exec.start(
                command=f"python3 -c 'import {package}' 2>/dev/null && echo 'installed' || echo 'not installed'"
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
    
    def _generate_visualization_script(self, 
                                      chart_type: str, 
                                      data: Dict, 
                                      title: Optional[str], 
                                      x_label: Optional[str], 
                                      y_label: Optional[str],
                                      figsize: List[float],
                                      show_grid: bool,
                                      color_palette: str) -> str:
        """Generate Python script for creating the visualization."""
        # Convert data to JSON string for embedding in script
        data_json = json.dumps(data)
        
        script = f"""
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
import json

# Set the style and color palette
sns.set_theme(style="whitegrid" if {show_grid} else "white")
sns.set_palette("{color_palette}")

# Parse the data
data = json.loads('{data_json}')
df = pd.DataFrame(data)

# Create figure with specified size
plt.figure(figsize=({figsize[0]}, {figsize[1]}))

# Create the chart based on type
if "{chart_type}" == "bar":
    if 'x' in data and 'y' in data:
        sns.barplot(x=data['x'], y=data['y'])
    else:
        sns.barplot(data=df)
elif "{chart_type}" == "line":
    if 'x' in data and 'y' in data:
        plt.plot(data['x'], data['y'])
    else:
        sns.lineplot(data=df)
elif "{chart_type}" == "scatter":
    if 'x' in data and 'y' in data:
        plt.scatter(data['x'], data['y'])
    else:
        sns.scatterplot(data=df)
elif "{chart_type}" == "pie":
    if 'values' in data and 'labels' in data:
        plt.pie(data['values'], labels=data['labels'], autopct='%1.1f%%')
    else:
        values = df.iloc[:, 0].values
        labels = df.index if df.index.name else None
        plt.pie(values, labels=labels, autopct='%1.1f%%')
elif "{chart_type}" == "heatmap":
    sns.heatmap(df, annot=True, cmap="{color_palette}")
elif "{chart_type}" == "histogram":
    if 'values' in data:
        plt.hist(data['values'], bins=10)
    else:
        for column in df.select_dtypes(include=[np.number]).columns:
            sns.histplot(df[column], label=column)
        plt.legend()
elif "{chart_type}" == "boxplot":
    sns.boxplot(data=df)
else:
    raise ValueError(f"Unsupported chart type: {chart_type}")

# Add title and labels if provided
"""
        
        if title:
            script += f'plt.title("{title}")\n'
        
        if x_label:
            script += f'plt.xlabel("{x_label}")\n'
        
        if y_label:
            script += f'plt.ylabel("{y_label}")\n'
        
        script += """
# Adjust layout
plt.tight_layout()

# Save the figure
plt.savefig('/tmp/visualization.png', dpi=300)
plt.close()
"""
        
        return script
    
    def success_response(self, message: str) -> ToolResult:
        """Create a success response."""
        return ToolResult(output=message)
    
    def fail_response(self, error: str) -> ToolResult:
        """Create a failure response."""
        return ToolResult(error=error)
