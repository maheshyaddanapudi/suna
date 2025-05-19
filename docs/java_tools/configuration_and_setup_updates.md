# Configuration and Setup Updates for New Tools

This document outlines the necessary configuration and setup updates to ensure the new Gradle, Maven, and Git tools are properly integrated into the Suna platform.

## Configuration File Updates

### 1. `backend/agent/config.yaml`

The main configuration file needs to be updated to include settings for the new tools:

```yaml
tools:
  # Existing tool configurations...
  
  # Java Development Tools
  gradle:
    enabled: true
    auto_install: true
    default_version: "7.6.1"
    cache_dir: "${HOME}/.gradle"
    wrapper_enabled: true
    
  maven:
    enabled: true
    auto_install: true
    default_version: "3.9.0"
    cache_dir: "${HOME}/.m2"
    settings_file: "${HOME}/.m2/settings.xml"
    
  git:
    enabled: true
    auto_install: true
    default_user_name: "${USER}"
    default_user_email: "${USER}@localhost"
    credential_helper: "cache"
```

### 2. `backend/agent/environment.py`

Update the environment setup to include Java environment detection:

```python
def setup_environment():
    """Set up the environment for the agent."""
    # Existing environment setup...
    
    # Set up Java environment
    setup_java_environment()
    
    # Set up Gradle environment
    setup_gradle_environment()
    
    # Set up Maven environment
    setup_maven_environment()
    
    # Set up Git environment
    setup_git_environment()

def setup_java_environment():
    """Set up the Java environment."""
    # Check if JAVA_HOME is set
    java_home = os.environ.get("JAVA_HOME")
    if not java_home:
        # Try to find Java installation
        java_path = find_java_installation()
        if java_path:
            os.environ["JAVA_HOME"] = java_path
            logger.info(f"Set JAVA_HOME to {java_path}")
        else:
            logger.warning("JAVA_HOME not set and Java installation not found")
    else:
        logger.info(f"Using existing JAVA_HOME: {java_home}")
    
    # Add JAVA_HOME/bin to PATH if not already there
    if java_home:
        java_bin = os.path.join(java_home, "bin")
        if java_bin not in os.environ.get("PATH", ""):
            os.environ["PATH"] = f"{java_bin}:{os.environ.get('PATH', '')}"
            logger.info(f"Added {java_bin} to PATH")

def find_java_installation():
    """Find Java installation on the system."""
    # Common Java installation locations
    common_locations = [
        "/usr/lib/jvm/default-java",
        "/usr/lib/jvm/java-11-openjdk-amd64",
        "/usr/lib/jvm/java-8-openjdk-amd64",
        "/Library/Java/JavaVirtualMachines",  # macOS
        "C:\\Program Files\\Java"  # Windows
    ]
    
    # Check common locations
    for location in common_locations:
        if os.path.exists(location):
            # For macOS and Windows, need to find the specific JDK directory
            if location in ["/Library/Java/JavaVirtualMachines", "C:\\Program Files\\Java"]:
                # Find the latest JDK
                jdk_dirs = [d for d in os.listdir(location) if d.startswith("jdk")]
                if jdk_dirs:
                    # Sort by version (assuming format like jdk-11.0.1)
                    jdk_dirs.sort(reverse=True)
                    if location == "/Library/Java/JavaVirtualMachines":
                        return os.path.join(location, jdk_dirs[0], "Contents/Home")
                    else:  # Windows
                        return os.path.join(location, jdk_dirs[0])
            else:
                return location
    
    # Try to find java executable in PATH
    try:
        java_path = subprocess.check_output(["which", "java"]).decode().strip()
        # java_path is typically /usr/bin/java, which is a symlink
        # Follow the symlink to find the actual Java home
        if os.path.islink(java_path):
            java_path = os.path.realpath(java_path)
            # Remove /bin/java from the path
            return os.path.dirname(os.path.dirname(java_path))
    except subprocess.CalledProcessError:
        pass
    
    return None

def setup_gradle_environment():
    """Set up the Gradle environment."""
    # Check if GRADLE_HOME is set
    gradle_home = os.environ.get("GRADLE_HOME")
    if not gradle_home:
        # Try to find Gradle installation
        gradle_path = find_gradle_installation()
        if gradle_path:
            os.environ["GRADLE_HOME"] = gradle_path
            logger.info(f"Set GRADLE_HOME to {gradle_path}")
        else:
            logger.info("GRADLE_HOME not set and Gradle installation not found")
    else:
        logger.info(f"Using existing GRADLE_HOME: {gradle_home}")
    
    # Add GRADLE_HOME/bin to PATH if not already there
    if gradle_home:
        gradle_bin = os.path.join(gradle_home, "bin")
        if gradle_bin not in os.environ.get("PATH", ""):
            os.environ["PATH"] = f"{gradle_bin}:{os.environ.get('PATH', '')}"
            logger.info(f"Added {gradle_bin} to PATH")

def find_gradle_installation():
    """Find Gradle installation on the system."""
    # Common Gradle installation locations
    common_locations = [
        "/usr/share/gradle",
        "/opt/gradle",
        os.path.expanduser("~/.gradle")
    ]
    
    # Check common locations
    for location in common_locations:
        if os.path.exists(location):
            return location
    
    # Try to find gradle executable in PATH
    try:
        gradle_path = subprocess.check_output(["which", "gradle"]).decode().strip()
        # gradle_path is typically /usr/bin/gradle, which might be a symlink
        # Follow the symlink to find the actual Gradle home
        if os.path.islink(gradle_path):
            gradle_path = os.path.realpath(gradle_path)
            # Remove /bin/gradle from the path
            return os.path.dirname(os.path.dirname(gradle_path))
        else:
            # If not a symlink, it's probably a wrapper script
            # Just return the directory containing the script
            return os.path.dirname(os.path.dirname(gradle_path))
    except subprocess.CalledProcessError:
        pass
    
    return None

def setup_maven_environment():
    """Set up the Maven environment."""
    # Check if MAVEN_HOME is set
    maven_home = os.environ.get("MAVEN_HOME")
    if not maven_home:
        # Try to find Maven installation
        maven_path = find_maven_installation()
        if maven_path:
            os.environ["MAVEN_HOME"] = maven_path
            logger.info(f"Set MAVEN_HOME to {maven_path}")
        else:
            logger.info("MAVEN_HOME not set and Maven installation not found")
    else:
        logger.info(f"Using existing MAVEN_HOME: {maven_home}")
    
    # Add MAVEN_HOME/bin to PATH if not already there
    if maven_home:
        maven_bin = os.path.join(maven_home, "bin")
        if maven_bin not in os.environ.get("PATH", ""):
            os.environ["PATH"] = f"{maven_bin}:{os.environ.get('PATH', '')}"
            logger.info(f"Added {maven_bin} to PATH")

def find_maven_installation():
    """Find Maven installation on the system."""
    # Common Maven installation locations
    common_locations = [
        "/usr/share/maven",
        "/opt/maven",
        os.path.expanduser("~/.m2")
    ]
    
    # Check common locations
    for location in common_locations:
        if os.path.exists(location):
            return location
    
    # Try to find mvn executable in PATH
    try:
        mvn_path = subprocess.check_output(["which", "mvn"]).decode().strip()
        # mvn_path is typically /usr/bin/mvn, which might be a symlink
        # Follow the symlink to find the actual Maven home
        if os.path.islink(mvn_path):
            mvn_path = os.path.realpath(mvn_path)
            # Remove /bin/mvn from the path
            return os.path.dirname(os.path.dirname(mvn_path))
        else:
            # If not a symlink, it's probably a wrapper script
            # Just return the directory containing the script
            return os.path.dirname(os.path.dirname(mvn_path))
    except subprocess.CalledProcessError:
        pass
    
    return None

def setup_git_environment():
    """Set up the Git environment."""
    # Check if git is installed
    try:
        subprocess.check_output(["which", "git"])
        logger.info("Git is installed")
    except subprocess.CalledProcessError:
        logger.warning("Git is not installed")
```

