# SAM Local Debug in WSL

This guide explains how to set up local debugging for AWS SAM Lambda functions in WSL.

## Prerequisites

- WSL (Windows Subsystem for Linux) installed
- VS Code with WSL Remote extension
- AWS SAM CLI installed
- Docker installed and running

## Setup Instructions

### 1. Install WSL Remote Extension

Install the WSL Remote extension in VS Code to enable remote development in WSL.

### 2. Create Launch Configuration

In the root of your project directory, create `.vscode` folder and include the configuration below in a file named `launch.json`.

**Important**: When you mount your WSL workspace, you must choose your project root folder as the root of your workspace so the `workspaceFolder` environment variable works across VS Code.

### 3. Launch Configuration

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "type": "aws-sam",
            "request": "direct-invoke",
            "name": "[DISPLAY NAME]",
            "invokeTarget": {
                "target": "template",
                "templatePath": "${workspaceFolder}/[path to template]/template.yaml",
                "logicalId": "[FUNCTION NAME IN YAML TEMPLATE]"
            },
            "lambda": {
                "runtime": "python3.12",
                "payload": {},
                "environmentVariables": {
                    "PATH": "/home/wsluser/.local/bin:/usr/local/bin:/usr/bin:${env:PATH}",
                    "PYTHONPATH": "${workspaceFolder}",
                    "PYTHONARGS": "-Xfrozen_modules=off"
                }                
            },
            "sam": {
                "containerBuild": true,
                "dockerNetwork": "bridge"
            },
            "aws": {
                "credentials": "profile:default",
                "region": "us-west-2"
            }            
        }        
    ]
}
```

## Configuration Parameters

### Display Name
Replace `[DISPLAY NAME]` with a descriptive name for your debug configuration (e.g., "Debug MakeCallStreamFunction").

### Template Path
Replace `[path to template]` with the relative path to your SAM template from the workspace root (e.g., `backend/calledit-backend`).

### Logical ID
Replace `[FUNCTION NAME IN YAML TEMPLATE]` with the exact function name as it appears in your `template.yaml` (e.g., `MakeCallStreamFunction`).

## Environment Variables

### PATH
Ensures Python and other tools are available in the Lambda execution environment.

### PYTHONPATH
Set to `${workspaceFolder}` to allow imports from your project root.

### PYTHONARGS
`-Xfrozen_modules=off` disables frozen modules for better debugging experience.

## SAM Configuration

### containerBuild
Set to `true` to build Lambda functions inside Docker containers, ensuring consistency with AWS Lambda environment.

### dockerNetwork
Set to `bridge` to use Docker's default bridge network.

## AWS Configuration

### credentials
Uses the `default` AWS profile from your `~/.aws/credentials` file.

### region
Set to your AWS region (e.g., `us-west-2`).

## Usage

1. Open your project in VS Code using WSL Remote
2. Set breakpoints in your Lambda function code
3. Press F5 or use the Debug panel to start debugging
4. The function will execute locally in a Docker container
5. Execution will pause at your breakpoints

## Troubleshooting

### Docker Not Running
Ensure Docker Desktop is running before attempting to debug.

### Permission Issues
If you encounter permission issues, ensure your WSL user has Docker permissions:
```bash
sudo usermod -aG docker $USER
```

### Path Issues
Verify that `workspaceFolder` is set correctly by checking VS Code's workspace settings.

### Python Import Errors
Ensure `PYTHONPATH` includes your project root and all necessary dependencies are installed.

## Example Configuration for CalledIt

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "type": "aws-sam",
            "request": "direct-invoke",
            "name": "Debug MakeCallStreamFunction",
            "invokeTarget": {
                "target": "template",
                "templatePath": "${workspaceFolder}/backend/calledit-backend/template.yaml",
                "logicalId": "MakeCallStreamFunction"
            },
            "lambda": {
                "runtime": "python3.12",
                "payload": {},
                "environmentVariables": {
                    "PATH": "/home/wsluser/.local/bin:/usr/local/bin:/usr/bin:${env:PATH}",
                    "PYTHONPATH": "${workspaceFolder}",
                    "PYTHONARGS": "-Xfrozen_modules=off"
                }                
            },
            "sam": {
                "containerBuild": true,
                "dockerNetwork": "bridge"
            },
            "aws": {
                "credentials": "profile:default",
                "region": "us-west-2"
            }            
        }        
    ]
}
```

## Additional Resources

- [AWS SAM CLI Documentation](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html)
- [VS Code WSL Documentation](https://code.visualstudio.com/docs/remote/wsl)
- [Docker Documentation](https://docs.docker.com/)
