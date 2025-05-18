"""
System Information tool for retrieving system information within the sandbox.
"""

import os
import platform
import json
import subprocess
from typing import Optional, Dict, Any, List

from agentpress.tool import ToolResult, openapi_schema, xml_schema
from sandbox.tool_base import SandboxToolsBase
from agentpress.thread_manager import ThreadManager
from utils.logger import logger

class SystemInfoTool(SandboxToolsBase):
    """Tool for retrieving system information within the sandbox."""

    def __init__(self, project_id: str, thread_id: str, thread_manager: ThreadManager):
        super().__init__(project_id, thread_manager)
        self.thread_id = thread_id
        self.thread_manager = thread_manager

    @openapi_schema({
        "type": "function",
        "function": {
            "name": "get_system_info",
            "description": "Retrieves system information such as OS details, CPU, memory, disk usage, and running processes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "include_processes": {
                        "type": "boolean",
                        "description": "Whether to include information about running processes",
                        "default": False
                    },
                    "include_network": {
                        "type": "boolean",
                        "description": "Whether to include network interface information",
                        "default": False
                    },
                    "include_environment": {
                        "type": "boolean",
                        "description": "Whether to include environment variables",
                        "default": False
                    },
                    "output_format": {
                        "type": "string",
                        "description": "Format for the output",
                        "enum": ["text", "json", "markdown"],
                        "default": "text"
                    },
                    "output_path": {
                        "type": "string",
                        "description": "Optional path to save the system information to a file"
                    }
                }
            }
        }
    })
    @xml_schema(
        tag_name="get-system-info",
        mappings=[
            {"param_name": "include_processes", "node_type": "attribute", "path": "."},
            {"param_name": "include_network", "node_type": "attribute", "path": "."},
            {"param_name": "include_environment", "node_type": "attribute", "path": "."},
            {"param_name": "output_format", "node_type": "attribute", "path": "."},
            {"param_name": "output_path", "node_type": "attribute", "path": "."}
        ],
        example='''
        <!-- Example: Get detailed system information in markdown format -->
        <get-system-info include_processes="true" include_network="true" output_format="markdown"></get-system-info>
        '''
    )
    async def get_system_info(self, 
                            include_processes: bool = False,
                            include_network: bool = False,
                            include_environment: bool = False,
                            output_format: str = "text",
                            output_path: Optional[str] = None) -> ToolResult:
        """Retrieves system information."""
        try:
            # Ensure sandbox is initialized
            await self._ensure_sandbox()
            
            # Create Python script for system info
            script_content = self._generate_system_info_script(
                include_processes=include_processes,
                include_network=include_network,
                include_environment=include_environment,
                output_format=output_format
            )
            
            # Save script to temporary file
            script_path = "/tmp/system_info_script.py"
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
                return self.fail_response(f"Failed to retrieve system information: {error_output}")
            
            # Get the output
            output = await result.get_output()
            
            # If output path was specified, save to file
            if output_path:
                cleaned_output_path = self.clean_path(output_path)
                full_output_path = f"{self.workspace_path}/{cleaned_output_path}"
                
                # Create directory if it doesn't exist
                dir_path = "/".join(full_output_path.split("/")[:-1])
                await self.sandbox.exec.start(
                    command=f"mkdir -p {dir_path}"
                )
                
                # Save the system info to file
                self.sandbox.fs.upload_file(full_output_path, output.encode('utf-8'))
                
                return self.success_response(f"System information saved to {cleaned_output_path}")
            else:
                return self.success_response(output)
            
        except Exception as e:
            logger.error(f"Error retrieving system information: {str(e)}", exc_info=True)
            return self.fail_response(f"Failed to retrieve system information: {str(e)}")
    
    def _generate_system_info_script(self, 
                                   include_processes: bool,
                                   include_network: bool,
                                   include_environment: bool,
                                   output_format: str) -> str:
        """Generate Python script for system information."""
        script = f"""
import os
import sys
import platform
import psutil
import json
import socket
import datetime
from tabulate import tabulate

def get_size(bytes, suffix="B"):
    '''
    Scale bytes to its proper format
    e.g:
        1253656 => '1.20MB'
        1253656678 => '1.17GB'
    '''
    factor = 1024
    for unit in ["", "K", "M", "G", "T", "P"]:
        if bytes < factor:
            return f"{{bytes:.2f}}{{unit}}{{suffix}}"
        bytes /= factor

def get_system_info():
    # System information dictionary
    info = {{}}
    
    # System information
    info["system"] = {{
        "system": platform.system(),
        "node_name": platform.node(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python_version": platform.python_version(),
        "current_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }}
    
    # Boot time
    boot_time_timestamp = psutil.boot_time()
    bt = datetime.datetime.fromtimestamp(boot_time_timestamp)
    info["boot_time"] = {{
        "timestamp": boot_time_timestamp,
        "formatted": bt.strftime("%Y-%m-%d %H:%M:%S")
    }}
    
    # CPU information
    info["cpu"] = {{
        "physical_cores": psutil.cpu_count(logical=False),
        "total_cores": psutil.cpu_count(logical=True),
        "max_frequency": f"{{psutil.cpu_freq().max:.2f}}Mhz" if psutil.cpu_freq() else "Unknown",
        "current_frequency": f"{{psutil.cpu_freq().current:.2f}}Mhz" if psutil.cpu_freq() else "Unknown",
        "usage_per_core": [f"{{x}}%" for x in psutil.cpu_percent(percpu=True, interval=1)],
        "total_usage": f"{{psutil.cpu_percent()}}%"
    }}
    
    # Memory information
    svmem = psutil.virtual_memory()
    info["memory"] = {{
        "total": get_size(svmem.total),
        "available": get_size(svmem.available),
        "used": get_size(svmem.used),
        "percentage": f"{{svmem.percent}}%"
    }}
    
    # Swap information
    swap = psutil.swap_memory()
    info["swap"] = {{
        "total": get_size(swap.total),
        "free": get_size(swap.free),
        "used": get_size(swap.used),
        "percentage": f"{{swap.percent}}%"
    }}
    
    # Disk information
    info["disks"] = []
    partitions = psutil.disk_partitions()
    for partition in partitions:
        try:
            partition_usage = psutil.disk_usage(partition.mountpoint)
            disk_info = {{
                "device": partition.device,
                "mountpoint": partition.mountpoint,
                "file_system_type": partition.fstype,
                "total_size": get_size(partition_usage.total),
                "used": get_size(partition_usage.used),
                "free": get_size(partition_usage.free),
                "percentage": f"{{partition_usage.percent}}%"
            }}
            info["disks"].append(disk_info)
        except PermissionError:
            # This can happen if the disk isn't ready or is protected
            continue
    
    # Network information
    if {str(include_network).lower()}:
        info["network"] = {{}}
        
        # Get hostname
        info["network"]["hostname"] = socket.gethostname()
        
        # Get IP address
        try:
            info["network"]["ip_address"] = socket.gethostbyname(socket.gethostname())
        except:
            info["network"]["ip_address"] = "Unknown"
        
        # Get all network interfaces
        info["network"]["interfaces"] = []
        if_addrs = psutil.net_if_addrs()
        for interface_name, interface_addresses in if_addrs.items():
            interface_info = {{"name": interface_name, "addresses": []}}
            for address in interface_addresses:
                addr_info = {{
                    "family": str(address.family),
                    "address": address.address,
                    "netmask": address.netmask,
                    "broadcast": address.broadcast
                }}
                interface_info["addresses"].append(addr_info)
            info["network"]["interfaces"].append(interface_info)
        
        # Get network IO statistics
        net_io = psutil.net_io_counters()
        info["network"]["io"] = {{
            "bytes_sent": get_size(net_io.bytes_sent),
            "bytes_received": get_size(net_io.bytes_recv),
            "packets_sent": net_io.packets_sent,
            "packets_received": net_io.packets_recv,
            "errors_in": net_io.errin,
            "errors_out": net_io.errout,
            "dropped_in": net_io.dropin,
            "dropped_out": net_io.dropout
        }}
    
    # Process information
    if {str(include_processes).lower()}:
        info["processes"] = []
        for proc in psutil.process_iter(['pid', 'name', 'username', 'memory_percent', 'cpu_percent', 'create_time', 'status']):
            try:
                process_info = proc.info
                process_info['memory_usage'] = get_size(proc.memory_info().rss)
                if 'create_time' in process_info and process_info['create_time']:
                    process_info['create_time'] = datetime.datetime.fromtimestamp(process_info['create_time']).strftime("%Y-%m-%d %H:%M:%S")
                info["processes"].append(process_info)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        
        # Sort processes by memory usage
        info["processes"] = sorted(info["processes"], key=lambda x: x.get('memory_percent', 0), reverse=True)
    
    # Environment variables
    if {str(include_environment).lower()}:
        info["environment"] = dict(os.environ)
    
    return info

def format_output(info, format_type):
    if format_type == "json":
        return json.dumps(info, indent=4)
    
    elif format_type == "markdown":
        md_output = []
        
        # System Information
        md_output.append("# System Information")
        md_output.append(f"**System:** {{info['system']['system']}}")
        md_output.append(f"**Node Name:** {{info['system']['node_name']}}")
        md_output.append(f"**Release:** {{info['system']['release']}}")
        md_output.append(f"**Version:** {{info['system']['version']}}")
        md_output.append(f"**Machine:** {{info['system']['machine']}}")
        md_output.append(f"**Processor:** {{info['system']['processor']}}")
        md_output.append(f"**Python Version:** {{info['system']['python_version']}}")
        md_output.append(f"**Current Time:** {{info['system']['current_time']}}")
        md_output.append("")
        
        # Boot Time
        md_output.append("## Boot Time")
        md_output.append(f"**Boot Time:** {{info['boot_time']['formatted']}}")
        md_output.append("")
        
        # CPU Information
        md_output.append("## CPU Information")
        md_output.append(f"**Physical Cores:** {{info['cpu']['physical_cores']}}")
        md_output.append(f"**Total Cores:** {{info['cpu']['total_cores']}}")
        md_output.append(f"**Max Frequency:** {{info['cpu']['max_frequency']}}")
        md_output.append(f"**Current Frequency:** {{info['cpu']['current_frequency']}}")
        md_output.append(f"**Total CPU Usage:** {{info['cpu']['total_usage']}}")
        md_output.append("")
        
        # CPU Usage Per Core
        md_output.append("### CPU Usage Per Core")
        for i, usage in enumerate(info['cpu']['usage_per_core']):
            md_output.append(f"**Core {{i}}:** {{usage}}")
        md_output.append("")
        
        # Memory Information
        md_output.append("## Memory Information")
        md_output.append(f"**Total:** {{info['memory']['total']}}")
        md_output.append(f"**Available:** {{info['memory']['available']}}")
        md_output.append(f"**Used:** {{info['memory']['used']}}")
        md_output.append(f"**Percentage:** {{info['memory']['percentage']}}")
        md_output.append("")
        
        # Swap Information
        md_output.append("## Swap Information")
        md_output.append(f"**Total:** {{info['swap']['total']}}")
        md_output.append(f"**Free:** {{info['swap']['free']}}")
        md_output.append(f"**Used:** {{info['swap']['used']}}")
        md_output.append(f"**Percentage:** {{info['swap']['percentage']}}")
        md_output.append("")
        
        # Disk Information
        md_output.append("## Disk Information")
        for disk in info['disks']:
            md_output.append(f"### {{disk['device']}}")
            md_output.append(f"**Mountpoint:** {{disk['mountpoint']}}")
            md_output.append(f"**File System Type:** {{disk['file_system_type']}}")
            md_output.append(f"**Total Size:** {{disk['total_size']}}")
            md_output.append(f"**Used:** {{disk['used']}}")
            md_output.append(f"**Free:** {{disk['free']}}")
            md_output.append(f"**Percentage:** {{disk['percentage']}}")
            md_output.append("")
        
        # Network Information
        if 'network' in info:
            md_output.append("## Network Information")
            md_output.append(f"**Hostname:** {{info['network']['hostname']}}")
            md_output.append(f"**IP Address:** {{info['network']['ip_address']}}")
            
            md_output.append("### Network Interfaces")
            for interface in info['network']['interfaces']:
                md_output.append(f"#### {{interface['name']}}")
                for addr in interface['addresses']:
                    md_output.append(f"**Family:** {{addr['family']}}")
                    md_output.append(f"**Address:** {{addr['address']}}")
                    if addr['netmask']:
                        md_output.append(f"**Netmask:** {{addr['netmask']}}")
                    if addr['broadcast']:
                        md_output.append(f"**Broadcast:** {{addr['broadcast']}}")
                    md_output.append("")
            
            md_output.append("### Network I/O")
            md_output.append(f"**Bytes Sent:** {{info['network']['io']['bytes_sent']}}")
            md_output.append(f"**Bytes Received:** {{info['network']['io']['bytes_received']}}")
            md_output.append(f"**Packets Sent:** {{info['network']['io']['packets_sent']}}")
            md_output.append(f"**Packets Received:** {{info['network']['io']['packets_received']}}")
            md_output.append("")
        
        # Process Information
        if 'processes' in info:
            md_output.append("## Process Information")
            md_output.append("| PID | Name | User | Memory Usage | Memory % | CPU % | Status | Created |")
            md_output.append("|-----|------|------|-------------|----------|-------|--------|---------|")
            for proc in info['processes'][:20]:  # Show top 20 processes by memory usage
                md_output.append(f"| {{proc.get('pid', 'N/A')}} | {{proc.get('name', 'N/A')}} | {{proc.get('username', 'N/A')}} | {{proc.get('memory_usage', 'N/A')}} | {{proc.get('memory_percent', 'N/A'):.2f}}% | {{proc.get('cpu_percent', 'N/A'):.2f}}% | {{proc.get('status', 'N/A')}} | {{proc.get('create_time', 'N/A')}} |")
            md_output.append("")
        
        # Environment Variables
        if 'environment' in info:
            md_output.append("## Environment Variables")
            md_output.append("| Variable | Value |")
            md_output.append("|----------|-------|")
            for key, value in info['environment'].items():
                md_output.append(f"| {{key}} | {{value}} |")
            md_output.append("")
        
        return "\\n".join(md_output)
    
    else:  # text format
        text_output = []
        
        # System Information
        text_output.append("="*40 + " System Information " + "="*40)
        text_output.append(f"System: {{info['system']['system']}}")
        text_output.append(f"Node Name: {{info['system']['node_name']}}")
        text_output.append(f"Release: {{info['system']['release']}}")
        text_output.append(f"Version: {{info['system']['version']}}")
        text_output.append(f"Machine: {{info['system']['machine']}}")
        text_output.append(f"Processor: {{info['system']['processor']}}")
        text_output.append(f"Python Version: {{info['system']['python_version']}}")
        text_output.append(f"Current Time: {{info['system']['current_time']}}")
        text_output.append("")
        
        # Boot Time
        text_output.append("="*40 + " Boot Time " + "="*40)
        text_output.append(f"Boot Time: {{info['boot_time']['formatted']}}")
        text_output.append("")
        
        # CPU Information
        text_output.append("="*40 + " CPU Information " + "="*40)
        text_output.append(f"Physical Cores: {{info['cpu']['physical_cores']}}")
        text_output.append(f"Total Cores: {{info['cpu']['total_cores']}}")
        text_output.append(f"Max Frequency: {{info['cpu']['max_frequency']}}")
        text_output.append(f"Current Frequency: {{info['cpu']['current_frequency']}}")
        text_output.append(f"Total CPU Usage: {{info['cpu']['total_usage']}}")
        text_output.append("")
        
        # CPU Usage Per Core
        text_output.append("-"*20 + " CPU Usage Per Core " + "-"*20)
        for i, usage in enumerate(info['cpu']['usage_per_core']):
            text_output.append(f"Core {{i}}: {{usage}}")
        text_output.append("")
        
        # Memory Information
        text_output.append("="*40 + " Memory Information " + "="*40)
        text_output.append(f"Total: {{info['memory']['total']}}")
        text_output.append(f"Available: {{info['memory']['available']}}")
        text_output.append(f"Used: {{info['memory']['used']}}")
        text_output.append(f"Percentage: {{info['memory']['percentage']}}")
        text_output.append("")
        
        # Swap Information
        text_output.append("="*40 + " Swap Information " + "="*40)
        text_output.append(f"Total: {{info['swap']['total']}}")
        text_output.append(f"Free: {{info['swap']['free']}}")
        text_output.append(f"Used: {{info['swap']['used']}}")
        text_output.append(f"Percentage: {{info['swap']['percentage']}}")
        text_output.append("")
        
        # Disk Information
        text_output.append("="*40 + " Disk Information " + "="*40)
        for disk in info['disks']:
            text_output.append(f"Device: {{disk['device']}}")
            text_output.append(f"Mountpoint: {{disk['mountpoint']}}")
            text_output.append(f"File System Type: {{disk['file_system_type']}}")
            text_output.append(f"Total Size: {{disk['total_size']}}")
            text_output.append(f"Used: {{disk['used']}}")
            text_output.append(f"Free: {{disk['free']}}")
            text_output.append(f"Percentage: {{disk['percentage']}}")
            text_output.append("-"*50)
        text_output.append("")
        
        # Network Information
        if 'network' in info:
            text_output.append("="*40 + " Network Information " + "="*40)
            text_output.append(f"Hostname: {{info['network']['hostname']}}")
            text_output.append(f"IP Address: {{info['network']['ip_address']}}")
            
            text_output.append("-"*20 + " Network Interfaces " + "-"*20)
            for interface in info['network']['interfaces']:
                text_output.append(f"Interface: {{interface['name']}}")
                for addr in interface['addresses']:
                    text_output.append(f"  Family: {{addr['family']}}")
                    text_output.append(f"  Address: {{addr['address']}}")
                    if addr['netmask']:
                        text_output.append(f"  Netmask: {{addr['netmask']}}")
                    if addr['broadcast']:
                        text_output.append(f"  Broadcast: {{addr['broadcast']}}")
                    text_output.append("")
            
            text_output.append("-"*20 + " Network I/O " + "-"*20)
            text_output.append(f"Bytes Sent: {{info['network']['io']['bytes_sent']}}")
            text_output.append(f"Bytes Received: {{info['network']['io']['bytes_received']}}")
            text_output.append(f"Packets Sent: {{info['network']['io']['packets_sent']}}")
            text_output.append(f"Packets Received: {{info['network']['io']['packets_received']}}")
            text_output.append("")
        
        # Process Information
        if 'processes' in info:
            text_output.append("="*40 + " Process Information " + "="*40)
            process_data = []
            headers = ["PID", "Name", "User", "Memory Usage", "Memory %", "CPU %", "Status", "Created"]
            for proc in info['processes'][:20]:  # Show top 20 processes by memory usage
                process_data.append([
                    proc.get('pid', 'N/A'),
                    proc.get('name', 'N/A'),
                    proc.get('username', 'N/A'),
                    proc.get('memory_usage', 'N/A'),
                    f"{{proc.get('memory_percent', 0):.2f}}%",
                    f"{{proc.get('cpu_percent', 0):.2f}}%",
                    proc.get('status', 'N/A'),
                    proc.get('create_time', 'N/A')
                ])
            text_output.append(tabulate(process_data, headers=headers))
            text_output.append("")
        
        # Environment Variables
        if 'environment' in info:
            text_output.append("="*40 + " Environment Variables " + "="*40)
            env_data = []
            for key, value in info['environment'].items():
                env_data.append([key, value])
            text_output.append(tabulate(env_data, headers=["Variable", "Value"]))
            text_output.append("")
        
        return "\\n".join(text_output)

# Get system information
try:
    # Install psutil if not already installed
    try:
        import psutil
    except ImportError:
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "psutil", "tabulate"])
        import psutil
        from tabulate import tabulate
    
    # Get system information
    system_info = get_system_info()
    
    # Format output
    output = format_output(system_info, "{output_format}")
    
    # Print output
    print(output)
    
except Exception as e:
    print(f"Error: {{str(e)}}")
    sys.exit(1)
"""
        
        return script
    
    def success_response(self, message: str) -> ToolResult:
        """Create a success response."""
        return ToolResult(output=message)
    
    def fail_response(self, error: str) -> ToolResult:
        """Create a failure response."""
        return ToolResult(error=error)
