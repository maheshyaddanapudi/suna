# Suna Java Development Tools Documentation

## Overview

This documentation provides comprehensive information about the Java development tools integrated into the Suna platform. These tools enhance the agent's capabilities for Java developers, enabling seamless project management, dependency handling, and version control directly through the agent.

The following tools have been added to the Suna platform:

1. **Gradle Tool**: For managing Gradle-based Java projects
2. **Maven Tool**: For managing Maven-based Java projects
3. **Git Tool**: For version control operations

## Gradle Tool

The Gradle tool provides functionality for managing Gradle-based Java projects, including project initialization, building, testing, and dependency management.

### Configuration

The Gradle tool can be configured in the `config.yaml` file:

```yaml
tools:
  gradle:
    enabled: true
    auto_install: true
    default_version: "7.6.1"
    cache_dir: "${HOME}/.gradle"
    wrapper_enabled: true
```

Configuration options:

- `enabled`: Whether the Gradle tool is enabled
- `auto_install`: Whether to automatically install Gradle if not found
- `default_version`: The default Gradle version to use
- `cache_dir`: The directory to use for Gradle cache
- `wrapper_enabled`: Whether to use the Gradle wrapper when available

### Functions

#### 1. Initialize Project

Creates a new Gradle project with the specified group ID and artifact ID.

```
init_project(project_dir, group_id, artifact_id, version, project_type)
```

Parameters:
- `project_dir`: Directory where the project should be created
- `group_id`: Group ID for the project (e.g., "com.example")
- `artifact_id`: Artifact ID for the project (e.g., "my-project")
- `version` (optional): Version for the project (default: "1.0.0")
- `project_type` (optional): Type of project to create (default: "java-application")

Example:
```python
result = gradle_tool.init_project(
    "/path/to/project",
    "com.example",
    "my-project",
    "1.0.0",
    "java-application"
)
```

#### 2. Build Project

Builds a Gradle project.

```
build(project_dir, tasks, options)
```

Parameters:
- `project_dir`: Directory of the Gradle project
- `tasks` (optional): List of tasks to execute (default: ["build"])
- `options` (optional): Dictionary of Gradle options

Example:
```python
result = gradle_tool.build(
    "/path/to/project",
    ["clean", "build"],
    {"--no-daemon": True, "--info": True}
)
```

#### 3. Run Tests

Runs tests for a Gradle project.

```
test(project_dir, test_name, options)
```

Parameters:
- `project_dir`: Directory of the Gradle project
- `test_name` (optional): Name of the test to run
- `options` (optional): Dictionary of Gradle options

Example:
```python
result = gradle_tool.test(
    "/path/to/project",
    "com.example.MyTest",
    {"--tests": "com.example.MyTest", "--info": True}
)
```

#### 4. List Dependencies

Lists dependencies for a Gradle project.

```
dependencies(project_dir, configuration)
```

Parameters:
- `project_dir`: Directory of the Gradle project
- `configuration` (optional): Configuration to list dependencies for (default: "implementation")

Example:
```python
result = gradle_tool.dependencies(
    "/path/to/project",
    "implementation"
)
```

#### 5. Add Dependency

Adds a dependency to a Gradle project.

```
add_dependency(project_dir, group_id, artifact_id, version, configuration)
```

Parameters:
- `project_dir`: Directory of the Gradle project
- `group_id`: Group ID of the dependency
- `artifact_id`: Artifact ID of the dependency
- `version`: Version of the dependency
- `configuration` (optional): Configuration to add the dependency to (default: "implementation")

Example:
```python
result = gradle_tool.add_dependency(
    "/path/to/project",
    "com.google.guava",
    "guava",
    "31.1-jre",
    "implementation"
)
```

#### 6. Run Task

Runs a Gradle task.

```
run_task(project_dir, task, options)
```

Parameters:
- `project_dir`: Directory of the Gradle project
- `task`: Task to run
- `options` (optional): Dictionary of Gradle options

Example:
```python
result = gradle_tool.run_task(
    "/path/to/project",
    "run",
    {"--args": "'arg1 arg2'", "--info": True}
)
```

#### 7. Generate Wrapper

Generates Gradle wrapper files.

