@echo off
echo Installing e-Gov Law MCP Server dependencies for Windows...
echo.

:: Check if we're in the right directory
if not exist "pyproject.toml" (
    echo Error: pyproject.toml not found. Please run this script from the e-gov-law-mcp directory.
    pause
    exit /b 1
)

:: Install dependencies with uv
echo Installing dependencies with uv...
uv sync

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo uv sync failed. Trying alternative installation method...
    echo Installing dependencies with pip...
    pip install fastmcp>=2.8.1 httpx>=0.24.0 PyYAML>=6.0
    
    if %ERRORLEVEL% NEQ 0 (
        echo.
        echo Both uv and pip installation failed. Please install manually:
        echo   pip install fastmcp httpx PyYAML
        pause
        exit /b 1
    )
)

:: Optional: Install performance monitoring
echo.
set /p install_psutil="Install psutil for performance monitoring? (y/n): "
if /i "%install_psutil%"=="y" (
    echo Installing psutil...
    uv add psutil
    if %ERRORLEVEL% NEQ 0 (
        pip install psutil
    )
)

echo.
echo Installation completed successfully!
echo.
echo Next steps:
echo 1. Update your Claude Desktop configuration file:
echo    %APPDATA%\Claude\claude_desktop_config.json
echo.
echo 2. Use this configuration:
type claude_desktop_config_windows.json
echo.
echo 3. Restart Claude Desktop
echo.
pause