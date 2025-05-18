"""
Planning tool for task decomposition and planning within the sandbox.
"""

from typing import Dict, List, Any, Optional
import json
import uuid

from agentpress.tool import ToolResult, openapi_schema, xml_schema
from sandbox.tool_base import SandboxToolsBase
from agentpress.thread_manager import ThreadManager
from utils.logger import logger

class PlanningTool(SandboxToolsBase):
    """Tool for task decomposition and planning."""

    def __init__(self, project_id: str, thread_id: str, thread_manager: ThreadManager):
        super().__init__(project_id, thread_manager)
        self.thread_id = thread_id
        self.thread_manager = thread_manager
        self.plans_dir = "/workspace/.plans"

    @openapi_schema({
        "type": "function",
        "function": {
            "name": "create_plan",
            "description": "Creates a structured plan for a complex task, breaking it down into steps.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task": {
                        "type": "string",
                        "description": "The complex task that needs to be planned"
                    },
                    "num_steps": {
                        "type": "integer",
                        "description": "Suggested number of steps for the plan (optional)",
                        "default": 5
                    },
                    "plan_name": {
                        "type": "string",
                        "description": "Name for the plan (optional, will be auto-generated if not provided)"
                    },
                    "save_to_file": {
                        "type": "boolean",
                        "description": "Whether to save the plan to a file",
                        "default": true
                    }
                },
                "required": ["task"]
            }
        }
    })
    @xml_schema(
        tag_name="create-plan",
        mappings=[
            {"param_name": "task", "node_type": "text", "path": "task"},
            {"param_name": "num_steps", "node_type": "attribute", "path": "."},
            {"param_name": "plan_name", "node_type": "attribute", "path": "."},
            {"param_name": "save_to_file", "node_type": "attribute", "path": "."}
        ],
        example='''
        <!-- Example: Create a plan for building a website -->
        <create-plan num_steps="7" plan_name="website_development" save_to_file="true">
            <task>Build a responsive e-commerce website with product catalog, shopping cart, and payment processing</task>
        </create-plan>
        '''
    )
    async def create_plan(self, 
                         task: str, 
                         num_steps: int = 5,
                         plan_name: Optional[str] = None,
                         save_to_file: bool = True) -> ToolResult:
        """Creates a structured plan for a complex task, breaking it down into steps."""
        try:
            # Ensure sandbox is initialized
            await self._ensure_sandbox()
            
            # Generate a plan name if not provided
            if not plan_name:
                plan_name = f"plan_{uuid.uuid4().hex[:8]}"
            
            # Create plans directory if it doesn't exist
            await self.sandbox.exec.start(
                command=f"mkdir -p {self.plans_dir}"
            )
            
            # Generate the plan using the agent's own reasoning
            plan_steps = self._generate_plan_steps(task, num_steps)
            
            # Create plan object
            plan = {
                "id": str(uuid.uuid4()),
                "name": plan_name,
                "task": task,
                "steps": plan_steps,
                "created_at": self._get_timestamp(),
                "status": "created"
            }
            
            # Save plan to file if requested
            if save_to_file:
                plan_path = f"{self.plans_dir}/{plan_name}.json"
                plan_content = json.dumps(plan, indent=2)
                self.sandbox.fs.upload_file(plan_path, plan_content.encode('utf-8'))
            
            # Format response
            response = f"Created plan '{plan_name}' with {len(plan_steps)} steps:\n\n"
            for i, step in enumerate(plan_steps):
                response += f"{i+1}. {step['description']}\n"
            
            if save_to_file:
                response += f"\nPlan saved to {self.plans_dir}/{plan_name}.json"
            
            return self.success_response(response)
            
        except Exception as e:
            logger.error(f"Error creating plan: {str(e)}", exc_info=True)
            return self.fail_response(f"Failed to create plan: {str(e)}")
    
    @openapi_schema({
        "type": "function",
        "function": {
            "name": "update_plan_step",
            "description": "Updates the status of a step in an existing plan.",
            "parameters": {
                "type": "object",
                "properties": {
                    "plan_name": {
                        "type": "string",
                        "description": "Name of the plan"
                    },
                    "step_index": {
                        "type": "integer",
                        "description": "Index of the step to update (1-based)"
                    },
                    "status": {
                        "type": "string",
                        "description": "New status for the step",
                        "enum": ["pending", "in_progress", "completed", "blocked"]
                    },
                    "notes": {
                        "type": "string",
                        "description": "Optional notes to add to the step"
                    }
                },
                "required": ["plan_name", "step_index", "status"]
            }
        }
    })
    @xml_schema(
        tag_name="update-plan-step",
        mappings=[
            {"param_name": "plan_name", "node_type": "attribute", "path": "."},
            {"param_name": "step_index", "node_type": "attribute", "path": "."},
            {"param_name": "status", "node_type": "attribute", "path": "."},
            {"param_name": "notes", "node_type": "text", "path": "notes"}
        ],
        example='''
        <!-- Example: Update step 2 of the website development plan to completed -->
        <update-plan-step plan_name="website_development" step_index="2" status="completed">
            <notes>Completed the database schema design with all required tables and relationships</notes>
        </update-plan-step>
        '''
    )
    async def update_plan_step(self,
                              plan_name: str,
                              step_index: int,
                              status: str,
                              notes: Optional[str] = None) -> ToolResult:
        """Updates the status of a step in an existing plan."""
        try:
            # Ensure sandbox is initialized
            await self._ensure_sandbox()
            
            # Check if plan exists
            plan_path = f"{self.plans_dir}/{plan_name}.json"
            try:
                plan_content = self.sandbox.fs.download_file(plan_path)
                plan = json.loads(plan_content.decode('utf-8'))
            except Exception:
                return self.fail_response(f"Plan '{plan_name}' not found")
            
            # Validate step index
            if step_index < 1 or step_index > len(plan['steps']):
                return self.fail_response(f"Invalid step index: {step_index}. Plan has {len(plan['steps'])} steps.")
            
            # Update step status
            step = plan['steps'][step_index - 1]
            step['status'] = status
            step['updated_at'] = self._get_timestamp()
            
            # Add notes if provided
            if notes:
                step['notes'] = notes
            
            # Save updated plan
            plan_content = json.dumps(plan, indent=2)
            self.sandbox.fs.upload_file(plan_path, plan_content.encode('utf-8'))
            
            return self.success_response(f"Updated step {step_index} of plan '{plan_name}' to status '{status}'")
            
        except Exception as e:
            logger.error(f"Error updating plan step: {str(e)}", exc_info=True)
            return self.fail_response(f"Failed to update plan step: {str(e)}")
    
    @openapi_schema({
        "type": "function",
        "function": {
            "name": "get_plan",
            "description": "Retrieves an existing plan.",
            "parameters": {
                "type": "object",
                "properties": {
                    "plan_name": {
                        "type": "string",
                        "description": "Name of the plan to retrieve"
                    }
                },
                "required": ["plan_name"]
            }
        }
    })
    @xml_schema(
        tag_name="get-plan",
        mappings=[
            {"param_name": "plan_name", "node_type": "attribute", "path": "."}
        ],
        example='''
        <!-- Example: Retrieve the website development plan -->
        <get-plan plan_name="website_development"></get-plan>
        '''
    )
    async def get_plan(self, plan_name: str) -> ToolResult:
        """Retrieves an existing plan."""
        try:
            # Ensure sandbox is initialized
            await self._ensure_sandbox()
            
            # Check if plan exists
            plan_path = f"{self.plans_dir}/{plan_name}.json"
            try:
                plan_content = self.sandbox.fs.download_file(plan_path)
                plan = json.loads(plan_content.decode('utf-8'))
            except Exception:
                return self.fail_response(f"Plan '{plan_name}' not found")
            
            # Format response
            response = f"Plan: {plan['name']}\n"
            response += f"Task: {plan['task']}\n"
            response += f"Created: {plan['created_at']}\n\n"
            response += "Steps:\n"
            
            for i, step in enumerate(plan['steps']):
                status = step.get('status', 'pending')
                response += f"{i+1}. [{status}] {step['description']}\n"
                if 'notes' in step:
                    response += f"   Notes: {step['notes']}\n"
            
            return self.success_response(response)
            
        except Exception as e:
            logger.error(f"Error retrieving plan: {str(e)}", exc_info=True)
            return self.fail_response(f"Failed to retrieve plan: {str(e)}")
    
    def _generate_plan_steps(self, task: str, num_steps: int) -> List[Dict[str, Any]]:
        """Generate plan steps for the given task."""
        # In a real implementation, this might use the LLM to generate steps
        # For now, we'll create a simple template-based plan
        
        steps = []
        
        # Create a basic plan structure based on the task type
        if "website" in task.lower():
            steps = [
                {"description": "Analyze requirements and create project specifications", "status": "pending"},
                {"description": "Design database schema and data models", "status": "pending"},
                {"description": "Create wireframes and UI/UX design", "status": "pending"},
                {"description": "Implement frontend components and pages", "status": "pending"},
                {"description": "Implement backend API and business logic", "status": "pending"},
                {"description": "Integrate payment processing and security features", "status": "pending"},
                {"description": "Test functionality and fix bugs", "status": "pending"},
                {"description": "Deploy and configure production environment", "status": "pending"}
            ]
        elif "research" in task.lower() or "report" in task.lower():
            steps = [
                {"description": "Define research questions and objectives", "status": "pending"},
                {"description": "Gather relevant sources and materials", "status": "pending"},
                {"description": "Analyze information and identify key insights", "status": "pending"},
                {"description": "Organize findings into a coherent structure", "status": "pending"},
                {"description": "Write draft report with supporting evidence", "status": "pending"},
                {"description": "Create visualizations and supporting materials", "status": "pending"},
                {"description": "Review, edit, and finalize report", "status": "pending"}
            ]
        elif "data" in task.lower() or "analysis" in task.lower():
            steps = [
                {"description": "Define analysis objectives and questions", "status": "pending"},
                {"description": "Collect and import relevant data", "status": "pending"},
                {"description": "Clean and preprocess data", "status": "pending"},
                {"description": "Perform exploratory data analysis", "status": "pending"},
                {"description": "Apply statistical methods or machine learning", "status": "pending"},
                {"description": "Visualize results and key findings", "status": "pending"},
                {"description": "Interpret results and draw conclusions", "status": "pending"},
                {"description": "Document methodology and findings", "status": "pending"}
            ]
        else:
            # Generic plan for any task
            steps = [
                {"description": "Define project scope and objectives", "status": "pending"},
                {"description": "Research and gather necessary information", "status": "pending"},
                {"description": "Develop initial approach and methodology", "status": "pending"},
                {"description": "Implement core functionality or content", "status": "pending"},
                {"description": "Test and validate results", "status": "pending"},
                {"description": "Refine and improve based on feedback", "status": "pending"},
                {"description": "Finalize and deliver completed work", "status": "pending"}
            ]
        
        # Adjust number of steps if needed
        if len(steps) > num_steps:
            steps = steps[:num_steps]
        
        # Add timestamps
        timestamp = self._get_timestamp()
        for step in steps:
            step["created_at"] = timestamp
        
        return steps
    
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