```
wrapper(project_dir, version)
```

Parameters:
- `project_dir`: Directory of the Gradle project
- `version` (optional): Gradle version to use for the wrapper

Example:
```python
result = gradle_tool.wrapper(
    "/path/to/project",
    "7.6.1"
)
```

### Troubleshooting

Common issues and solutions:

1. **Gradle not found**: If Gradle is not found, the tool will attempt to install it automatically if `auto_install` is set to `true`. If installation fails, ensure that the system has internet access and sufficient permissions.

2. **Build failures**: If a build fails, check the output for error messages. Common issues include missing dependencies, compilation errors, or test failures.

3. **Performance issues**: If Gradle builds are slow, consider using the Gradle daemon by setting the `--daemon` option, or using the Gradle wrapper.

## Maven Tool

The Maven tool provides functionality for managing Maven-based Java projects, including project initialization, building, testing, and dependency management.

### Configuration

The Maven tool can be configured in the `config.yaml` file:

```yaml
tools:
  maven:
    enabled: true
    auto_install: true
    default_version: "3.9.0"
    cache_dir: "${HOME}/.m2"
    settings_file: "${HOME}/.m2/settings.xml"
```

Configuration options:

- `enabled`: Whether the Maven tool is enabled
- `auto_install`: Whether to automatically install Maven if not found
- `default_version`: The default Maven version to use
- `cache_dir`: The directory to use for Maven cache
- `settings_file`: Path to the Maven settings file

### Functions

#### 1. Initialize Project

Creates a new Maven project with the specified group ID and artifact ID.

```
init_project(project_dir, group_id, artifact_id, version, template)
```

Parameters:
- `project_dir`: Directory where the project should be created
- `group_id`: Group ID for the project (e.g., "com.example")
- `artifact_id`: Artifact ID for the project (e.g., "my-project")
- `version` (optional): Version for the project (default: "1.0.0")
- `template` (optional): Maven archetype to use (default: "maven-archetype-quickstart")

Example:
```python
result = maven_tool.init_project(
    "/path/to/project",
    "com.example",
    "my-project",
    "1.0.0",
    "maven-archetype-quickstart"
)
```

#### 2. Build Project

Builds a Maven project.

```
build(project_dir, goals, options)
```

Parameters:
- `project_dir`: Directory of the Maven project
- `goals` (optional): List of goals to execute (default: ["clean", "install"])
- `options` (optional): Dictionary of Maven options

Example:
```python
result = maven_tool.build(
    "/path/to/project",
    ["clean", "package"],
    {"-DskipTests": True, "-X": True}
)
```

#### 3. Run Tests

Runs tests for a Maven project.

```
test(project_dir, test_name, options)
```

Parameters:
- `project_dir`: Directory of the Maven project
- `test_name` (optional): Name of the test to run
- `options` (optional): Dictionary of Maven options

Example:
```python
result = maven_tool.test(
    "/path/to/project",
    "com.example.MyTest",
    {"-Dtest": "com.example.MyTest", "-X": True}
)
```

#### 4. List Dependencies

Lists dependencies for a Maven project.

```
dependencies(project_dir, scope)
```

Parameters:
- `project_dir`: Directory of the Maven project
- `scope` (optional): Scope to list dependencies for (default: "compile")

Example:
```python
result = maven_tool.dependencies(
    "/path/to/project",
    "compile"
)
```

#### 5. Add Dependency

Adds a dependency to a Maven project.

```
add_dependency(project_dir, group_id, artifact_id, version, scope)
```

Parameters:
- `project_dir`: Directory of the Maven project
- `group_id`: Group ID of the dependency
- `artifact_id`: Artifact ID of the dependency
- `version`: Version of the dependency
- `scope` (optional): Scope of the dependency (default: "compile")

Example:
```python
result = maven_tool.add_dependency(
    "/path/to/project",
    "com.google.guava",
    "guava",
    "31.1-jre",
    "compile"
)
```

#### 6. Run Goal

Runs a Maven goal.

```
run_goal(project_dir, goal, options)
```

Parameters:
- `project_dir`: Directory of the Maven project
- `goal`: Goal to run
- `options` (optional): Dictionary of Maven options

