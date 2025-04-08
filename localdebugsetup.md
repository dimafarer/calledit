# VS Code debugger configuration

+ Ah, this is a specific issue with the VS Code debugger configuration. Since the debugger is running in a different context than your terminal, it needs explicit configuration to find Python and pip. Here's how to fix it:
+ First, modify your launch.json to include the correct Python path and environment variables:

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "type": "aws-sam",
            "request": "direct-invoke",
            "name": "HelloWorldFunction",
            "invokeTarget": {
                "target": "template",
                "templatePath": "${workspaceFolder}/backend/calledit-backend/template.yaml",
                "logicalId": "HelloWorldFunction"
            },
            "lambda": {
                "runtime": "python3.12",
                "payload": {},
                "environmentVariables": {}
            },
            "sam": {
                "containerBuild": true,
                "dockerNetwork": "bridge"
            },
            "env": {
                "PATH": "/home/wsluser/.local/bin:/usr/local/bin:/usr/bin:${env:PATH}"
            }
        },
        {
            "type": "aws-sam",
            "request": "direct-invoke",
            "name": "PromptBedrockFunction",
            "invokeTarget": {
                "target": "template",
                "templatePath": "${workspaceFolder}/backend/calledit-backend/template.yaml",
                "logicalId": "PromptBedrockFunction"
            },
            "lambda": {
                "runtime": "python3.12",
                "payload": {},
                "environmentVariables": {}
            },
            "sam": {
                "containerBuild": true,
                "dockerNetwork": "bridge"
            },
            "env": {
                "PATH": "/home/wsluser/.local/bin:/usr/local/bin:/usr/bin:${env:PATH}"
            }
        }        
    ]
}
```

+ Make sure you're using the Remote - WSL extension and have opened your folder through WSL.
+ Create a virtual environment specifically for debugging (if you haven't already):

```bash
cd /home/wsluser/projects/calledit/backend/calledit-backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

+ Add a samconfig.toml file in your project root if you don't have one:

```toml
version = 0.1
[default]
[default.build]
[default.build.parameters]
use_container = true
parallel = true

[default.local_invoke]
[default.local_invoke.parameters]
env_vars = "env.json"
```

+ Create an env.json file for local testing:

```json
{
    "Parameters": {
        "PYTHONPATH": "/home/wsluser/projects/calledit/backend/calledit-backend"
    }
}
```

In VS Code, ensure you:

+ Have the Python extension installed
+ Have selected the correct Python interpreter (Ctrl+Shift+P -> "Python: Select Interpreter" -> choose the one from your .venv)
+ Are running VS Code with the WSL extension
+ Try adding these debug configurations as well:

```json
{
    "version": "0.2.0",
    "configurations": [
        // ... your existing config ...
        {
            "name": "Python: Remote Attach",
            "type": "python",
            "request": "attach",
            "connect": {
                "host": "localhost",
                "port": 5890
            },
            "pathMappings": [
                {
                    "localRoot": "${workspaceFolder}",
                    "remoteRoot": "/var/task"
                }
            ],
            "justMyCode": true
        }
    ]
}
```

To debug:

+ Set breakpoints in your code
+ Select the "API HelloWorldFunction" configuration from the Run and Debug panel
+ Start debugging (F5)
+ If you're still having issues, you can try:
```bash
# Make sure pip is installed for Python 3.12
python3.12 -m ensurepip --upgrade

# Install pip in user space
python3.12 -m pip install --user --upgrade pip

# Verify the pip location
which pip
```

+ Then update your launch.json with the specific pip path shown by the which pip command.