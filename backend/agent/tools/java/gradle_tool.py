package com.suna.agent.tools;

import com.agentpress.tool.ToolResult;
import com.agentpress.tool.openapi_schema;
import com.agentpress.tool.xml_schema;
import com.agentpress.thread_manager.ThreadManager;
import com.suna.agent.tools.base.SandboxToolsBase;
import com.suna.utils.logger;

import java.io.File;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.TimeUnit;

/**
 * Tool for executing Gradle commands and managing Gradle projects.
 */
public class GradleTool extends SandboxToolsBase {
    private static final String TOOL_NAME = "gradle";
    private JavaEnvironmentTool javaEnvTool;

    /**
     * Constructor for GradleTool.
     *
     * @param projectId The project ID
     * @param threadManager The thread manager
     */
    public GradleTool(String projectId, ThreadManager threadManager) {
        super(projectId, threadManager);
        logger.info("Initializing GradleTool");
    }

    /**
     * Initialize the tool with references to other tools.
     *
     * @param tools Map of available tools
     */
    @Override
    public void initialize(Map<String, Object> tools) {
        super.initialize(tools);
        
        // Get reference to JavaEnvironmentTool
        if (tools.containsKey("java_environment")) {
            javaEnvTool = (JavaEnvironmentTool) tools.get("java_environment");
        } else {
            logger.warning("JavaEnvironmentTool not found, Gradle functionality may be limited");
        }
    }

    /**
     * Ensure Gradle is installed and available.
     *
     * @param version Optional version to install if Gradle is not found
     * @return Map containing status and path information
     */
    public Map<String, Object> ensureGradle(String version) {
        // Check if Gradle is already installed
        String gradlePath = findGradle();
        if (gradlePath != null) {
            Map<String, Object> result = new HashMap<>();
            result.put("status", "found");
            result.put("path", gradlePath);
            return result;
        }

        // If not found, use Gradle wrapper if available
        String wrapperPath = findGradleWrapper();
        if (wrapperPath != null) {
            Map<String, Object> result = new HashMap<>();
            result.put("status", "wrapper_found");
            result.put("path", wrapperPath);
            return result;
        }

        // If no wrapper, install Gradle
        if (version == null || version.isEmpty()) {
            version = "7.4.2"; // Default version
        }
        
        return installGradle(version);
    }

    /**
     * Find Gradle installation on the system.
     *
     * @return Path to Gradle executable or null if not found
     */
    private String findGradle() {
        try {
            ProcessBuilder pb = new ProcessBuilder("which", "gradle");
            Process process = pb.start();
            
            if (process.waitFor(10, TimeUnit.SECONDS) && process.exitValue() == 0) {
                return new String(process.getInputStream().readAllBytes()).trim();
            }
            return null;
        } catch (Exception e) {
            logger.error("Error finding Gradle: " + e.getMessage());
            return null;
        }
    }

    /**
     * Find Gradle wrapper in the current project.
     *
     * @return Path to Gradle wrapper or null if not found
     */
    private String findGradleWrapper() {
        try {
            File gradlew = new File("./gradlew");
            if (gradlew.exists() && gradlew.canExecute()) {
                return "./gradlew";
            }
            return null;
        } catch (Exception e) {
            logger.error("Error finding Gradle wrapper: " + e.getMessage());
            return null;
        }
    }