Example:
```python
result = maven_tool.run_goal(
    "/path/to/project",
    "exec:java",
    {"-Dexec.mainClass": "com.example.Main", "-Dexec.args": "arg1 arg2"}
)
```

#### 7. Generate POM

Generates a POM file.

```
generate_pom(project_dir, group_id, artifact_id, version)
```

Parameters:
- `project_dir`: Directory where the POM file should be created
- `group_id`: Group ID for the project
- `artifact_id`: Artifact ID for the project
- `version` (optional): Version for the project (default: "1.0.0")

Example:
```python
result = maven_tool.generate_pom(
    "/path/to/project",
    "com.example",
    "my-project",
    "1.0.0"
)
```

### Troubleshooting

Common issues and solutions:

1. **Maven not found**: If Maven is not found, the tool will attempt to install it automatically if `auto_install` is set to `true`. If installation fails, ensure that the system has internet access and sufficient permissions.

2. **Build failures**: If a build fails, check the output for error messages. Common issues include missing dependencies, compilation errors, or test failures.

3. **Repository issues**: If Maven cannot download dependencies, check the network connection and ensure that the Maven settings file is properly configured.

## Git Tool

The Git tool provides functionality for managing Git repositories, including repository initialization, cloning, committing, pushing, and pulling.

### Configuration

The Git tool can be configured in the `config.yaml` file:

```yaml
tools:
  git:
    enabled: true
    auto_install: true
    default_user_name: "${USER}"
    default_user_email: "${USER}@localhost"
    credential_helper: "cache"
```

Configuration options:

- `enabled`: Whether the Git tool is enabled
- `auto_install`: Whether to automatically install Git if not found
- `default_user_name`: Default user name for Git operations
- `default_user_email`: Default user email for Git operations
- `credential_helper`: Git credential helper to use

### Functions

#### 1. Initialize Repository

Initializes a new Git repository.

```
init_repo(repo_dir, bare)
```

Parameters:
- `repo_dir`: Directory where the Git repository should be created
- `bare` (optional): Whether to create a bare repository (default: false)

Example:
```python
result = git_tool.init_repo(
    "/path/to/repo",
    False
)
```

#### 2. Clone Repository

Clones a Git repository.

```
clone_repo(repo_url, target_dir, branch, depth)
```

Parameters:
- `repo_url`: URL of the Git repository to clone
- `target_dir`: Directory where the repository should be cloned
- `branch` (optional): Branch to checkout after cloning
- `depth` (optional): Create a shallow clone with a history truncated to the specified number of commits

Example:
```python
result = git_tool.clone_repo(
    "https://github.com/example/repo.git",
    "/path/to/target",
    "main",
    1
)
```

#### 3. Create Branch

Creates a new branch.

```
create_branch(repo_dir, branch_name, start_point)
```

Parameters:
- `repo_dir`: Directory of the Git repository
- `branch_name`: Name of the branch to create
- `start_point` (optional): The commit at which to start the new branch

Example:
```python
result = git_tool.create_branch(
    "/path/to/repo",
    "feature/new-feature",
    "main"
)
```

#### 4. Checkout Branch

Checks out a branch.

```
checkout_branch(repo_dir, branch_name, create)
```

Parameters:
- `repo_dir`: Directory of the Git repository
- `branch_name`: Name of the branch to checkout
- `create` (optional): Whether to create the branch if it doesn't exist (default: false)

Example:
```python
result = git_tool.checkout_branch(
    "/path/to/repo",
    "feature/new-feature",
    True
)
```

#### 5. List Branches

Lists branches in the repository.

```
list_branches(repo_dir, all, remote)
```

Parameters:
- `repo_dir`: Directory of the Git repository
- `all` (optional): Whether to list all branches (local and remote) (default: false)
- `remote` (optional): Whether to list only remote branches (default: false)

Example:
```python
result = git_tool.list_branches(
    "/path/to/repo",
    True,
    False
)
```

#### 6. Add Files

Adds files to the staging area.

```
add_files(repo_dir, files)
```

Parameters:
- `repo_dir`: Directory of the Git repository
- `files` (optional): Files to add (if not specified, all files will be added)

