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
import javax.xml.parsers.DocumentBuilder;
import javax.xml.parsers.DocumentBuilderFactory;
import javax.xml.transform.Transformer;
import javax.xml.transform.TransformerFactory;
import javax.xml.transform.dom.DOMSource;
import javax.xml.transform.stream.StreamResult;
import org.w3c.dom.Document;
import org.w3c.dom.Element;
import org.w3c.dom.Node;
import org.w3c.dom.NodeList;

/**
 * Tool for executing Maven commands and managing Maven projects.
 */
public class MavenTool extends SandboxToolsBase {
    private static final String TOOL_NAME = "maven";
    private JavaEnvironmentTool javaEnvTool;

    /**
     * Constructor for MavenTool.
     *
     * @param projectId The project ID
     * @param threadManager The thread manager
     */
    public MavenTool(String projectId, ThreadManager threadManager) {
        super(projectId, threadManager);
        logger.info("Initializing MavenTool");
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
            logger.warning("JavaEnvironmentTool not found, Maven functionality may be limited");
        }
    }

    /**
     * Ensure Maven is installed and available.
     *
     * @param version Optional version to install if Maven is not found
     * @return Map containing status and path information
     */
    public Map<String, Object> ensureMaven(String version) {
        // Check if Maven is already installed
        String mavenPath = findMaven();
        if (mavenPath != null) {
            Map<String, Object> result = new HashMap<>();
            result.put("status", "found");
            result.put("path", mavenPath);
            return result;
        }

        // If not found, use Maven wrapper if available
        String wrapperPath = findMavenWrapper();
        if (wrapperPath != null) {
            Map<String, Object> result = new HashMap<>();
            result.put("status", "wrapper_found");
            result.put("path", wrapperPath);
            return result;
        }

        // If no wrapper, install Maven
        if (version == null || version.isEmpty()) {
            version = "3.8.6"; // Default version
        }
        
        return installMaven(version);
    }

    /**
     * Find Maven installation on the system.
     *
     * @return Path to Maven executable or null if not found
     */
    private String findMaven() {
        try {
            ProcessBuilder pb = new ProcessBuilder("which", "mvn");
            Process process = pb.start();
            
            if (process.waitFor(10, TimeUnit.SECONDS) && process.exitValue() == 0) {
                return new String(process.getInputStream().readAllBytes()).trim();
            }
            return null;
        } catch (Exception e) {
            logger.error("Error finding Maven: " + e.getMessage());
            return null;
        }
    }

    /**
     * Find Maven wrapper in the current project.
     *
     * @return Path to Maven wrapper or null if not found
     */
    private String findMavenWrapper() {
        try {
            File mvnw = new File("./mvnw");
            if (mvnw.exists() && mvnw.canExecute()) {
                return "./mvnw";
            }
            return null;
        } catch (Exception e) {
            logger.error("Error finding Maven wrapper: " + e.getMessage());
            return null;
        }
    }

    /**
     * Install Maven of the specified version.
     *
     * @param version Version to install
     * @return Map containing status and path information
     */
    private Map<String, Object> installMaven(String version) {
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
            
            // Create Maven directory
            String homeDir = System.getProperty("user.home");
            Path mavenDir = Paths.get(homeDir, ".m2");
            Files.createDirectories(mavenDir);
            
            // Download and extract Maven
            String mavenArchive = "apache-maven-" + version + "-bin.tar.gz";
            String downloadUrl = "https://archive.apache.org/dist/maven/maven-3/" + version + "/binaries/" + mavenArchive;
            
            // Download
            ProcessBuilder downloadPb = new ProcessBuilder("curl", "-L", "-o", mavenArchive, downloadUrl);
            Process downloadProcess = downloadPb.start();
            if (!downloadProcess.waitFor(5, TimeUnit.MINUTES) || downloadProcess.exitValue() != 0) {
                result.put("status", "error");
                result.put("message", "Failed to download Maven");
                return result;
            }
            
            // Extract
            ProcessBuilder extractPb = new ProcessBuilder("tar", "-xzf", mavenArchive, "-C", homeDir);
            Process extractProcess = extractPb.start();
            if (!extractProcess.waitFor(2, TimeUnit.MINUTES) || extractProcess.exitValue() != 0) {
                result.put("status", "error");
                result.put("message", "Failed to extract Maven");
                return result;
            }
            
            // Add to PATH
            String mavenHome = Paths.get(homeDir, "apache-maven-" + version).toString();
            String mavenBin = Paths.get(mavenHome, "bin").toString();
            
            // Update PATH in .bashrc
            Path bashrcPath = Paths.get(homeDir, ".bashrc");
            List<String> bashrcLines = Files.exists(bashrcPath) 
                ? Files.readAllLines(bashrcPath) 
                : new ArrayList<>();
            
            bashrcLines.add("\nexport PATH=\"" + mavenBin + ":$PATH\"\n");
            bashrcLines.add("\nexport M2_HOME=\"" + mavenHome + "\"\n");
            Files.write(bashrcPath, bashrcLines);
            
            // Source .bashrc
            ProcessBuilder sourcePb = new ProcessBuilder("bash", "-c", "source " + bashrcPath.toString());
            sourcePb.start().waitFor();
            
            result.put("status", "installed");
            result.put("path", Paths.get(mavenBin, "mvn").toString());
            return result;
        } catch (Exception e) {
            result.put("status", "error");
            result.put("message", e.getMessage());
            return result;
        }
    }

    /**
     * Create a new Maven project.
     *
     * @param projectDir Directory where the Maven project should be created
     * @param groupId Group ID for the Maven project (e.g., com.example)
     * @param artifactId Artifact ID for the Maven project (e.g., my-app)
     * @param template Maven archetype to use for project creation
     * @return ToolResult containing the result of the operation
     */
    @xml_schema
    public ToolResult createProject(String projectDir, String groupId, String artifactId, String template) {
        Map<String, Object> result = new HashMap<>();
        
        try {
            // Ensure Maven is available
            Map<String, Object> mavenInfo = ensureMaven(null);
            if (!isMavenAvailable(mavenInfo)) {
                result.put("status", "error");
                result.put("message", "Maven not available: " + mavenInfo.get("message"));
                return new ToolResult(result);
            }
            
            String mavenPath = (String) mavenInfo.get("path");
            
            // Create project directory if it doesn't exist
            Files.createDirectories(Paths.get(projectDir));
            
            // Change to project directory
            String originalDir = System.getProperty("user.dir");
            System.setProperty("user.dir", projectDir);
            
            try {
                // Create Maven project
                List<String> cmd = new ArrayList<>();
                cmd.add(mavenPath);
                cmd.add("archetype:generate");
                cmd.add("-DgroupId=" + groupId);
                cmd.add("-DartifactId=" + artifactId);
                
                if (template != null && !template.isEmpty()) {
                    cmd.add("-DarchetypeArtifactId=" + template);
                } else {
                    cmd.add("-DarchetypeArtifactId=maven-archetype-quickstart");
                }
                
                cmd.add("-DinteractiveMode=false");
                
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
                    result.put("message", "Maven project created successfully");
                    result.put("output", new String(process.getInputStream().readAllBytes()));
                } else {
                    result.put("status", "error");
                    result.put("message", "Failed to create Maven project: " + 
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
     * Execute a Maven goal in the specified project directory.
     *
     * @param projectDir Directory of the Maven project
     * @param goal Maven goal to execute (e.g., compile, test, package)
     * @param arguments Additional arguments for the Maven goal
     * @return ToolResult containing the result of the operation
     */
    @xml_schema
    public ToolResult executeGoal(String projectDir, String goal, List<String> arguments) {
        Map<String, Object> result = new HashMap<>();
        
        try {
            // Ensure Maven is available
            Map<String, Object> mavenInfo = ensureMaven(null);
            if (!isMavenAvailable(mavenInfo)) {
                result.put("status", "error");
                result.put("message", "Maven not available: " + mavenInfo.get("message"));
                return new ToolResult(result);
            }
            
            String mavenPath = (String) mavenInfo.get("path");
            
            // Change to project directory
            String originalDir = System.getProperty("user.dir");
            System.setProperty("user.dir", projectDir);
            
            try {
                // Check for Maven wrapper in project
                File mvnw = new File(projectDir, "mvnw");
                if (mvnw.exists() && mvnw.canExecute()) {
                    mavenPath = "./mvnw";
                }
                
                // Build command
                List<String> cmd = new ArrayList<>();
                cmd.add(mavenPath);
                cmd.add(goal);
                
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
                    result.put("message", "Maven goal '" + goal + "' executed successfully");
                    result.put("output", new String(process.getInputStream().readAllBytes()));
                } else {
                    result.put("status", "error");
                    result.put("message", "Failed to execute Maven goal '" + goal + "': " + 
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
     * Add a dependency to the pom.xml file.
     *
     * @param projectDir Directory of the Maven project
     * @param groupId Group ID of the dependency
     * @param artifactId Artifact ID of the dependency
     * @param version Version of the dependency
     * @param scope Scope of the dependency (e.g., compile, test, provided)
     * @return ToolResult containing the result of the operation
     */
    @xml_schema
    public ToolResult addDependency(String projectDir, String groupId, String artifactId, String version, String scope) {
        Map<String, Object> result = new HashMap<>();
        
        try {
            // Change to project directory
            String originalDir = System.getProperty("user.dir");
            System.setProperty("user.dir", projectDir);
            
            try {
                // Find pom.xml file
                Path pomPath = Paths.get(projectDir, "pom.xml");
                if (!Files.exists(pomPath)) {
                    result.put("status", "error");
                    result.put("message", "pom.xml file not found");
                    return new ToolResult(result);
                }
                
                // Parse pom.xml
                DocumentBuilderFactory docFactory = DocumentBuilderFactory.newInstance();
                DocumentBuilder docBuilder = docFactory.newDocumentBuilder();
                Document doc = docBuilder.parse(pomPath.toFile());
                
                // Find or create dependencies element
                NodeList dependenciesNodes = doc.getElementsByTagName("dependencies");
                Element dependencies;
                
                if (dependenciesNodes.getLength() > 0) {
                    dependencies = (Element) dependenciesNodes.item(0);
                } else {
                    dependencies = doc.createElement("dependencies");
                    doc.getDocumentElement().appendChild(dependencies);
                }
                
                // Create new dependency element
                Element dependency = doc.createElement("dependency");
                
                // Add groupId, artifactId, and version
                Element groupIdElem = doc.createElement("groupId");
                groupIdElem.setTextContent(groupId);
                dependency.appendChild(groupIdElem);
                
                Element artifactIdElem = doc.createElement("artifactId");
                artifactIdElem.setTextContent(artifactId);
                dependency.appendChild(artifactIdElem);
                
                Element versionElem = doc.createElement("version");
                versionElem.setTextContent(version);
                dependency.appendChild(versionElem);
                
                // Add scope if specified
                if (scope != null && !scope.isEmpty()) {
                    Element scopeElem = doc.createElement("scope");
                    scopeElem.setTextContent(scope);
                    dependency.appendChild(scopeElem);
                }
                
                // Add dependency to dependencies
                dependencies.appendChild(dependency);
                
                // Write updated pom.xml
                TransformerFactory transformerFactory = TransformerFactory.newInstance();
                Transformer transformer = transformerFactory.newTransformer();
                DOMSource source = new DOMSource(doc);
                StreamResult streamResult = new StreamResult(pomPath.toFile());
                transformer.transform(source, streamResult);
                
                result.put("status", "success");
                result.put("message", "Added dependency " + groupId + ":" + artifactId + ":" + version + " to pom.xml");
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
     * Add a plugin to the pom.xml file.
     *
     * @param projectDir Directory of the Maven project
     * @param groupId Group ID of the plugin
     * @param artifactId Artifact ID of the plugin
     * @param version Version of the plugin
     * @param configuration Configuration for the plugin
     * @return ToolResult containing the result of the operation
     */
    @xml_schema
    public ToolResult addPlugin(String projectDir, String groupId, String artifactId, String version, Map<String, String> configuration) {
        Map<String, Object> result = new HashMap<>();
        
        try {
            // Change to project directory
            String originalDir = System.getProperty("user.dir");
            System.setProperty("user.dir", projectDir);
            
            try {
                // Find pom.xml file
                Path pomPath = Paths.get(projectDir, "pom.xml");
                if (!Files.exists(pomPath)) {
                    result.put("status", "error");
                    result.put("message", "pom.xml file not found");
                    return new ToolResult(result);
                }
                
                // Parse pom.xml
                DocumentBuilderFactory docFactory = DocumentBuilderFactory.newInstance();
                DocumentBuilder docBuilder = docFactory.newDocumentBuilder();
                Document doc = docBuilder.parse(pomPath.toFile());
                
                // Find or create build element
                NodeList buildNodes = doc.getElementsByTagName("build");
                Element build;
                
                if (buildNodes.getLength() > 0) {
                    build = (Element) buildNodes.item(0);
                } else {
                    build = doc.createElement("build");
                    doc.getDocumentElement().appendChild(build);
                }
                
                // Find or create plugins element
                NodeList pluginsNodes = build.getElementsByTagName("plugins");
                Element plugins;
                
                if (pluginsNodes.getLength() > 0) {
                    plugins = (Element) pluginsNodes.item(0);
                } else {
                    plugins = doc.createElement("plugins");
                    build.appendChild(plugins);
                }
                
                // Create new plugin element
                Element plugin = doc.createElement("plugin");
                
                // Add groupId, artifactId, and version
                Element groupIdElem = doc.createElement("groupId");
                groupIdElem.setTextContent(groupId);
                plugin.appendChild(groupIdElem);
                
                Element artifactIdElem = doc.createElement("artifactId");
                artifactIdElem.setTextContent(artifactId);
                plugin.appendChild(artifactIdElem);
                
                Element versionElem = doc.createElement("version");
                versionElem.setTextContent(version);
                plugin.appendChild(versionElem);
                
                // Add configuration if specified
                if (configuration != null && !configuration.isEmpty()) {
                    Element configElem = doc.createElement("configuration");
                    
                    for (Map.Entry<String, String> entry : configuration.entrySet()) {
                        Element paramElem = doc.createElement(entry.getKey());
                        paramElem.setTextContent(entry.getValue());
                        configElem.appendChild(paramElem);
                    }
                    
                    plugin.appendChild(configElem);
                }
                
                // Add plugin to plugins
                plugins.appendChild(plugin);
                
                // Write updated pom.xml
                TransformerFactory transformerFactory = TransformerFactory.newInstance();
                Transformer transformer = transformerFactory.newTransformer();
                DOMSource source = new DOMSource(doc);
                StreamResult streamResult = new StreamResult(pomPath.toFile());
                transformer.transform(source, streamResult);
                
                result.put("status", "success");
                result.put("message", "Added plugin " + groupId + ":" + artifactId + ":" + version + " to pom.xml");
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
     * Analyze a Maven project and return information about it.
     *
     * @param projectDir Directory of the Maven project
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
                // Check for Maven wrapper
                boolean hasWrapper = Files.exists(Paths.get(projectDir, "mvnw"));
                
                // Check for pom.xml
                Path pomPath = Paths.get(projectDir, "pom.xml");
                if (!Files.exists(pomPath)) {
                    result.put("status", "error");
                    result.put("message", "Not a Maven project (no pom.xml found)");
                    return new ToolResult(result);
                }
                
                // Get Maven info
                Map<String, Object> mavenInfo = ensureMaven(null);
                if (!isMavenAvailable(mavenInfo)) {
                    result.put("status", "error");
                    result.put("message", "Maven not available: " + mavenInfo.get("message"));
                    return new ToolResult(result);
                }
                
                String mavenPath = (String) mavenInfo.get("path");
                if (hasWrapper) {
                    mavenPath = "./mvnw";
                }
                
                // Get project info
                ProcessBuilder pb = new ProcessBuilder(mavenPath, "help:evaluate", "-Dexpression=project", "-q", "-DforceStdout");
                Process process = pb.start();
                boolean completed = process.waitFor(2, TimeUnit.MINUTES);
                String projectInfo = completed && process.exitValue() == 0 
                    ? new String(process.getInputStream().readAllBytes()) 
                    : "Failed to get project info";
                
                // Parse pom.xml
                DocumentBuilderFactory docFactory = DocumentBuilderFactory.newInstance();
                DocumentBuilder docBuilder = docFactory.newDocumentBuilder();
                Document doc = docBuilder.parse(pomPath.toFile());
                
                // Extract basic project info
                String groupId = getElementTextContent(doc, "groupId");
                String artifactId = getElementTextContent(doc, "artifactId");
                String version = getElementTextContent(doc, "version");
                
                // Extract dependencies
                List<Map<String, String>> dependencies = new ArrayList<>();
                NodeList dependenciesNodes = doc.getElementsByTagName("dependencies");
                
                if (dependenciesNodes.getLength() > 0) {
                    Element dependenciesElem = (Element) dependenciesNodes.item(0);
                    NodeList dependencyNodes = dependenciesElem.getElementsByTagName("dependency");
                    
                    for (int i = 0; i < dependencyNodes.getLength(); i++) {
                        Element dependencyElem = (Element) dependencyNodes.item(i);
                        
                        String depGroupId = getElementTextContent(dependencyElem, "groupId");
                        String depArtifactId = getElementTextContent(dependencyElem, "artifactId");
                        String depVersion = getElementTextContent(dependencyElem, "version");
                        String depScope = getElementTextContent(dependencyElem, "scope");
                        
                        if (depGroupId != null && depArtifactId != null) {
                            Map<String, String> dependency = new HashMap<>();
                            dependency.put("groupId", depGroupId);
                            dependency.put("artifactId", depArtifactId);
                            dependency.put("version", depVersion != null ? depVersion : "unspecified");
                            dependency.put("scope", depScope != null ? depScope : "compile");
                            dependencies.add(dependency);
                        }
                    }
                }
                
                // Extract plugins
                List<Map<String, String>> plugins = new ArrayList<>();
                NodeList buildNodes = doc.getElementsByTagName("build");
                
                if (buildNodes.getLength() > 0) {
                    Element buildElem = (Element) buildNodes.item(0);
                    NodeList pluginsNodes = buildElem.getElementsByTagName("plugins");
                    
                    if (pluginsNodes.getLength() > 0) {
                        Element pluginsElem = (Element) pluginsNodes.item(0);
                        NodeList pluginNodes = pluginsElem.getElementsByTagName("plugin");
                        
                        for (int i = 0; i < pluginNodes.getLength(); i++) {
                            Element pluginElem = (Element) pluginNodes.item(i);
                            
                            String pluginGroupId = getElementTextContent(pluginElem, "groupId");
                            String pluginArtifactId = getElementTextContent(pluginElem, "artifactId");
                            String pluginVersion = getElementTextContent(pluginElem, "version");
                            
                            if (pluginArtifactId != null) {
                                Map<String, String> plugin = new HashMap<>();
                                plugin.put("groupId", pluginGroupId != null ? pluginGroupId : "org.apache.maven.plugins");
                                plugin.put("artifactId", pluginArtifactId);
                                plugin.put("version", pluginVersion != null ? pluginVersion : "unspecified");
                                plugins.add(plugin);
                            }
                        }
                    }
                }
                
                result.put("status", "success");
                result.put("project_type", "Maven");
                result.put("has_wrapper", hasWrapper);
                result.put("group_id", groupId != null ? groupId : "unknown");
                result.put("artifact_id", artifactId != null ? artifactId : "unknown");
                result.put("version", version != null ? version : "unknown");
                result.put("project_info", projectInfo);
                result.put("dependencies", dependencies);
                result.put("plugins", plugins);
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
     * Get text content of an element by tag name.
     *
     * @param parent Parent element or document
     * @param tagName Tag name to find
     * @return Text content of the element or null if not found
     */
    private String getElementTextContent(Node parent, String tagName) {
        NodeList nodes;
        
        if (parent instanceof Document) {
            nodes = ((Document) parent).getElementsByTagName(tagName);
        } else if (parent instanceof Element) {
            nodes = ((Element) parent).getElementsByTagName(tagName);
        } else {
            return null;
        }
        
        if (nodes.getLength() > 0) {
            return nodes.item(0).getTextContent();
        }
        
        return null;
    }

    /**
     * Check if Maven is available based on the result of ensureMaven.
     *
     * @param mavenInfo Result of ensureMaven
     * @return true if Maven is available, false otherwise
     */
    private boolean isMavenAvailable(Map<String, Object> mavenInfo) {
        return mavenInfo != null && 
               (mavenInfo.get("status").equals("found") || 
                mavenInfo.get("status").equals("wrapper_found") || 
                mavenInfo.get("status").equals("installed"));
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
        schema.put("description", "Execute Maven commands and manage Maven projects");
        
        List<Map<String, Object>> functions = new ArrayList<>();
        
        // create_project function
        Map<String, Object> createProjectFunction = new HashMap<>();
        createProjectFunction.put("name", "create_project");
        createProjectFunction.put("description", "Create a new Maven project");
        
        List<Map<String, Object>> createProjectParams = new ArrayList<>();
        
        Map<String, Object> projectDirParam = new HashMap<>();
        projectDirParam.put("name", "project_dir");
        projectDirParam.put("type", "string");
        projectDirParam.put("description", "Directory where the Maven project should be created");
        projectDirParam.put("required", true);
        createProjectParams.add(projectDirParam);
        
        Map<String, Object> groupIdParam = new HashMap<>();
        groupIdParam.put("name", "group_id");
        groupIdParam.put("type", "string");
        groupIdParam.put("description", "Group ID for the Maven project (e.g., com.example)");
        groupIdParam.put("required", true);
        createProjectParams.add(groupIdParam);
        
        Map<String, Object> artifactIdParam = new HashMap<>();
        artifactIdParam.put("name", "artifact_id");
        artifactIdParam.put("type", "string");
        artifactIdParam.put("description", "Artifact ID for the Maven project (e.g., my-app)");
        artifactIdParam.put("required", true);
        createProjectParams.add(artifactIdParam);
        
        Map<String, Object> templateParam = new HashMap<>();
        templateParam.put("name", "template");
        templateParam.put("type", "string");
        templateParam.put("description", "Maven archetype to use for project creation");
        templateParam.put("required", false);
        templateParam.put("default", "maven-archetype-quickstart");
        createProjectParams.add(templateParam);
        
        createProjectFunction.put("parameters", createProjectParams);
        functions.add(createProjectFunction);
        
        // execute_goal function
        Map<String, Object> executeGoalFunction = new HashMap<>();
        executeGoalFunction.put("name", "execute_goal");
        executeGoalFunction.put("description", "Execute a Maven goal");
        
        List<Map<String, Object>> executeGoalParams = new ArrayList<>();
        
        Map<String, Object> execProjectDirParam = new HashMap<>();
        execProjectDirParam.put("name", "project_dir");
        execProjectDirParam.put("type", "string");
        execProjectDirParam.put("description", "Directory of the Maven project");
        execProjectDirParam.put("required", true);
        executeGoalParams.add(execProjectDirParam);
        
        Map<String, Object> goalParam = new HashMap<>();
        goalParam.put("name", "goal");
        goalParam.put("type", "string");
        goalParam.put("description", "Maven goal to execute (e.g., compile, test, package)");
        goalParam.put("required", true);
        executeGoalParams.add(goalParam);
        
        Map<String, Object> argumentsParam = new HashMap<>();
        argumentsParam.put("name", "arguments");
        argumentsParam.put("type", "array");
        Map<String, Object> itemsType = new HashMap<>();
        itemsType.put("type", "string");
        argumentsParam.put("items", itemsType);
        argumentsParam.put("description", "Additional arguments for the Maven goal");
        argumentsParam.put("required", false);
        executeGoalParams.add(argumentsParam);
        
        executeGoalFunction.put("parameters", executeGoalParams);
        functions.add(executeGoalFunction);
        
        // add_dependency function
        Map<String, Object> addDependencyFunction = new HashMap<>();
        addDependencyFunction.put("name", "add_dependency");
        addDependencyFunction.put("description", "Add a dependency to the pom.xml file");
        
        List<Map<String, Object>> addDependencyParams = new ArrayList<>();
        
        Map<String, Object> depProjectDirParam = new HashMap<>();
        depProjectDirParam.put("name", "project_dir");
        depProjectDirParam.put("type", "string");
        depProjectDirParam.put("description", "Directory of the Maven project");
        depProjectDirParam.put("required", true);
        addDependencyParams.add(depProjectDirParam);
        
        Map<String, Object> groupIdDepParam = new HashMap<>();
        groupIdDepParam.put("name", "group_id");
        groupIdDepParam.put("type", "string");
        groupIdDepParam.put("description", "Group ID of the dependency");
        groupIdDepParam.put("required", true);
        addDependencyParams.add(groupIdDepParam);
        
        Map<String, Object> artifactIdDepParam = new HashMap<>();
        artifactIdDepParam.put("name", "artifact_id");
        artifactIdDepParam.put("type", "string");
        artifactIdDepParam.put("description", "Artifact ID of the dependency");
        artifactIdDepParam.put("required", true);
        addDependencyParams.add(artifactIdDepParam);
        
        Map<String, Object> versionDepParam = new HashMap<>();
        versionDepParam.put("name", "version");
        versionDepParam.put("type", "string");
        versionDepParam.put("description", "Version of the dependency");
        versionDepParam.put("required", true);
        addDependencyParams.add(versionDepParam);
        
        Map<String, Object> scopeParam = new HashMap<>();
        scopeParam.put("name", "scope");
        scopeParam.put("type", "string");
        scopeParam.put("description", "Scope of the dependency (e.g., compile, test, provided)");
        scopeParam.put("required", false);
        addDependencyParams.add(scopeParam);
        
        addDependencyFunction.put("parameters", addDependencyParams);
        functions.add(addDependencyFunction);
        
        // add_plugin function
        Map<String, Object> addPluginFunction = new HashMap<>();
        addPluginFunction.put("name", "add_plugin");
        addPluginFunction.put("description", "Add a plugin to the pom.xml file");
        
        List<Map<String, Object>> addPluginParams = new ArrayList<>();
        
        Map<String, Object> pluginProjectDirParam = new HashMap<>();
        pluginProjectDirParam.put("name", "project_dir");
        pluginProjectDirParam.put("type", "string");
        pluginProjectDirParam.put("description", "Directory of the Maven project");
        pluginProjectDirParam.put("required", true);
        addPluginParams.add(pluginProjectDirParam);
        
        Map<String, Object> groupIdPluginParam = new HashMap<>();
        groupIdPluginParam.put("name", "group_id");
        groupIdPluginParam.put("type", "string");
        groupIdPluginParam.put("description", "Group ID of the plugin");
        groupIdPluginParam.put("required", true);
        addPluginParams.add(groupIdPluginParam);
        
        Map<String, Object> artifactIdPluginParam = new HashMap<>();
        artifactIdPluginParam.put("name", "artifact_id");
        artifactIdPluginParam.put("type", "string");
        artifactIdPluginParam.put("description", "Artifact ID of the plugin");
        artifactIdPluginParam.put("required", true);
        addPluginParams.add(artifactIdPluginParam);
        
        Map<String, Object> versionPluginParam = new HashMap<>();
        versionPluginParam.put("name", "version");
        versionPluginParam.put("type", "string");
        versionPluginParam.put("description", "Version of the plugin");
        versionPluginParam.put("required", true);
        addPluginParams.add(versionPluginParam);
        
        Map<String, Object> configurationParam = new HashMap<>();
        configurationParam.put("name", "configuration");
        configurationParam.put("type", "object");
        configurationParam.put("description", "Configuration for the plugin");
        configurationParam.put("required", false);
        addPluginParams.add(configurationParam);
        
        addPluginFunction.put("parameters", addPluginParams);
        functions.add(addPluginFunction);
        
        // analyze_project function
        Map<String, Object> analyzeProjectFunction = new HashMap<>();
        analyzeProjectFunction.put("name", "analyze_project");
        analyzeProjectFunction.put("description", "Analyze a Maven project");
        
        List<Map<String, Object>> analyzeProjectParams = new ArrayList<>();
        
        Map<String, Object> analyzeProjectDirParam = new HashMap<>();
        analyzeProjectDirParam.put("name", "project_dir");
        analyzeProjectDirParam.put("type", "string");
        analyzeProjectDirParam.put("description", "Directory of the Maven project");
        analyzeProjectDirParam.put("required", true);
        analyzeProjectParams.add(analyzeProjectDirParam);
        
        analyzeProjectFunction.put("parameters", analyzeProjectParams);
        functions.add(analyzeProjectFunction);
        
        schema.put("functions", functions);
        return schema;
    }
}