    /**
     * Install Gradle of the specified version.
     *
     * @param version Version to install
     * @return Map containing status and path information
     */
    private Map<String, Object> installGradle(String version) {
        Map<String, Object> result = new HashMap<>();
        
        try {
            // Ensure Java is available
            if (javaEnvTool != null) {
                Map<String, Object> javaEnv = javaEnvTool.detectJava();
                if (!"found".equals(javaEnv.get("status"))) {
                    javaEnv = javaEnvTool.installJdk();
                    if (!"installed".equals(javaEnv.get("status"))) {
                        result.put("status", "error");
                        result.put("message", "Failed to set up Java environment: " + javaEnv.get("message"));
                        return result;
                    }
                }
            }
            
            // Create Gradle directory
            String homeDir = System.getProperty("user.home");
            Path gradleDir = Paths.get(homeDir, ".gradle");
            Files.createDirectories(gradleDir);
            
            // Download and extract Gradle
            String gradleZip = "gradle-" + version + "-bin.zip";
            String downloadUrl = "https://services.gradle.org/distributions/" + gradleZip;
            
            // Download
            ProcessBuilder downloadPb = new ProcessBuilder("curl", "-L", "-o", gradleZip, downloadUrl);
            Process downloadProcess = downloadPb.start();
            if (!downloadProcess.waitFor(5, TimeUnit.MINUTES) || downloadProcess.exitValue() != 0) {
                result.put("status", "error");
                result.put("message", "Failed to download Gradle");
                return result;
            }
            
            // Extract
            ProcessBuilder extractPb = new ProcessBuilder("unzip", "-q", gradleZip, "-d", homeDir);
            Process extractProcess = extractPb.start();
            if (!extractProcess.waitFor(2, TimeUnit.MINUTES) || extractProcess.exitValue() != 0) {
                result.put("status", "error");
                result.put("message", "Failed to extract Gradle");
                return result;
            }
            
            // Add to PATH
            String gradleHome = Paths.get(homeDir, "gradle-" + version).toString();
            String gradleBin = Paths.get(gradleHome, "bin").toString();
            
            // Update PATH in .bashrc
            Path bashrcPath = Paths.get(homeDir, ".bashrc");
            List<String> bashrcLines = Files.exists(bashrcPath) 
                ? Files.readAllLines(bashrcPath) 
                : new ArrayList<>();
            
            bashrcLines.add("\nexport PATH=\"" + gradleBin + ":$PATH\"\n");
            Files.write(bashrcPath, bashrcLines);
            
            // Source .bashrc
            ProcessBuilder sourcePb = new ProcessBuilder("bash", "-c", "source " + bashrcPath.toString());
            sourcePb.start().waitFor();
            
            result.put("status", "installed");
            result.put("path", Paths.get(gradleBin, "gradle").toString());
            return result;
        } catch (Exception e) {
            result.put("status", "error");
            result.put("message", e.getMessage());
            return result;
        }
    }

    /**
     * Initialize a new Gradle project.
     *
     * @param projectDir Directory where the Gradle project should be created
     * @param projectName Name of the project (optional)
     * @param projectType Type of project (java-application, java-library, etc.)
     * @return ToolResult containing the result of the operation
     */
    @xml_schema
    public ToolResult initProject(String projectDir, String projectName, String projectType) {
        Map<String, Object> result = new HashMap<>();
        
        try {
            // Ensure Gradle is available
            Map<String, Object> gradleInfo = ensureGradle(null);
            if (!isGradleAvailable(gradleInfo)) {
                result.put("status", "error");
                result.put("message", "Gradle not available: " + gradleInfo.get("message"));
                return new ToolResult(result);
            }
            
            String gradlePath = (String) gradleInfo.get("path");
            
            // Create project directory if it doesn't exist
            Files.createDirectories(Paths.get(projectDir));
            
            // Change to project directory
            String originalDir = System.getProperty("user.dir");
            System.setProperty("user.dir", projectDir);
            
            try {
                // Initialize Gradle project
                List<String> cmd = new ArrayList<>();
                cmd.add(gradlePath);
                cmd.add("init");
                
                if (projectType != null && !projectType.isEmpty()) {
                    cmd.add("--type=" + projectType);
                } else {
                    cmd.add("--type=java-application");
                }
                
                if (projectName != null && !projectName.isEmpty()) {
                    cmd.add("--project-name=" + projectName);
                }
                
                ProcessBuilder pb = new ProcessBuilder(cmd);
                Map<String, String> env = pb.environment();
                
                // Set Java environment if available
                if (javaEnvTool != null) {
                    Map<String, Object> javaEnv = javaEnvTool.detectJava();
                    if ("found".equals(javaEnv.get("status"))) {
                        env.put("JAVA_HOME", (String) javaEnv.get("java_home"));
                    }
                }
                
                Process process = pb.start();
                boolean completed = process.waitFor(5, TimeUnit.MINUTES);
                
                if (completed && process.exitValue() == 0) {
                    result.put("status", "success");
                    result.put("message", "Gradle project initialized successfully");
                    result.put("output", new String(process.getInputStream().readAllBytes()));
                } else {
                    result.put("status", "error");
                    result.put("message", "Failed to initialize Gradle project: " + 
                               new String(process.getErrorStream().readAllBytes()));
                }
            } finally {
                // Change back to original directory
                System.setProperty("user.dir", originalDir);
            }
        } catch (Exception e) {
            result.put("status", "error");
            result.put("message", e.getMessage());
        }
        
        return new ToolResult(result);
    }