Example:
```python
result = git_tool.add_files(
    "/path/to/repo",
    ["file1.txt", "file2.txt"]
)
```

#### 7. Commit

Commits staged changes.

```
commit(repo_dir, message, author)
```

Parameters:
- `repo_dir`: Directory of the Git repository
- `message`: Commit message
- `author` (optional): Author of the commit (format: 'Name <email>')

Example:
```python
result = git_tool.commit(
    "/path/to/repo",
    "Add new feature",
    "John Doe <john@example.com>"
)
```

#### 8. Get Commit History

Gets commit history.

```
get_commit_history(repo_dir, max_count, skip, author, since, until, path)
```

Parameters:
- `repo_dir`: Directory of the Git repository
- `max_count` (optional): Maximum number of commits to return
- `skip` (optional): Number of commits to skip
- `author` (optional): Filter commits by author
- `since` (optional): Show commits more recent than a specific date
- `until` (optional): Show commits older than a specific date
- `path` (optional): Only show commits that affect the specified path

Example:
```python
result = git_tool.get_commit_history(
    "/path/to/repo",
    10,
    0,
    "John Doe",
    "2023-01-01",
    "2023-12-31",
    "src/main/java"
)
```

#### 9. Add Remote

Adds a remote repository.

```
add_remote(repo_dir, name, url)
```

Parameters:
- `repo_dir`: Directory of the Git repository
- `name`: Name of the remote
- `url`: URL of the remote repository

Example:
```python
result = git_tool.add_remote(
    "/path/to/repo",
    "origin",
    "https://github.com/example/repo.git"
)
```

#### 10. List Remotes

Lists remote repositories.

```
list_remotes(repo_dir, verbose)
```

Parameters:
- `repo_dir`: Directory of the Git repository
- `verbose` (optional): Whether to show remote URLs (default: false)

Example:
```python
result = git_tool.list_remotes(
    "/path/to/repo",
    True
)
```

#### 11. Push

Pushes changes to a remote repository.

```
push(repo_dir, remote, branch, force, set_upstream)
```

Parameters:
- `repo_dir`: Directory of the Git repository
- `remote` (optional): Name of the remote
- `branch` (optional): Branch to push
- `force` (optional): Whether to force push (default: false)
- `set_upstream` (optional): Whether to set the upstream for the branch (default: false)

Example:
```python
result = git_tool.push(
    "/path/to/repo",
    "origin",
    "main",
    False,
    True
)
```

#### 12. Pull

Pulls changes from a remote repository.

```
pull(repo_dir, remote, branch, rebase)
```

Parameters:
- `repo_dir`: Directory of the Git repository
- `remote` (optional): Name of the remote
- `branch` (optional): Branch to pull
- `rebase` (optional): Whether to rebase instead of merge (default: false)

Example:
```python
result = git_tool.pull(
    "/path/to/repo",
    "origin",
    "main",
    True
)
```

#### 13. Get Status

Gets repository status.

```
get_status(repo_dir, short)
```

Parameters:
- `repo_dir`: Directory of the Git repository
- `short` (optional): Whether to show status in short format (default: false)

Example:
```python
result = git_tool.get_status(
    "/path/to/repo",
    True
)
```

#### 14. Get Diff

Gets diff of changes.

```
get_diff(repo_dir, file, staged)
```

Parameters:
- `repo_dir`: Directory of the Git repository
- `file` (optional): File to get diff for
- `staged` (optional): Whether to show staged changes (default: false)

Example:
```python
result = git_tool.get_diff(
    "/path/to/repo",
    "file.txt",
    True
)
```

### Troubleshooting

Common issues and solutions:

1. **Git not found**: If Git is not found, the tool will attempt to install it automatically if `auto_install` is set to `true`. If installation fails, ensure that the system has internet access and sufficient permissions.

2. **Authentication issues**: If Git operations that require authentication fail, ensure that the Git credential helper is properly configured. You may need to set up SSH keys or use a credential helper like `cache` or `store`.

3. **Merge conflicts**: If a pull or merge operation results in conflicts, you will need to resolve the conflicts manually and then commit the changes.

## Integration with Agent Framework

The Java development tools are integrated with the Suna agent framework, allowing them to be used seamlessly with other tools.

