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
 * Tool for executing Git commands and managing Git repositories.
 */
public class GitTool extends SandboxToolsBase {
    private static final String TOOL_NAME = "git";

    /**
     * Constructor for GitTool.
     *
     * @param projectId The project ID
     * @param threadManager The thread manager
     */
    public GitTool(String projectId, ThreadManager threadManager) {
        super(projectId, threadManager);
        logger.info("Initializing GitTool");
    }

    /**
     * Initialize the tool with references to other tools.
     *
     * @param tools Map of available tools
     */
    @Override
    public void initialize(Map<String, Object> tools) {
        super.initialize(tools);
    }

    /**
     * Ensure Git is installed and available.
     *
     * @return Map containing status and path information
     */
    public Map<String, Object> ensureGit() {
        // Check if Git is already installed
        String gitPath = findGit();
        if (gitPath != null) {
            Map<String, Object> result = new HashMap<>();
            result.put("status", "found");
            result.put("path", gitPath);
            return result;
        }

        // If not found, install Git
        return installGit();
    }

    /**
     * Find Git installation on the system.
     *
     * @return Path to Git executable or null if not found
     */
    private String findGit() {
        try {
            ProcessBuilder pb = new ProcessBuilder("which", "git");
            Process process = pb.start();
            
            if (process.waitFor(10, TimeUnit.SECONDS) && process.exitValue() == 0) {
                return new String(process.getInputStream().readAllBytes()).trim();
            }
            return null;
        } catch (Exception e) {
            logger.error("Error finding Git: " + e.getMessage());
            return null;
        }
    }

    /**
     * Install Git.
     *
     * @return Map containing status and path information
     */
    private Map<String, Object> installGit() {
        Map<String, Object> result = new HashMap<>();
        
        try {
            // Install Git
            ProcessBuilder updatePb = new ProcessBuilder("apt-get", "update");
            Process updateProcess = updatePb.start();
            if (!updateProcess.waitFor(5, TimeUnit.MINUTES) || updateProcess.exitValue() != 0) {
                result.put("status", "error");
                result.put("message", "Failed to update package lists");
                return result;
            }
            
            ProcessBuilder installPb = new ProcessBuilder("apt-get", "install", "-y", "git");
            Process installProcess = installPb.start();
            if (!installProcess.waitFor(5, TimeUnit.MINUTES) || installProcess.exitValue() != 0) {
                result.put("status", "error");
                result.put("message", "Failed to install Git");
                return result;
            }
            
            // Verify installation
            String gitPath = findGit();
            if (gitPath != null) {
                result.put("status", "installed");
                result.put("path", gitPath);
                return result;
            } else {
                result.put("status", "error");
                result.put("message", "Git installation failed");
                return result;
            }
        } catch (Exception e) {
            result.put("status", "error");
            result.put("message", e.getMessage());
            return result;
        }
    }