    /**
     * Execute a Gradle task in the specified project directory.
     *
     * @param projectDir Directory of the Gradle project
     * @param task Gradle task to execute (e.g., build, test, run)
     * @param arguments Additional arguments for the Gradle task
     * @return ToolResult containing the result of the operation
     */
    @xml_schema
    public ToolResult executeTask(String projectDir, String task, List<String> arguments) {
        Map<String, Object> result = new HashMap<>();
        
        try {
            // Ensure Gradle is available
            Map<String, Object> gradleInfo = ensureGradle(null);
            if (!isGradleAvailable(gradleInfo)) {
                result.put("status", "error");
                result.put("message", "Gradle not available: " + gradleInfo.get("message"));
                return new ToolResult(result);
            }
            
            String gradlePath = (String) gradleInfo.get("path");
            
            // Change to project directory
            String originalDir = System.getProperty("user.dir");
            System.setProperty("user.dir", projectDir);
            
            try {
                // Check for Gradle wrapper in project
                File gradlew = new File(projectDir, "gradlew");
                if (gradlew.exists() && gradlew.canExecute()) {
                    gradlePath = "./gradlew";
                }
                
                // Build command
                List<String> cmd = new ArrayList<>();
                cmd.add(gradlePath);
                cmd.add(task);
                
                if (arguments != null && !arguments.isEmpty()) {
                    cmd.addAll(arguments);
                }
                
                // Execute command
                ProcessBuilder pb = new ProcessBuilder(cmd);
                Map<String, String> env = pb.environment();
                
                // Set Java environment if available
                if (javaEnvTool != null) {
                    Map<String, Object> javaEnv = javaEnvTool.detectJava();
                    if ("found".equals(javaEnv.get("status"))) {
                        env.put("JAVA_HOME", (String) javaEnv.get("java_home"));
                    }
                }
                
                Process process = pb.start();
                boolean completed = process.waitFor(10, TimeUnit.MINUTES);
                
                if (completed && process.exitValue() == 0) {
                    result.put("status", "success");
                    result.put("message", "Gradle task '" + task + "' executed successfully");
                    result.put("output", new String(process.getInputStream().readAllBytes()));
                } else {
                    result.put("status", "error");
                    result.put("message", "Failed to execute Gradle task '" + task + "': " + 
                               new String(process.getErrorStream().readAllBytes()));
                    result.put("output", new String(process.getInputStream().readAllBytes()));
                    result.put("error", new String(process.getErrorStream().readAllBytes()));
                }
            } finally {
                // Change back to original directory
                System.setProperty("user.dir", originalDir);
            }
        } catch (Exception e) {
            result.put("status", "error");
            result.put("message", e.getMessage());
        }
        
        return new ToolResult(result);
    }

    /**
     * Add a dependency to the build.gradle file.
     *
     * @param projectDir Directory of the Gradle project
     * @param dependency Dependency to add (e.g., 'com.google.guava:guava:30.1-jre')
     * @param configuration Configuration to add the dependency to
     * @return ToolResult containing the result of the operation
     */
    @xml_schema
    public ToolResult addDependency(String projectDir, String dependency, String configuration) {
        Map<String, Object> result = new HashMap<>();
        
        try {
            // Change to project directory
            String originalDir = System.getProperty("user.dir");
            System.setProperty("user.dir", projectDir);
            
            try {
                // Find build.gradle file
                String buildFile = "build.gradle";
                if (!Files.exists(Paths.get(projectDir, buildFile))) {
                    buildFile = "build.gradle.kts";
                    if (!Files.exists(Paths.get(projectDir, buildFile))) {
                        result.put("status", "error");
                        result.put("message", "build.gradle file not found");
                        return new ToolResult(result);
                    }
                }
                
                // Read build.gradle
                Path buildFilePath = Paths.get(projectDir, buildFile);
                String content = Files.readString(buildFilePath);
                
                // Check if it's a Kotlin DSL file
                boolean isKotlin = buildFile.endsWith(".kts");
                
                // Find dependencies block
                if (content.contains("dependencies {")) {
                    // Add dependency to dependencies block
                    String newContent;
                    if (configuration == null || configuration.isEmpty()) {
                        configuration = "implementation";
                    }
                    
                    if (isKotlin) {
                        newContent = content.replace(
                            "dependencies {",
                            "dependencies {\n    " + configuration + "(\"" + dependency + "\")"
                        );
                    } else {
                        newContent = content.replace(
                            "dependencies {",
                            "dependencies {\n    " + configuration + "('" + dependency + "')"
                        );
                    }
                    
                    // Write updated build.gradle
                    Files.writeString(buildFilePath, newContent);
                    
                    result.put("status", "success");
                    result.put("message", "Added dependency '" + dependency + "' to " + configuration + " configuration");
                } else {
                    result.put("status", "error");
                    result.put("message", "Could not find dependencies block in build.gradle");
                }
            } finally {
                // Change back to original directory
                System.setProperty("user.dir", originalDir);
            }
        } catch (Exception e) {
            result.put("status", "error");
            result.put("message", e.getMessage());
        }
        
        return new ToolResult(result);
    }

