# Windows Setup Guide for e-Gov Law MCP Server

## 🚨 Current Issue Analysis

Based on your logs, Claude Desktop is using the FastMCP command instead of our Windows-compatible `run_server.py`. The error shows:

```
ERROR Failed to run: No module named 'yaml'
```

This happens because the FastMCP isolated environment doesn't have access to your installed dependencies.

## ✅ Quick Fix Steps

### 1. Update Claude Desktop Configuration

**Location**: `%APPDATA%\Claude\claude_desktop_config.json`
**Full Path**: `C:\Users\ryoki\AppData\Roaming\Claude\claude_desktop_config.json`

**Replace your current configuration with**:
```json
{
  "mcpServers": {
    "e-gov-law": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "C:\\Users\\ryoki\\Claude\\mcp\\e-gov-law-mcp",
        "python",
        "run_server.py"
      ]
    }
  }
}
```

### 2. Install Dependencies in Your Project Directory

Open Command Prompt or PowerShell in `C:\Users\ryoki\Claude\mcp\e-gov-law-mcp` and run:

```cmd
# Method 1: Using uv (recommended)
uv sync

# Method 2: If uv sync fails, use pip directly
pip install fastmcp>=2.8.1 httpx>=0.24.0 PyYAML>=6.0

# Optional: For performance monitoring
pip install psutil
```

### 3. Verify run_server.py Exists

Make sure `run_server.py` exists in your project root. If not, pull the latest changes:

```cmd
cd C:\Users\ryoki\Claude\mcp\e-gov-law-mcp
git pull origin main
```

### 4. Test the Configuration

Before restarting Claude Desktop, test that the server works:

```cmd
cd C:\Users\ryoki\Claude\mcp\e-gov-law-mcp
uv run python run_server.py
```

You should see initialization messages without the "No module named 'yaml'" error.

## 🔧 Alternative Solutions

### Option A: Use Automated Install Script

1. Download and run `install_windows.bat` from the project root
2. It will automatically install dependencies and show you the correct configuration

### Option B: Manual pip installation

If uv is causing issues:

```cmd
cd C:\Users\ryoki\Claude\mcp\e-gov-law-mcp
pip install fastmcp httpx PyYAML psutil
```

Then use this simpler configuration:
```json
{
  "mcpServers": {
    "e-gov-law": {
      "command": "python",
      "args": [
        "C:\\Users\\ryoki\\Claude\\mcp\\e-gov-law-mcp\\run_server.py"
      ],
      "cwd": "C:\\Users\\ryoki\\Claude\\mcp\\e-gov-law-mcp"
    }
  }
}
```

## 🎯 Expected Success Log

After correct configuration, you should see:
```
[info] Server started and connected successfully
[info] Message from client: {"method":"initialize"...}
```

Without any "No module named" errors.