    /**
     * Initialize a new Git repository.
     *
     * @param repoDir Directory where the Git repository should be created
     * @param bare Whether to create a bare repository
     * @return ToolResult containing the result of the operation
     */
    @xml_schema
    public ToolResult initRepo(String repoDir, boolean bare) {
        Map<String, Object> result = new HashMap<>();
        
        try {
            // Ensure Git is available
            Map<String, Object> gitInfo = ensureGit();
            if (!isGitAvailable(gitInfo)) {
                result.put("status", "error");
                result.put("message", "Git not available: " + gitInfo.get("message"));
                return new ToolResult(result);
            }
            
            String gitPath = (String) gitInfo.get("path");
            
            // Create repository directory if it doesn't exist
            Files.createDirectories(Paths.get(repoDir));
            
            // Change to repository directory
            String originalDir = System.getProperty("user.dir");
            System.setProperty("user.dir", repoDir);
            
            try {
                // Initialize Git repository
                List<String> cmd = new ArrayList<>();
                cmd.add(gitPath);
                cmd.add("init");
                
                if (bare) {
                    cmd.add("--bare");
                }
                
                ProcessBuilder pb = new ProcessBuilder(cmd);
                Process process = pb.start();
                boolean completed = process.waitFor(2, TimeUnit.MINUTES);
                
                if (completed && process.exitValue() == 0) {
                    result.put("status", "success");
                    result.put("message", "Git repository initialized successfully in " + repoDir);
                    result.put("output", new String(process.getInputStream().readAllBytes()));
                } else {
                    result.put("status", "error");
                    result.put("message", "Failed to initialize Git repository: " + 
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
     * Clone a Git repository.
     *
     * @param repoUrl URL of the Git repository to clone
     * @param targetDir Directory where the repository should be cloned
     * @param branch Branch to checkout after cloning
     * @param depth Create a shallow clone with a history truncated to the specified number of commits
     * @return ToolResult containing the result of the operation
     */
    @xml_schema
    public ToolResult cloneRepo(String repoUrl, String targetDir, String branch, Integer depth) {
        Map<String, Object> result = new HashMap<>();
        
        try {
            // Ensure Git is available
            Map<String, Object> gitInfo = ensureGit();
            if (!isGitAvailable(gitInfo)) {
                result.put("status", "error");
                result.put("message", "Git not available: " + gitInfo.get("message"));
                return new ToolResult(result);
            }
            
            String gitPath = (String) gitInfo.get("path");
            
            // Create parent directory if it doesn't exist
            Path parentPath = Paths.get(targetDir).getParent();
            if (parentPath != null) {
                Files.createDirectories(parentPath);
            }
            
            // Build command
            List<String> cmd = new ArrayList<>();
            cmd.add(gitPath);
            cmd.add("clone");
            cmd.add(repoUrl);
            cmd.add(targetDir);
            
            if (branch != null && !branch.isEmpty()) {
                cmd.add("--branch");
                cmd.add(branch);
            }
            
            if (depth != null && depth > 0) {
                cmd.add("--depth");
                cmd.add(depth.toString());
            }
            
            // Execute command
            ProcessBuilder pb = new ProcessBuilder(cmd);
            Process process = pb.start();
            boolean completed = process.waitFor(10, TimeUnit.MINUTES);
            
            if (completed && process.exitValue() == 0) {
                result.put("status", "success");
                result.put("message", "Repository cloned successfully to " + targetDir);
                result.put("output", new String(process.getInputStream().readAllBytes()));
            } else {
                result.put("status", "error");
                result.put("message", "Failed to clone repository: " + 
                           new String(process.getErrorStream().readAllBytes()));
            }
        } catch (Exception e) {
            result.put("status", "error");
            result.put("message", e.getMessage());
        }
        
        return new ToolResult(result);
    }

    /**
     * Create a new branch.
     *
     * @param repoDir Directory of the Git repository
     * @param branchName Name of the branch to create
     * @param startPoint The commit at which to start the new branch
     * @return ToolResult containing the result of the operation
     */
    @xml_schema
    public ToolResult createBranch(String repoDir, String branchName, String startPoint) {
        Map<String, Object> result = new HashMap<>();
        
        try {
            // Ensure Git is available
            Map<String, Object> gitInfo = ensureGit();
            if (!isGitAvailable(gitInfo)) {
                result.put("status", "error");
                result.put("message", "Git not available: " + gitInfo.get("message"));
                return new ToolResult(result);
            }
            
            String gitPath = (String) gitInfo.get("path");
            
            // Change to repository directory
            String originalDir = System.getProperty("user.dir");
            System.setProperty("user.dir", repoDir);
            
            try {
                // Create branch
                List<String> cmd = new ArrayList<>();
                cmd.add(gitPath);
                cmd.add("branch");
                cmd.add(branchName);
                
                if (startPoint != null && !startPoint.isEmpty()) {
                    cmd.add(startPoint);
                }
                
                ProcessBuilder pb = new ProcessBuilder(cmd);
                Process process = pb.start();
                boolean completed = process.waitFor(2, TimeUnit.MINUTES);
                
                if (completed && process.exitValue() == 0) {
                    result.put("status", "success");
                    result.put("message", "Branch '" + branchName + "' created successfully");
                    result.put("output", new String(process.getInputStream().readAllBytes()));
                } else {
                    result.put("status", "error");
                    result.put("message", "Failed to create branch: " + 
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
     * Checkout a branch.
     *
     * @param repoDir Directory of the Git repository
     * @param branchName Name of the branch to checkout
     * @param create Whether to create the branch if it doesn't exist
     * @return ToolResult containing the result of the operation
     */
    @xml_schema
    public ToolResult checkoutBranch(String repoDir, String branchName, boolean create) {
        Map<String, Object> result = new HashMap<>();
        
        try {
            // Ensure Git is available
            Map<String, Object> gitInfo = ensureGit();
            if (!isGitAvailable(gitInfo)) {
                result.put("status", "error");
                result.put("message", "Git not available: " + gitInfo.get("message"));
                return new ToolResult(result);
            }
            
            String gitPath = (String) gitInfo.get("path");
            
            // Change to repository directory
            String originalDir = System.getProperty("user.dir");
            System.setProperty("user.dir", repoDir);
            
            try {
                // Checkout branch
                List<String> cmd = new ArrayList<>();
                cmd.add(gitPath);
                cmd.add("checkout");
                
                if (create) {
                    cmd.add("-b");
                }
                
                cmd.add(branchName);
                
                ProcessBuilder pb = new ProcessBuilder(cmd);
                Process process = pb.start();
                boolean completed = process.waitFor(2, TimeUnit.MINUTES);
                
                if (completed && process.exitValue() == 0) {
                    result.put("status", "success");
                    result.put("message", "Checked out branch '" + branchName + "' successfully");
                    result.put("output", new String(process.getInputStream().readAllBytes()));
                } else {
                    result.put("status", "error");
                    result.put("message", "Failed to checkout branch: " + 
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
     * List branches in the repository.
     *
     * @param repoDir Directory of the Git repository
     * @param all Whether to list all branches (local and remote)
     * @param remote Whether to list only remote branches
     * @return ToolResult containing the result of the operation
     */
    @xml_schema
    public ToolResult listBranches(String repoDir, boolean all, boolean remote) {
        Map<String, Object> result = new HashMap<>();
        
        try {
            // Ensure Git is available
            Map<String, Object> gitInfo = ensureGit();
            if (!isGitAvailable(gitInfo)) {
                result.put("status", "error");
                result.put("message", "Git not available: " + gitInfo.get("message"));
                return new ToolResult(result);
            }
            
            String gitPath = (String) gitInfo.get("path");
            
            // Change to repository directory
            String originalDir = System.getProperty("user.dir");
            System.setProperty("user.dir", repoDir);
            
            try {
                // List branches
                List<String> cmd = new ArrayList<>();
                cmd.add(gitPath);
                cmd.add("branch");
                
                if (all) {
                    cmd.add("--all");
                }
                
                if (remote) {
                    cmd.add("--remote");
                }
                
                ProcessBuilder pb = new ProcessBuilder(cmd);
                Process process = pb.start();
                boolean completed = process.waitFor(2, TimeUnit.MINUTES);
                
                if (completed && process.exitValue() == 0) {
                    // Parse branches
                    String output = new String(process.getInputStream().readAllBytes());
                    List<String> branches = new ArrayList<>();
                    String currentBranch = null;
                    
                    for (String line : output.split("\n")) {
                        line = line.trim();
                        if (line.startsWith("*")) {
                            String branch = line.substring(1).trim();
                            branches.add(branch);
                            currentBranch = branch;
                        } else if (!line.isEmpty()) {
                            branches.add(line);
                        }
                    }
                    
                    result.put("status", "success");
                    result.put("branches", branches);
                    result.put("current_branch", currentBranch);
                    result.put("output", output);
                } else {
                    result.put("status", "error");
                    result.put("message", "Failed to list branches: " + 
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
     * Add files to the staging area.
     *
     * @param repoDir Directory of the Git repository
     * @param files Files to add (if not specified, all files will be added)
     * @return ToolResult containing the result of the operation
     */
    @xml_schema
    public ToolResult addFiles(String repoDir, List<String> files) {
        Map<String, Object> result = new HashMap<>();
        
        try {
            // Ensure Git is available
            Map<String, Object> gitInfo = ensureGit();
            if (!isGitAvailable(gitInfo)) {
                result.put("status", "error");
                result.put("message", "Git not available: " + gitInfo.get("message"));
                return new ToolResult(result);
            }
            
            String gitPath = (String) gitInfo.get("path");
            
            // Change to repository directory
            String originalDir = System.getProperty("user.dir");
            System.setProperty("user.dir", repoDir);
            
            try {
                // Add files
                List<String> cmd = new ArrayList<>();
                cmd.add(gitPath);
                cmd.add("add");
                
                if (files != null && !files.isEmpty()) {
                    cmd.addAll(files);
                } else {
                    cmd.add(".");
                }
                
                ProcessBuilder pb = new ProcessBuilder(cmd);
                Process process = pb.start();
                boolean completed = process.waitFor(2, TimeUnit.MINUTES);
                
                if (completed && process.exitValue() == 0) {
                    result.put("status", "success");
                    result.put("message", "Files added to staging area successfully");
                    result.put("output", new String(process.getInputStream().readAllBytes()));
                } else {
                    result.put("status", "error");
                    result.put("message", "Failed to add files: " + 
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
     * Commit staged changes.
     *
     * @param repoDir Directory of the Git repository
     * @param message Commit message
     * @param author Author of the commit (format: 'Name <email>')
     * @return ToolResult containing the result of the operation
     */
    @xml_schema
    public ToolResult commit(String repoDir, String message, String author) {
        Map<String, Object> result = new HashMap<>();
        
        try {
            // Ensure Git is available
            Map<String, Object> gitInfo = ensureGit();
            if (!isGitAvailable(gitInfo)) {
                result.put("status", "error");
                result.put("message", "Git not available: " + gitInfo.get("message"));
                return new ToolResult(result);
            }
            
            String gitPath = (String) gitInfo.get("path");
            
            // Change to repository directory
            String originalDir = System.getProperty("user.dir");
            System.setProperty("user.dir", repoDir);
            
            try {
                // Commit changes
                List<String> cmd = new ArrayList<>();
                cmd.add(gitPath);
                cmd.add("commit");
                cmd.add("-m");
                cmd.add(message);
                
                if (author != null && !author.isEmpty()) {
                    cmd.add("--author");
                    cmd.add(author);
                }
                
                ProcessBuilder pb = new ProcessBuilder(cmd);
                Process process = pb.start();
                boolean completed = process.waitFor(2, TimeUnit.MINUTES);
                
                if (completed && process.exitValue() == 0) {
                    result.put("status", "success");
                    result.put("message", "Changes committed successfully");
                    result.put("output", new String(process.getInputStream().readAllBytes()));
                } else {
                    result.put("status", "error");
                    result.put("message", "Failed to commit changes: " + 
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
     * Get commit history.
     *
     * @param repoDir Directory of the Git repository
     * @param maxCount Maximum number of commits to return
     * @param skip Number of commits to skip
     * @param author Filter commits by author
     * @param since Show commits more recent than a specific date
     * @param until Show commits older than a specific date
     * @param path Only show commits that affect the specified path
     * @return ToolResult containing the result of the operation
     */
    @xml_schema
    public ToolResult getCommitHistory(String repoDir, Integer maxCount, Integer skip, 
                                      String author, String since, String until, String path) {
        Map<String, Object> result = new HashMap<>();
        
        try {
            // Ensure Git is available
            Map<String, Object> gitInfo = ensureGit();
            if (!isGitAvailable(gitInfo)) {
                result.put("status", "error");
                result.put("message", "Git not available: " + gitInfo.get("message"));
                return new ToolResult(result);
            }
            
            String gitPath = (String) gitInfo.get("path");
            
            // Change to repository directory
            String originalDir = System.getProperty("user.dir");
            System.setProperty("user.dir", repoDir);
            
            try {
                // Get commit history
                List<String> cmd = new ArrayList<>();
                cmd.add(gitPath);
                cmd.add("log");
                cmd.add("--pretty=format:%H|%an|%ae|%at|%s");
                
                if (maxCount != null && maxCount > 0) {
                    cmd.add("--max-count");
                    cmd.add(maxCount.toString());
                }
                
                if (skip != null && skip > 0) {
                    cmd.add("--skip");
                    cmd.add(skip.toString());
                }
                
                if (author != null && !author.isEmpty()) {
                    cmd.add("--author");
                    cmd.add(author);
                }
                
                if (since != null && !since.isEmpty()) {
                    cmd.add("--since");
                    cmd.add(since);
                }
                
                if (until != null && !until.isEmpty()) {
                    cmd.add("--until");
                    cmd.add(until);
                }
                
                if (path != null && !path.isEmpty()) {
                    cmd.add("--");
                    cmd.add(path);
                }
                
                ProcessBuilder pb = new ProcessBuilder(cmd);
                Process process = pb.start();
                boolean completed = process.waitFor(2, TimeUnit.MINUTES);
                
                if (completed && process.exitValue() == 0) {
                    // Parse commit history
                    String output = new String(process.getInputStream().readAllBytes());
                    List<Map<String, Object>> commits = new ArrayList<>();
                    
                    for (String line : output.split("\n")) {
                        if (line.trim().isEmpty()) {
                            continue;
                        }
                        
                        String[] parts = line.split("\\|");
                        if (parts.length >= 5) {
                            Map<String, Object> commit = new HashMap<>();
                            commit.put("hash", parts[0]);
                            commit.put("author_name", parts[1]);
                            commit.put("author_email", parts[2]);
                            commit.put("timestamp", Integer.parseInt(parts[3]));
                            commit.put("message", parts[4]);
                            commits.add(commit);
                        }
                    }
                    
                    result.put("status", "success");
                    result.put("commits", commits);
                    result.put("output", output);
                } else {
                    result.put("status", "error");
                    result.put("message", "Failed to get commit history: " + 
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
     * Add a remote repository.
     *
     * @param repoDir Directory of the Git repository
     * @param name Name of the remote
     * @param url URL of the remote repository
     * @return ToolResult containing the result of the operation
     */
    @xml_schema
    public ToolResult addRemote(String repoDir, String name, String url) {
        Map<String, Object> result = new HashMap<>();
        
        try {
            // Ensure Git is available
            Map<String, Object> gitInfo = ensureGit();
            if (!isGitAvailable(gitInfo)) {
                result.put("status", "error");
                result.put("message", "Git not available: " + gitInfo.get("message"));
                return new ToolResult(result);
            }
            
            String gitPath = (String) gitInfo.get("path");
            
            // Change to repository directory
            String originalDir = System.getProperty("user.dir");
            System.setProperty("user.dir", repoDir);
            
            try {
                // Add remote
                List<String> cmd = new ArrayList<>();
                cmd.add(gitPath);
                cmd.add("remote");
                cmd.add("add");
                cmd.add(name);
                cmd.add(url);
                
                ProcessBuilder pb = new ProcessBuilder(cmd);
                Process process = pb.start();
                boolean completed = process.waitFor(2, TimeUnit.MINUTES);
                
                if (completed && process.exitValue() == 0) {
                    result.put("status", "success");
                    result.put("message", "Remote '" + name + "' added successfully");
                    result.put("output", new String(process.getInputStream().readAllBytes()));
                } else {
                    result.put("status", "error");
                    result.put("message", "Failed to add remote: " + 
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
     * List remote repositories.
     *
     * @param repoDir Directory of the Git repository
     * @param verbose Whether to show remote URLs
     * @return ToolResult containing the result of the operation
     */
    @xml_schema
    public ToolResult listRemotes(String repoDir, boolean verbose) {
        Map<String, Object> result = new HashMap<>();
        
        try {
            // Ensure Git is available
            Map<String, Object> gitInfo = ensureGit();
            if (!isGitAvailable(gitInfo)) {
                result.put("status", "error");
                result.put("message", "Git not available: " + gitInfo.get("message"));
                return new ToolResult(result);
            }
            
            String gitPath = (String) gitInfo.get("path");
            
            // Change to repository directory
            String originalDir = System.getProperty("user.dir");
            System.setProperty("user.dir", repoDir);
            
            try {
                // List remotes
                List<String> cmd = new ArrayList<>();
                cmd.add(gitPath);
                cmd.add("remote");
                
                if (verbose) {
                    cmd.add("-v");
                }
                
                ProcessBuilder pb = new ProcessBuilder(cmd);
                Process process = pb.start();
                boolean completed = process.waitFor(2, TimeUnit.MINUTES);
                
                if (completed && process.exitValue() == 0) {
                    // Parse remotes
                    String output = new String(process.getInputStream().readAllBytes());
                    List<Object> remotes = new ArrayList<>();
                    
                    if (verbose) {
                        for (String line : output.split("\n")) {
                            if (line.trim().isEmpty()) {
                                continue;
                            }
                            
                            String[] parts = line.split("\\s+");
                            if (parts.length >= 3) {
                                Map<String, String> remote = new HashMap<>();
                                remote.put("name", parts[0]);
                                remote.put("url", parts[1]);
                                remote.put("type", parts[2].replaceAll("[()]", ""));
                                remotes.add(remote);
                            }
                        }
                    } else {
                        for (String line : output.split("\n")) {
                            if (!line.trim().isEmpty()) {
                                remotes.add(line.trim());
                            }
                        }
                    }
                    
                    result.put("status", "success");
                    result.put("remotes", remotes);
                    result.put("output", output);
                } else {
                    result.put("status", "error");
                    result.put("message", "Failed to list remotes: " + 
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
     * Push changes to a remote repository.
     *
     * @param repoDir Directory of the Git repository
     * @param remote Name of the remote
     * @param branch Branch to push
     * @param force Whether to force push
     * @param setUpstream Whether to set the upstream for the branch
     * @return ToolResult containing the result of the operation
     */
    @xml_schema
    public ToolResult push(String repoDir, String remote, String branch, boolean force, boolean setUpstream) {
        Map<String, Object> result = new HashMap<>();
        
        try {
            // Ensure Git is available
            Map<String, Object> gitInfo = ensureGit();
            if (!isGitAvailable(gitInfo)) {
                result.put("status", "error");
                result.put("message", "Git not available: " + gitInfo.get("message"));
                return new ToolResult(result);
            }
            
            String gitPath = (String) gitInfo.get("path");
            
            // Change to repository directory
            String originalDir = System.getProperty("user.dir");
            System.setProperty("user.dir", repoDir);
            
            try {
                // Push changes
                List<String> cmd = new ArrayList<>();
                cmd.add(gitPath);
                cmd.add("push");
                
                if (force) {
                    cmd.add("--force");
                }
                
                if (setUpstream) {
                    cmd.add("--set-upstream");
                }
                
                if (remote != null && !remote.isEmpty()) {
                    cmd.add(remote);
                }
                
                if (branch != null && !branch.isEmpty()) {
                    cmd.add(branch);
                }
                
                ProcessBuilder pb = new ProcessBuilder(cmd);
                Process process = pb.start();
                boolean completed = process.waitFor(5, TimeUnit.MINUTES);
                
                if (completed && process.exitValue() == 0) {
                    result.put("status", "success");
                    result.put("message", "Changes pushed successfully");
                    result.put("output", new String(process.getInputStream().readAllBytes()));
                } else {
                    result.put("status", "error");
                    result.put("message", "Failed to push changes: " + 
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
     * Pull changes from a remote repository.
     *
     * @param repoDir Directory of the Git repository
     * @param remote Name of the remote
     * @param branch Branch to pull
     * @param rebase Whether to rebase instead of merge
     * @return ToolResult containing the result of the operation
     */
    @xml_schema
    public ToolResult pull(String repoDir, String remote, String branch, boolean rebase) {
        Map<String, Object> result = new HashMap<>();
        
        try {
            // Ensure Git is available
            Map<String, Object> gitInfo = ensureGit();
            if (!isGitAvailable(gitInfo)) {
                result.put("status", "error");
                result.put("message", "Git not available: " + gitInfo.get("message"));
                return new ToolResult(result);
            }
            
            String gitPath = (String) gitInfo.get("path");
            
            // Change to repository directory
            String originalDir = System.getProperty("user.dir");
            System.setProperty("user.dir", repoDir);
            
            try {
                // Pull changes
                List<String> cmd = new ArrayList<>();
                cmd.add(gitPath);
                cmd.add("pull");
                
                if (rebase) {
                    cmd.add("--rebase");
                }
                
                if (remote != null && !remote.isEmpty()) {
                    cmd.add(remote);
                }
                
                if (branch != null && !branch.isEmpty()) {
                    cmd.add(branch);
                }
                
                ProcessBuilder pb = new ProcessBuilder(cmd);
                Process process = pb.start();
                boolean completed = process.waitFor(5, TimeUnit.MINUTES);
                
                if (completed && process.exitValue() == 0) {
                    result.put("status", "success");
                    result.put("message", "Changes pulled successfully");
                    result.put("output", new String(process.getInputStream().readAllBytes()));
                } else {
                    result.put("status", "error");
                    result.put("message", "Failed to pull changes: " + 
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
     * Get repository status.
     *
     * @param repoDir Directory of the Git repository
     * @param shortFormat Whether to show status in short format
     * @return ToolResult containing the result of the operation
     */
    @xml_schema
    public ToolResult getStatus(String repoDir, boolean shortFormat) {
        Map<String, Object> result = new HashMap<>();
        
        try {
            // Ensure Git is available
            Map<String, Object> gitInfo = ensureGit();
            if (!isGitAvailable(gitInfo)) {
                result.put("status", "error");
                result.put("message", "Git not available: " + gitInfo.get("message"));
                return new ToolResult(result);
            }
            
            String gitPath = (String) gitInfo.get("path");
            
            // Change to repository directory
            String originalDir = System.getProperty("user.dir");
            System.setProperty("user.dir", repoDir);
            
            try {
                // Get status
                List<String> cmd = new ArrayList<>();
                cmd.add(gitPath);
                cmd.add("status");
                
                if (shortFormat) {
                    cmd.add("--short");
                }
                
                ProcessBuilder pb = new ProcessBuilder(cmd);
                Process process = pb.start();
                boolean completed = process.waitFor(2, TimeUnit.MINUTES);
                
                if (completed && process.exitValue() == 0) {
                    String output = new String(process.getInputStream().readAllBytes());
                    result.put("status", "success");
                    result.put("git_status", output);
                    result.put("output", output);
                } else {
                    result.put("status", "error");
                    result.put("message", "Failed to get status: " + 
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
     * Get diff of changes.
     *
     * @param repoDir Directory of the Git repository
     * @param file File to get diff for
     * @param staged Whether to show staged changes
     * @return ToolResult containing the result of the operation
     */
    @xml_schema
    public ToolResult getDiff(String repoDir, String file, boolean staged) {
        Map<String, Object> result = new HashMap<>();
        
        try {
            // Ensure Git is available
            Map<String, Object> gitInfo = ensureGit();
            if (!isGitAvailable(gitInfo)) {
                result.put("status", "error");
                result.put("message", "Git not available: " + gitInfo.get("message"));
                return new ToolResult(result);
            }
            
            String gitPath = (String) gitInfo.get("path");
            
            // Change to repository directory
            String originalDir = System.getProperty("user.dir");
            System.setProperty("user.dir", repoDir);
            
            try {
                // Get diff
                List<String> cmd = new ArrayList<>();
                cmd.add(gitPath);
                cmd.add("diff");
                
                if (staged) {
                    cmd.add("--staged");
                }
                
                if (file != null && !file.isEmpty()) {
                    cmd.add("--");
                    cmd.add(file);
                }
                
                ProcessBuilder pb = new ProcessBuilder(cmd);
                Process process = pb.start();
                boolean completed = process.waitFor(2, TimeUnit.MINUTES);
                
                if (completed && process.exitValue() == 0) {
                    String output = new String(process.getInputStream().readAllBytes());
                    result.put("status", "success");
                    result.put("diff", output);
                    result.put("output", output);
                } else {
                    result.put("status", "error");
                    result.put("message", "Failed to get diff: " + 
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
     * Check if Git is available based on the result of ensureGit.
     *
     * @param gitInfo Result of ensureGit
     * @return true if Git is available, false otherwise
     */
    private boolean isGitAvailable(Map<String, Object> gitInfo) {
        return gitInfo != null && 
               (gitInfo.get("status").equals("found") || 
                gitInfo.get("status").equals("installed"));
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
        schema.put("description", "Execute Git commands and manage Git repositories");
        
        List<Map<String, Object>> functions = new ArrayList<>();
        
        // init_repo function
        Map<String, Object> initRepoFunction = new HashMap<>();
        initRepoFunction.put("name", "init_repo");
        initRepoFunction.put("description", "Initialize a new Git repository");
        
        List<Map<String, Object>> initRepoParams = new ArrayList<>();
        
        Map<String, Object> repoDirParam = new HashMap<>();
        repoDirParam.put("name", "repo_dir");
        repoDirParam.put("type", "string");
        repoDirParam.put("description", "Directory where the Git repository should be created");
        repoDirParam.put("required", true);
        initRepoParams.add(repoDirParam);
        
        Map<String, Object> bareParam = new HashMap<>();
        bareParam.put("name", "bare");
        bareParam.put("type", "boolean");
        bareParam.put("description", "Whether to create a bare repository");
        bareParam.put("required", false);
        bareParam.put("default", false);
        initRepoParams.add(bareParam);
        
        initRepoFunction.put("parameters", initRepoParams);
        functions.add(initRepoFunction);
        
        // clone_repo function
        Map<String, Object> cloneRepoFunction = new HashMap<>();
        cloneRepoFunction.put("name", "clone_repo");
        cloneRepoFunction.put("description", "Clone a Git repository");
        
        List<Map<String, Object>> cloneRepoParams = new ArrayList<>();
        
        Map<String, Object> repoUrlParam = new HashMap<>();
        repoUrlParam.put("name", "repo_url");
        repoUrlParam.put("type", "string");
        repoUrlParam.put("description", "URL of the Git repository to clone");
        repoUrlParam.put("required", true);
        cloneRepoParams.add(repoUrlParam);
        
        Map<String, Object> targetDirParam = new HashMap<>();
        targetDirParam.put("name", "target_dir");
        targetDirParam.put("type", "string");
        targetDirParam.put("description", "Directory where the repository should be cloned");
        targetDirParam.put("required", true);
        cloneRepoParams.add(targetDirParam);
        
        Map<String, Object> branchParam = new HashMap<>();
        branchParam.put("name", "branch");
        branchParam.put("type", "string");
        branchParam.put("description", "Branch to checkout after cloning");
        branchParam.put("required", false);
        cloneRepoParams.add(branchParam);
        
        Map<String, Object> depthParam = new HashMap<>();
        depthParam.put("name", "depth");
        depthParam.put("type", "integer");
        depthParam.put("description", "Create a shallow clone with a history truncated to the specified number of commits");
        depthParam.put("required", false);
        cloneRepoParams.add(depthParam);
        
        cloneRepoFunction.put("parameters", cloneRepoParams);
        functions.add(cloneRepoFunction);
        
        // Additional functions would be defined similarly...
        
        // For brevity, we'll add just a few more key functions
        
        // create_branch function
        Map<String, Object> createBranchFunction = new HashMap<>();
        createBranchFunction.put("name", "create_branch");
        createBranchFunction.put("description", "Create a new branch");
        
        List<Map<String, Object>> createBranchParams = new ArrayList<>();
        
        Map<String, Object> branchRepoDirParam = new HashMap<>();
        branchRepoDirParam.put("name", "repo_dir");
        branchRepoDirParam.put("type", "string");
        branchRepoDirParam.put("description", "Directory of the Git repository");
        branchRepoDirParam.put("required", true);
        createBranchParams.add(branchRepoDirParam);
        
        Map<String, Object> branchNameParam = new HashMap<>();
        branchNameParam.put("name", "branch_name");
        branchNameParam.put("type", "string");
        branchNameParam.put("description", "Name of the branch to create");
        branchNameParam.put("required", true);
        createBranchParams.add(branchNameParam);
        
        Map<String, Object> startPointParam = new HashMap<>();
        startPointParam.put("name", "start_point");
        startPointParam.put("type", "string");
        startPointParam.put("description", "The commit at which to start the new branch");
        startPointParam.put("required", false);
        createBranchParams.add(startPointParam);
        
        createBranchFunction.put("parameters", createBranchParams);
        functions.add(createBranchFunction);
        
        // commit function
        Map<String, Object> commitFunction = new HashMap<>();
        commitFunction.put("name", "commit");
        commitFunction.put("description", "Commit staged changes");
        
        List<Map<String, Object>> commitParams = new ArrayList<>();
        
        Map<String, Object> commitRepoDirParam = new HashMap<>();
        commitRepoDirParam.put("name", "repo_dir");
        commitRepoDirParam.put("type", "string");
        commitRepoDirParam.put("description", "Directory of the Git repository");
        commitRepoDirParam.put("required", true);
        commitParams.add(commitRepoDirParam);
        
        Map<String, Object> messageParam = new HashMap<>();
        messageParam.put("name", "message");
        messageParam.put("type", "string");
        messageParam.put("description", "Commit message");
        messageParam.put("required", true);
        commitParams.add(messageParam);
        
        Map<String, Object> authorParam = new HashMap<>();
        authorParam.put("name", "author");
        authorParam.put("type", "string");
        authorParam.put("description", "Author of the commit (format: 'Name <email>')");
        authorParam.put("required", false);
        commitParams.add(authorParam);
        
        commitFunction.put("parameters", commitParams);
        functions.add(commitFunction);
        
        // push function
        Map<String, Object> pushFunction = new HashMap<>();
        pushFunction.put("name", "push");
        pushFunction.put("description", "Push changes to a remote repository");
        
        List<Map<String, Object>> pushParams = new ArrayList<>();
        
        Map<String, Object> pushRepoDirParam = new HashMap<>();
        pushRepoDirParam.put("name", "repo_dir");
        pushRepoDirParam.put("type", "string");
        pushRepoDirParam.put("description", "Directory of the Git repository");
        pushRepoDirParam.put("required", true);
        pushParams.add(pushRepoDirParam);
        
        Map<String, Object> remoteParam = new HashMap<>();
        remoteParam.put("name", "remote");
        remoteParam.put("type", "string");
        remoteParam.put("description", "Name of the remote");
        remoteParam.put("required", false);
        pushParams.add(remoteParam);
        
        Map<String, Object> pushBranchParam = new HashMap<>();
        pushBranchParam.put("name", "branch");
        pushBranchParam.put("type", "string");
        pushBranchParam.put("description", "Branch to push");
        pushBranchParam.put("required", false);
        pushParams.add(pushBranchParam);
        
        Map<String, Object> forceParam = new HashMap<>();
        forceParam.put("name", "force");
        forceParam.put("type", "boolean");
        forceParam.put("description", "Whether to force push");
        forceParam.put("required", false);
        forceParam.put("default", false);
        pushParams.add(forceParam);
        
        Map<String, Object> setUpstreamParam = new HashMap<>();
        setUpstreamParam.put("name", "set_upstream");
        setUpstreamParam.put("type", "boolean");
        setUpstreamParam.put("description", "Whether to set the upstream for the branch");
        setUpstreamParam.put("required", false);
        setUpstreamParam.put("default", false);
        pushParams.add(setUpstreamParam);
        
        pushFunction.put("parameters", pushParams);
        functions.add(pushFunction);
        
        schema.put("functions", functions);
        return schema;
    }
}