## Dependency Management Updates

### 1. `requirements.txt`

Update the requirements file to include dependencies for the new tools:

```
# Existing dependencies...

# Java Development Tool Dependencies
py4j>=0.10.9
gitpython>=3.1.30
```

### 2. `setup.py`

Update the setup script to include the new tools and their dependencies:

```python
setup(
    name="suna",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        # Existing dependencies...
        
        # Java Development Tool Dependencies
        "py4j>=0.10.9",
        "gitpython>=3.1.30",
    ],
    extras_require={
        "dev": [
            # Existing dev dependencies...
        ],
        "java": [
            "py4j>=0.10.9",
            "gitpython>=3.1.30",
        ],
    },
)
```

## Installation Script Updates

### 1. `scripts/install.sh`

Update the installation script to include the new tools:

```bash
#!/bin/bash

# Existing installation steps...

# Check for Java installation
echo "Checking for Java installation..."
if command -v java &> /dev/null; then
    echo "Java is installed"
    java -version
else
    echo "Java is not installed. Installing OpenJDK 11..."
    sudo apt-get update
    sudo apt-get install -y openjdk-11-jdk
    echo "Java installed successfully"
    java -version
fi

# Check for Gradle installation
echo "Checking for Gradle installation..."
if command -v gradle &> /dev/null; then
    echo "Gradle is installed"
    gradle --version
else
    echo "Gradle is not installed. Installing Gradle 7.6.1..."
    wget -q https://services.gradle.org/distributions/gradle-7.6.1-bin.zip -P /tmp
    sudo unzip -d /opt /tmp/gradle-7.6.1-bin.zip
    sudo ln -s /opt/gradle-7.6.1/bin/gradle /usr/bin/gradle
    echo "Gradle installed successfully"
    gradle --version
fi

# Check for Maven installation
echo "Checking for Maven installation..."
if command -v mvn &> /dev/null; then
    echo "Maven is installed"
    mvn --version
else
    echo "Maven is not installed. Installing Maven 3.9.0..."
    wget -q https://dlcdn.apache.org/maven/maven-3/3.9.0/binaries/apache-maven-3.9.0-bin.tar.gz -P /tmp
    sudo tar -xf /tmp/apache-maven-3.9.0-bin.tar.gz -C /opt
    sudo ln -s /opt/apache-maven-3.9.0/bin/mvn /usr/bin/mvn
    echo "Maven installed successfully"
    mvn --version
fi

# Check for Git installation
echo "Checking for Git installation..."
if command -v git &> /dev/null; then
    echo "Git is installed"
    git --version
else
    echo "Git is not installed. Installing Git..."
    sudo apt-get update
    sudo apt-get install -y git
    echo "Git installed successfully"
    git --version
fi

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

echo "Installation completed successfully"
```