### Tool Registration

The tools are registered with the agent's tool registry in the `backend/agent/tools/tool_registry.py` file:

```python
# Register Java development tools
registry.register_tool("gradle", GradleTool)
registry.register_tool("maven", MavenTool)
registry.register_tool("git", GitTool)
```

### Tool Initialization

The tools are initialized with the agent's thread manager and project ID in the `backend/agent/run.py` file:

```python
# Initialize Java development tools
tools["gradle"] = GradleTool(project_id, thread_manager)
tools["maven"] = MavenTool(project_id, thread_manager)
tools["git"] = GitTool(project_id, thread_manager)
```

### Tool Schema Registration

The tools register their XML schemas with the agent's schema registry in the `backend/agent/schema_registry.py` file:

```python
# Register Java development tool schemas
registry.register_schema(GradleTool.get_xml_schema())
registry.register_schema(MavenTool.get_xml_schema())
registry.register_schema(GitTool.get_xml_schema())
```

### Environment Setup

The environment is set up for the Java development tools in the `backend/agent/environment.py` file:

```python
# Set up Java environment
setup_java_environment()

# Set up Gradle environment
setup_gradle_environment()

# Set up Maven environment
setup_maven_environment()

# Set up Git environment
setup_git_environment()
```

## Developer Notes

### Adding New Functions

To add a new function to a tool, follow these steps:

1. Add the function to the tool class:

```python
@xml_schema
def new_function(self, param1, param2):
    """Function description."""
    # Implementation
    return result
```

2. Add the function to the tool's XML schema:

```python
@xml_schema
def get_xml_schema():
    schema = {
        "name": "tool_name",
        "description": "Tool description",
        "functions": [
            # Existing functions...
            {
                "name": "new_function",
                "description": "Function description",
                "parameters": [
                    {
                        "name": "param1",
                        "type": "string",
                        "description": "Parameter description",
                        "required": True
                    },
                    {
                        "name": "param2",
                        "type": "integer",
                        "description": "Parameter description",
                        "required": False,
                        "default": 0
                    }
                ]
            }
        ]
    }
    return schema
```

3. Update the documentation to include the new function.

### Modifying Existing Functions

To modify an existing function, follow these steps:

1. Update the function implementation in the tool class.
2. Update the function schema in the tool's XML schema.
3. Update the documentation to reflect the changes.

### Adding New Tools

To add a new tool, follow these steps:

1. Create a new tool class that extends `SandboxToolsBase`:

```python
class NewTool(SandboxToolsBase):
    """Tool description."""
    
    def __init__(self, project_id, thread_manager):
        super().__init__(project_id, thread_manager)
    
    def initialize(self, tools):
        super().initialize(tools)
    
    @xml_schema
    def function1(self, param1, param2):
        """Function description."""
        # Implementation
        return result
    
    @xml_schema
    def get_xml_schema():
        schema = {
            "name": "new_tool",
            "description": "Tool description",
            "functions": [
                {
                    "name": "function1",
                    "description": "Function description",
                    "parameters": [
                        {
                            "name": "param1",
                            "type": "string",
                            "description": "Parameter description",
                            "required": True
                        },
                        {
                            "name": "param2",
                            "type": "integer",
                            "description": "Parameter description",
                            "required": False,
                            "default": 0
                        }
                    ]
                }
            ]
        }
        return schema
```

2. Register the tool with the agent's tool registry:

```python
registry.register_tool("new_tool", NewTool)
```

3. Initialize the tool with the agent's thread manager and project ID:

```python
tools["new_tool"] = NewTool(project_id, thread_manager)
```

4. Register the tool's XML schema with the agent's schema registry:

```python
registry.register_schema(NewTool.get_xml_schema())
```

5. Add configuration for the tool in the `config.yaml` file:

```yaml
tools:
  new_tool:
    enabled: true
    # Tool-specific configuration...
```

6. Add documentation for the tool.

## Conclusion

The Java development tools integrated into the Suna platform provide powerful capabilities for Java developers, enabling seamless project management, dependency handling, and version control directly through the agent. By following the documentation and best practices outlined in this document, developers can effectively use these tools to enhance their Java development workflow.