    /**
     * Analyze a Gradle project and return information about it.
     *
     * @param projectDir Directory of the Gradle project
     * @return ToolResult containing the result of the operation
     */
    @xml_schema
    public ToolResult analyzeProject(String projectDir) {
        Map<String, Object> result = new HashMap<>();
        
        try {
            // Change to project directory
            String originalDir = System.getProperty("user.dir");
            System.setProperty("user.dir", projectDir);
            
            try {
                // Check for Gradle wrapper
                boolean hasWrapper = Files.exists(Paths.get(projectDir, "gradlew"));
                
                // Check for build.gradle
                String buildFile = null;
                if (Files.exists(Paths.get(projectDir, "build.gradle"))) {
                    buildFile = "build.gradle";
                } else if (Files.exists(Paths.get(projectDir, "build.gradle.kts"))) {
                    buildFile = "build.gradle.kts";
                }
                
                if (buildFile == null) {
                    result.put("status", "error");
                    result.put("message", "Not a Gradle project (no build.gradle found)");
                    return new ToolResult(result);
                }
                
                // Get available tasks
                Map<String, Object> gradleInfo = ensureGradle(null);
                if (!isGradleAvailable(gradleInfo)) {
                    result.put("status", "error");
                    result.put("message", "Gradle not available: " + gradleInfo.get("message"));
                    return new ToolResult(result);
                }
                
                String gradlePath = (String) gradleInfo.get("path");
                if (hasWrapper) {
                    gradlePath = "./gradlew";
                }
                
                // Get tasks
                ProcessBuilder pb = new ProcessBuilder(gradlePath, "tasks", "--all");
                Process process = pb.start();
                boolean completed = process.waitFor(2, TimeUnit.MINUTES);
                String tasksOutput = completed && process.exitValue() == 0 
                    ? new String(process.getInputStream().readAllBytes()) 
                    : "Failed to get tasks";
                
                // Parse build.gradle for dependencies
                String buildContent = Files.readString(Paths.get(projectDir, buildFile));
                
                // Simple regex to extract dependencies
                List<Map<String, String>> dependencies = new ArrayList<>();
                java.util.regex.Pattern pattern = java.util.regex.Pattern.compile(
                    "(\\w+)\\s*\\(['\"]([^'\"]+)['\"]"
                );
                java.util.regex.Matcher matcher = pattern.matcher(buildContent);
                
                while (matcher.find()) {
                    Map<String, String> dependency = new HashMap<>();
                    dependency.put("configuration", matcher.group(1));
                    dependency.put("dependency", matcher.group(2));
                    dependencies.add(dependency);
                }
                
                result.put("status", "success");
                result.put("project_type", "Gradle");
                result.put("build_file", buildFile);
                result.put("has_wrapper", hasWrapper);
                result.put("tasks", tasksOutput);
                result.put("dependencies", dependencies);
            } finally {
                // Change back to original directory
                System.setProperty("user.dir", originalDir);
            }
        } catch (Exception e) {
            result.put("status", "error");
            result.put("message", e.getMessage());
        }
        
        return new ToolResult(result);
    }

    /**
     * Check if Gradle is available based on the result of ensureGradle.
     *
     * @param gradleInfo Result of ensureGradle
     * @return true if Gradle is available, false otherwise
     */
    private boolean isGradleAvailable(Map<String, Object> gradleInfo) {
        return gradleInfo != null && 
               (gradleInfo.get("status").equals("found") || 
                gradleInfo.get("status").equals("wrapper_found") || 
                gradleInfo.get("status").equals("installed"));
    }