## Docker Configuration Updates

### 1. `Dockerfile`

Update the Dockerfile to include the new tools:

```dockerfile
FROM python:3.9-slim

# Existing setup...

# Install Java, Gradle, Maven, and Git
RUN apt-get update && apt-get install -y \
    openjdk-11-jdk \
    git \
    wget \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Install Gradle
RUN wget -q https://services.gradle.org/distributions/gradle-7.6.1-bin.zip -P /tmp \
    && unzip -d /opt /tmp/gradle-7.6.1-bin.zip \
    && ln -s /opt/gradle-7.6.1/bin/gradle /usr/bin/gradle \
    && rm /tmp/gradle-7.6.1-bin.zip

# Install Maven
RUN wget -q https://dlcdn.apache.org/maven/maven-3/3.9.0/binaries/apache-maven-3.9.0-bin.tar.gz -P /tmp \
    && tar -xf /tmp/apache-maven-3.9.0-bin.tar.gz -C /opt \
    && ln -s /opt/apache-maven-3.9.0/bin/mvn /usr/bin/mvn \
    && rm /tmp/apache-maven-3.9.0-bin.tar.gz

# Set environment variables
ENV JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
ENV GRADLE_HOME=/opt/gradle-7.6.1
ENV MAVEN_HOME=/opt/apache-maven-3.9.0
ENV PATH=$JAVA_HOME/bin:$GRADLE_HOME/bin:$MAVEN_HOME/bin:$PATH

# Existing setup continues...
```

