# Tool Integration Implementation

This document outlines the implementation for integrating the new Gradle, Maven, and Git tools with the Suna agent framework.

## Tool Registry Integration

To integrate the new tools with the agent framework, we need to update the tool registry in the `backend/agent/tools/tool_registry_update.py` file. This file is responsible for registering all tools with the agent's tool registry.

```python
def register_tools(registry):
    # Register existing tools
    registry.register_tool("terminal", TerminalTool)
    registry.register_tool("browser", BrowserTool)
    registry.register_tool("file", FileTool)
    registry.register_tool("image", ImageTool)
    registry.register_tool("search", SearchTool)
    registry.register_tool("code", CodeTool)
    registry.register_tool("document", DocumentTool)
    registry.register_tool("ocr", OcrTool)
    registry.register_tool("task_planner", TaskPlannerTool)
    registry.register_tool("data_visualization", DataVisualizationTool)
    registry.register_tool("speech", SpeechTool)
    
    # Register new tools
    registry.register_tool("gradle", GradleTool)
    registry.register_tool("maven", MavenTool)
    registry.register_tool("git", GitTool)
```

## Tool Initialization

The tools need to be properly initialized with the agent's thread manager and project ID. This is handled in the `backend/agent/run.py` file:

```python
def initialize_tools(project_id, thread_manager):
    tools = {}
    
    # Initialize existing tools
    tools["terminal"] = TerminalTool(project_id, thread_manager)
    tools["browser"] = BrowserTool(project_id, thread_manager)
    tools["file"] = FileTool(project_id, thread_manager)
    tools["image"] = ImageTool(project_id, thread_manager)
    tools["search"] = SearchTool(project_id, thread_manager)
    tools["code"] = CodeTool(project_id, thread_manager)
    tools["document"] = DocumentTool(project_id, thread_manager)
    tools["ocr"] = OcrTool(project_id, thread_manager)
    tools["task_planner"] = TaskPlannerTool(project_id, thread_manager)
    tools["data_visualization"] = DataVisualizationTool(project_id, thread_manager)
    tools["speech"] = SpeechTool(project_id, thread_manager)
    
    # Initialize new tools
    tools["gradle"] = GradleTool(project_id, thread_manager)
    tools["maven"] = MavenTool(project_id, thread_manager)
    tools["git"] = GitTool(project_id, thread_manager)
    
    # Initialize all tools with references to other tools
    for tool_name, tool in tools.items():
        tool.initialize(tools)
    
    return tools
```

## Tool Import Statements

We need to add import statements for the new tools in the appropriate files:

### In `backend/agent/tools/__init__.py`:

```python
from .terminal_tool import TerminalTool
from .browser_tool import BrowserTool
from .file_tool import FileTool
from .image_tool import ImageTool
from .search_tool import SearchTool
from .code_tool import CodeTool
from .document_tool import DocumentTool
from .ocr_tool import OcrTool
from .task_planner_tool import TaskPlannerTool
from .data_visualization_tool import DataVisualizationTool
from .speech_tool import SpeechTool
from .anthropic_browser_tool import AnthropicBrowserTool
from .human_interaction_tool import HumanInteractionTool

# Import new tools
from .gradle_tool import GradleTool
from .maven_tool import MavenTool
from .git_tool import GitTool
```

### In `backend/agent/run.py`:

```python
from .tools import (
    TerminalTool, BrowserTool, FileTool, ImageTool, SearchTool, 
    CodeTool, DocumentTool, OcrTool, TaskPlannerTool, 
    DataVisualizationTool, SpeechTool, AnthropicBrowserTool,
    HumanInteractionTool, GradleTool, MavenTool, GitTool
)
```

## Tool Configuration

The tools need to be properly configured in the agent's configuration file. This is handled in the `backend/agent/config.py` file:

```python
def get_tool_config():
    return {
        "terminal": {
            "enabled": True,
            "config": {}
        },
        "browser": {
            "enabled": True,
            "config": {}
        },
        "file": {
            "enabled": True,
            "config": {}
        },
        "image": {
            "enabled": True,
            "config": {}
        },
        "search": {
            "enabled": True,
            "config": {}
        },
        "code": {
            "enabled": True,
            "config": {}
        },
        "document": {
            "enabled": True,
            "config": {}
        },
        "ocr": {
            "enabled": True,
            "config": {}
        },
        "task_planner": {
            "enabled": True,
            "config": {}
        },
        "data_visualization": {
            "enabled": True,
            "config": {}
        },
        "speech": {
            "enabled": True,
            "config": {}
        },
        "anthropic_browser": {
            "enabled": True,
            "config": {}
        },
        "human_interaction": {
            "enabled": True,
            "config": {}
        },
        # New tool configurations
        "gradle": {
            "enabled": True,
            "config": {
                "auto_install": True,
                "default_version": "7.6.1",
                "cache_dir": "/tmp/gradle_cache"
            }
        },
        "maven": {
            "enabled": True,
            "config": {
                "auto_install": True,
                "default_version": "3.9.0",
                "cache_dir": "/tmp/maven_cache"
            }
        },
        "git": {
            "enabled": True,
            "config": {
                "auto_install": True
            }
        }
    }
```

## Tool Schema Registration

The tools need to register their XML schemas with the agent's schema registry. This is handled in the `backend/agent/schema_registry.py` file:

```python
def register_schemas(registry):
    # Register existing schemas
    registry.register_schema(TerminalTool.get_xml_schema())
    registry.register_schema(BrowserTool.get_xml_schema())
    registry.register_schema(FileTool.get_xml_schema())
    registry.register_schema(ImageTool.get_xml_schema())
    registry.register_schema(SearchTool.get_xml_schema())
    registry.register_schema(CodeTool.get_xml_schema())
    registry.register_schema(DocumentTool.get_xml_schema())
    registry.register_schema(OcrTool.get_xml_schema())
    registry.register_schema(TaskPlannerTool.get_xml_schema())
    registry.register_schema(DataVisualizationTool.get_xml_schema())
    registry.register_schema(SpeechTool.get_xml_schema())
    registry.register_schema(AnthropicBrowserTool.get_xml_schema())
    registry.register_schema(HumanInteractionTool.get_xml_schema())
    
    # Register new schemas
    registry.register_schema(GradleTool.get_xml_schema())
    registry.register_schema(MavenTool.get_xml_schema())
    registry.register_schema(GitTool.get_xml_schema())
```

## Tool Dependencies

The new tools may have dependencies that need to be installed. We need to update the `requirements.txt` file to include these dependencies:

```
# Existing dependencies
...

# New dependencies for Gradle, Maven, and Git tools
py4j>=0.10.9
gitpython>=3.1.30
```

## Tool Documentation

The tools need to be properly documented in the agent's documentation. This is handled in the `docs/tools.md` file:

```markdown
# Suna Tools

## Core Tools

...

## Java Development Tools

### Gradle Tool

The Gradle tool provides functionality for managing Gradle-based Java projects. It can be used to build, test, and manage dependencies for Java projects.

#### Functions

- `init_project`: Initialize a new Gradle project
- `build`: Build a Gradle project
- `test`: Run tests for a Gradle project
- `dependencies`: List dependencies for a Gradle project
- `add_dependency`: Add a dependency to a Gradle project
- `run_task`: Run a Gradle task
- `wrapper`: Generate Gradle wrapper files

### Maven Tool

The Maven tool provides functionality for managing Maven-based Java projects. It can be used to build, test, and manage dependencies for Java projects.

#### Functions

- `init_project`: Initialize a new Maven project
- `build`: Build a Maven project
- `test`: Run tests for a Maven project
- `dependencies`: List dependencies for a Maven project
- `add_dependency`: Add a dependency to a Maven project
- `run_goal`: Run a Maven goal
- `generate_pom`: Generate a POM file

### Git Tool

The Git tool provides functionality for managing Git repositories. It can be used to initialize, clone, commit, push, and pull from Git repositories.

#### Functions

- `init_repo`: Initialize a new Git repository
- `clone_repo`: Clone a Git repository
- `create_branch`: Create a new branch
- `checkout_branch`: Checkout a branch
- `list_branches`: List branches in the repository
- `add_files`: Add files to the staging area
- `commit`: Commit staged changes
- `get_commit_history`: Get commit history
- `add_remote`: Add a remote repository
- `list_remotes`: List remote repositories
- `push`: Push changes to a remote repository
- `pull`: Pull changes from a remote repository
- `get_status`: Get repository status
- `get_diff`: Get diff of changes
```

## Integration Testing

To ensure that the new tools are properly integrated with the agent framework, we need to add integration tests for each tool. These tests should verify that the tools can be initialized, registered, and used by the agent.

### Gradle Tool Test

```python
def test_gradle_tool():
    # Initialize the tool
    project_id = "test_project"
    thread_manager = ThreadManager()
    gradle_tool = GradleTool(project_id, thread_manager)
    
    # Test initialization
    tools = {"terminal": TerminalTool(project_id, thread_manager)}
    gradle_tool.initialize(tools)
    
    # Test schema registration
    schema = GradleTool.get_xml_schema()
    assert schema["name"] == "gradle"
    
    # Test basic functionality
    result = gradle_tool.init_project("/tmp/gradle_test", "com.example", "test-project")
    assert result.get("status") == "success"
```

### Maven Tool Test

```python
def test_maven_tool():
    # Initialize the tool
    project_id = "test_project"
    thread_manager = ThreadManager()
    maven_tool = MavenTool(project_id, thread_manager)
    
    # Test initialization
    tools = {"terminal": TerminalTool(project_id, thread_manager)}
    maven_tool.initialize(tools)
    
    # Test schema registration
    schema = MavenTool.get_xml_schema()
    assert schema["name"] == "maven"
    
    # Test basic functionality
    result = maven_tool.init_project("/tmp/maven_test", "com.example", "test-project")
    assert result.get("status") == "success"
```

### Git Tool Test

```python
def test_git_tool():
    # Initialize the tool
    project_id = "test_project"
    thread_manager = ThreadManager()
    git_tool = GitTool(project_id, thread_manager)
    
    # Test initialization
    tools = {"terminal": TerminalTool(project_id, thread_manager)}
    git_tool.initialize(tools)
    
    # Test schema registration
    schema = GitTool.get_xml_schema()
    assert schema["name"] == "git"
    
    # Test basic functionality
    result = git_tool.init_repo("/tmp/git_test")
    assert result.get("status") == "success"
```

## Conclusion

By implementing the above changes, we can successfully integrate the new Gradle, Maven, and Git tools with the Suna agent framework. These tools will provide Java developers with powerful capabilities for managing their projects, dependencies, and version control directly through the agent.