    /**
     * Get the XML schema for this tool.
     *
     * @return XML schema for the tool
     */
    @xml_schema
    public static Map<String, Object> getXmlSchema() {
        Map<String, Object> schema = new HashMap<>();
        schema.put("name", TOOL_NAME);
        schema.put("description", "Execute Gradle commands and manage Gradle projects");
        
        List<Map<String, Object>> functions = new ArrayList<>();
        
        // init_project function
        Map<String, Object> initProjectFunction = new HashMap<>();
        initProjectFunction.put("name", "init_project");
        initProjectFunction.put("description", "Initialize a new Gradle project");
        
        List<Map<String, Object>> initProjectParams = new ArrayList<>();
        
        Map<String, Object> projectDirParam = new HashMap<>();
        projectDirParam.put("name", "project_dir");
        projectDirParam.put("type", "string");
        projectDirParam.put("description", "Directory where the Gradle project should be created");
        projectDirParam.put("required", true);
        initProjectParams.add(projectDirParam);
        
        Map<String, Object> projectNameParam = new HashMap<>();
        projectNameParam.put("name", "project_name");
        projectNameParam.put("type", "string");
        projectNameParam.put("description", "Name of the project (optional)");
        projectNameParam.put("required", false);
        initProjectParams.add(projectNameParam);
        
        Map<String, Object> projectTypeParam = new HashMap<>();
        projectTypeParam.put("name", "project_type");
        projectTypeParam.put("type", "string");
        projectTypeParam.put("description", "Type of project (java-application, java-library, etc.)");
        projectTypeParam.put("required", false);
        projectTypeParam.put("default", "java-application");
        initProjectParams.add(projectTypeParam);
        
        initProjectFunction.put("parameters", initProjectParams);
        functions.add(initProjectFunction);
        
        // execute_task function
        Map<String, Object> executeTaskFunction = new HashMap<>();
        executeTaskFunction.put("name", "execute_task");
        executeTaskFunction.put("description", "Execute a Gradle task");
        
        List<Map<String, Object>> executeTaskParams = new ArrayList<>();
        
        Map<String, Object> execProjectDirParam = new HashMap<>();
        execProjectDirParam.put("name", "project_dir");
        execProjectDirParam.put("type", "string");
        execProjectDirParam.put("description", "Directory of the Gradle project");
        execProjectDirParam.put("required", true);
        executeTaskParams.add(execProjectDirParam);
        
        Map<String, Object> taskParam = new HashMap<>();
        taskParam.put("name", "task");
        taskParam.put("type", "string");
        taskParam.put("description", "Gradle task to execute (e.g., build, test, run)");
        taskParam.put("required", true);
        executeTaskParams.add(taskParam);
        
        Map<String, Object> argumentsParam = new HashMap<>();
        argumentsParam.put("name", "arguments");
        argumentsParam.put("type", "array");
        Map<String, Object> itemsType = new HashMap<>();
        itemsType.put("type", "string");
        argumentsParam.put("items", itemsType);
        argumentsParam.put("description", "Additional arguments for the Gradle task");
        argumentsParam.put("required", false);
        executeTaskParams.add(argumentsParam);
        
        executeTaskFunction.put("parameters", executeTaskParams);
        functions.add(executeTaskFunction);
        
        // add_dependency function
        Map<String, Object> addDependencyFunction = new HashMap<>();
        addDependencyFunction.put("name", "add_dependency");
        addDependencyFunction.put("description", "Add a dependency to the build.gradle file");
        
        List<Map<String, Object>> addDependencyParams = new ArrayList<>();
        
        Map<String, Object> depProjectDirParam = new HashMap<>();
        depProjectDirParam.put("name", "project_dir");
        depProjectDirParam.put("type", "string");
        depProjectDirParam.put("description", "Directory of the Gradle project");
        depProjectDirParam.put("required", true);
        addDependencyParams.add(depProjectDirParam);
        
        Map<String, Object> dependencyParam = new HashMap<>();
        dependencyParam.put("name", "dependency");
        dependencyParam.put("type", "string");
        dependencyParam.put("description", "Dependency to add (e.g., 'com.google.guava:guava:30.1-jre')");
        dependencyParam.put("required", true);
        addDependencyParams.add(dependencyParam);
        
        Map<String, Object> configurationParam = new HashMap<>();
        configurationParam.put("name", "configuration");
        configurationParam.put("type", "string");
        configurationParam.put("description", "Configuration to add the dependency to");
        configurationParam.put("required", false);
        configurationParam.put("default", "implementation");
        addDependencyParams.add(configurationParam);
        
        addDependencyFunction.put("parameters", addDependencyParams);
        functions.add(addDependencyFunction);
        
        // analyze_project function
        Map<String, Object> analyzeProjectFunction = new HashMap<>();
        analyzeProjectFunction.put("name", "analyze_project");
        analyzeProjectFunction.put("description", "Analyze a Gradle project");
        
        List<Map<String, Object>> analyzeProjectParams = new ArrayList<>();
        
        Map<String, Object> analyzeProjectDirParam = new HashMap<>();
        analyzeProjectDirParam.put("name", "project_dir");
        analyzeProjectDirParam.put("type", "string");
        analyzeProjectDirParam.put("description", "Directory of the Gradle project");
        analyzeProjectDirParam.put("required", true);
        analyzeProjectParams.add(analyzeProjectDirParam);
        
        analyzeProjectFunction.put("parameters", analyzeProjectParams);
        functions.add(analyzeProjectFunction);
        
        schema.put("functions", functions);
        return schema;
    }
}