## Tool Registry Updates

### 1. `backend/agent/tools/tool_registry.py`

Update the tool registry to include the new tools:

```python
class ToolRegistry:
    """Registry for tools."""
    
    def __init__(self):
        self.tools = {}
    
    def register_tool(self, name, tool_class):
        """Register a tool."""
        self.tools[name] = tool_class
    
    def get_tool(self, name):
        """Get a tool by name."""
        return self.tools.get(name)
    
    def get_all_tools(self):
        """Get all registered tools."""
        return self.tools
    
    def get_tool_names(self):
        """Get all registered tool names."""
        return list(self.tools.keys())

# Create a singleton instance
registry = ToolRegistry()

# Register core tools
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

# Register Java development tools
from .gradle_tool import GradleTool
from .maven_tool import MavenTool
from .git_tool import GitTool

# Register all tools
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
registry.register_tool("anthropic_browser", AnthropicBrowserTool)
registry.register_tool("human_interaction", HumanInteractionTool)

# Register Java development tools
registry.register_tool("gradle", GradleTool)
registry.register_tool("maven", MavenTool)
registry.register_tool("git", GitTool)
```

## Tool Schema Updates

### 1. `backend/agent/schema_registry.py`

Update the schema registry to include the new tools:

```python
class SchemaRegistry:
    """Registry for tool schemas."""
    
    def __init__(self):
        self.schemas = {}
    
    def register_schema(self, schema):
        """Register a schema."""
        self.schemas[schema["name"]] = schema
    
    def get_schema(self, name):
        """Get a schema by name."""
        return self.schemas.get(name)
    
    def get_all_schemas(self):
        """Get all registered schemas."""
        return self.schemas
    
    def get_schema_names(self):
        """Get all registered schema names."""
        return list(self.schemas.keys())

# Create a singleton instance
registry = SchemaRegistry()

# Register core tool schemas
from .tools.terminal_tool import TerminalTool
from .tools.browser_tool import BrowserTool
from .tools.file_tool import FileTool
from .tools.image_tool import ImageTool
from .tools.search_tool import SearchTool
from .tools.code_tool import CodeTool
from .tools.document_tool import DocumentTool
from .tools.ocr_tool import OcrTool
from .tools.task_planner_tool import TaskPlannerTool
from .tools.data_visualization_tool import DataVisualizationTool
from .tools.speech_tool import SpeechTool
from .tools.anthropic_browser_tool import AnthropicBrowserTool
from .tools.human_interaction_tool import HumanInteractionTool

# Register Java development tool schemas
from .tools.gradle_tool import GradleTool
from .tools.maven_tool import MavenTool
from .tools.git_tool import GitTool

# Register all schemas
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

# Register Java development tool schemas
registry.register_schema(GradleTool.get_xml_schema())
registry.register_schema(MavenTool.get_xml_schema())
registry.register_schema(GitTool.get_xml_schema())
```

## Sandbox Environment Updates

### 1. `backend/agent/sandbox/environment.py`

Update the sandbox environment to include the new tools:

```python
def setup_sandbox_environment():
    """Set up the sandbox environment."""
    # Existing setup...
    
    # Set up Java environment
    setup_java_environment()
    
    # Set up Gradle environment
    setup_gradle_environment()
    
    # Set up Maven environment
    setup_maven_environment()
    
    # Set up Git environment
    setup_git_environment()

def setup_java_environment():
    """Set up the Java environment in the sandbox."""
    # Check if Java is installed
    java_installed = subprocess.run(["which", "java"], capture_output=True).returncode == 0
    
    if not java_installed:
        logger.info("Installing Java in sandbox...")
        subprocess.run(["apt-get", "update"], check=True)
        subprocess.run(["apt-get", "install", "-y", "openjdk-11-jdk"], check=True)
        logger.info("Java installed successfully")
    
    # Set JAVA_HOME
    java_home = subprocess.run(["readlink", "-f", "/usr/bin/java"], capture_output=True, text=True).stdout.strip()
    java_home = os.path.dirname(os.path.dirname(java_home))
    os.environ["JAVA_HOME"] = java_home
    logger.info(f"Set JAVA_HOME to {java_home}")

def setup_gradle_environment():
    """Set up the Gradle environment in the sandbox."""
    # Check if Gradle is installed
    gradle_installed = subprocess.run(["which", "gradle"], capture_output=True).returncode == 0
    
    if not gradle_installed:
        logger.info("Installing Gradle in sandbox...")
        subprocess.run(["wget", "-q", "https://services.gradle.org/distributions/gradle-7.6.1-bin.zip", "-P", "/tmp"], check=True)
        subprocess.run(["unzip", "-d", "/opt", "/tmp/gradle-7.6.1-bin.zip"], check=True)
        subprocess.run(["ln", "-s", "/opt/gradle-7.6.1/bin/gradle", "/usr/bin/gradle"], check=True)
        logger.info("Gradle installed successfully")
    
    # Set GRADLE_HOME
    gradle_home = "/opt/gradle-7.6.1"
    os.environ["GRADLE_HOME"] = gradle_home
    logger.info(f"Set GRADLE_HOME to {gradle_home}")

def setup_maven_environment():
    """Set up the Maven environment in the sandbox."""
    # Check if Maven is installed
    maven_installed = subprocess.run(["which", "mvn"], capture_output=True).returncode == 0
    
    if not maven_installed:
        logger.info("Installing Maven in sandbox...")
        subprocess.run(["wget", "-q", "https://dlcdn.apache.org/maven/maven-3/3.9.0/binaries/apache-maven-3.9.0-bin.tar.gz", "-P", "/tmp"], check=True)
        subprocess.run(["tar", "-xf", "/tmp/apache-maven-3.9.0-bin.tar.gz", "-C", "/opt"], check=True)
        subprocess.run(["ln", "-s", "/opt/apache-maven-3.9.0/bin/mvn", "/usr/bin/mvn"], check=True)
        logger.info("Maven installed successfully")
    
    # Set MAVEN_HOME
    maven_home = "/opt/apache-maven-3.9.0"
    os.environ["MAVEN_HOME"] = maven_home
    logger.info(f"Set MAVEN_HOME to {maven_home}")

def setup_git_environment():
    """Set up the Git environment in the sandbox."""
    # Check if Git is installed
    git_installed = subprocess.run(["which", "git"], capture_output=True).returncode == 0
    
    if not git_installed:
        logger.info("Installing Git in sandbox...")
        subprocess.run(["apt-get", "update"], check=True)
        subprocess.run(["apt-get", "install", "-y", "git"], check=True)
        logger.info("Git installed successfully")
    
    # Configure Git
    subprocess.run(["git", "config", "--global", "user.name", "Suna Agent"], check=True)
    subprocess.run(["git", "config", "--global", "user.email", "suna@example.com"], check=True)
    logger.info("Git configured successfully")
```

## Conclusion

These configuration and setup updates ensure that the new Gradle, Maven, and Git tools are properly integrated into the Suna platform. The updates include:

1. Configuration file updates to include settings for the new tools
2. Environment setup updates to detect and configure Java, Gradle, Maven, and Git
3. Dependency management updates to include dependencies for the new tools
4. Installation script updates to install the new tools
5. Docker configuration updates to include the new tools in the Docker image
6. Tool registry updates to register the new tools
7. Tool schema updates to register the schemas for the new tools
8. Sandbox environment updates to set up the new tools in the sandbox

These updates ensure that the new tools are available and properly configured for Java developers using the Suna platform.
