# Debugging Guide for WEB-AI-Startr.Team

This guide provides comprehensive instructions for debugging the WEB-AI-Startr.Team system, focusing on model validation, interactive debugging, and runtime inspection.

## Quick Start

### 1. Setup

Run the debug setup command to prepare the environment:

```bash
make debug-setup
```

### 2. Validate Model Configuration

Check if your model configuration is valid:

```bash
make debug-model MODEL=LLAMA_3
```

### 3. Run with Debugging Enabled

Run the system with full debugging capabilities:

```bash
make debug-run
```

## Common Issues and Solutions

### Model Not Found Error

If you encounter a "model not found" error (like the `llama-3.3-70b-versatile` error in the traceback), here are the steps to resolve it:

1. **Verify your model configuration:**

```bash
make debug-model MODEL=LLAMA_3
```

2. **Use a fallback model:**

The system now has automatic fallback to GPT-4 for unsupported models, but you can explicitly use GPT-4:

```bash
make debug-fallback
```

3. **Check API connectivity:**

Verify that your API key works and can access models:

```bash
make debug-api-test
```

### Installation or Import Errors

If you encounter import errors or missing dependencies:

1. Ensure all dependencies are installed:

```bash
pipenv install
```

2. Run with verbose error reporting:

```bash
./debug_run.py --log-level debug --model-debug
```

## Advanced Debugging

### Interactive Debugging

To pause execution at specific points:

```bash
./debug_run.py --interactive --breakpoints "OpenAIModel.run,ChatChain.execute_chain"
```

When a breakpoint is hit, you'll enter Python's PDB debugger. Common commands:
- `c` - Continue execution
- `n` - Execute next line (step over)
- `s` - Step into function call
- `p expression` - Print value of expression
- `l` - List source code
- `q` - Quit debugger

### Debugging API Calls

To trace API calls and inspect responses:

```bash
VERBOSE_MODEL_DEBUG=true ./debug_run.py
```

### Inspecting Debug Output

Debug logs are saved to:
- `debug_[timestamp].log` - Full debug log
- `debug_state_*.json` - State snapshots during execution

## Customizing Debug Points

The debugging system defines inspection points throughout the codebase:

### Model Validation

- `model_config` - Inspects model configuration
- `model_verification_result` - Results of model validation
- `openai_run_call` - Details of API calls to OpenAI
- `openai_model_access_response_{model_name}` - API responses when testing model access

### Execution Flow

- `OpenAIModel.__init__` - Model initialization 
- `OpenAIModel.run` - API call execution
- `ChatChain.execute_chain` - Main execution flow
- `Phase.execute` - Individual phase execution

## Using with iPython

For more interactive debugging, you can use iPython:

```bash
ipython -c "import os; os.environ['STARTR_DEBUG'] = 'true'; os.environ['STARTR_INTERACTIVE'] = 'true'; os.environ['VERBOSE_MODEL_DEBUG'] = 'true'; import debug_run; debug_run.main()"
```

## Tips for Effective Debugging

1. **Start with model verification:**
   Always check model compatibility first as this is a common source of errors.

2. **Use targeted breakpoints:**
   Set specific breakpoints rather than enabling interactive mode for everything.

3. **Monitor debug.log:**
   Keep a terminal window open with `tail -f debug_*.log` to watch log output.

4. **Check debug state files:**
   Review the JSON state files to understand system state at different execution points.

5. **Try fallback models:**
   If encountering model issues, test with a known working model like GPT-3.5-turbo.

## Troubleshooting the Debugger

If the debugging tools themselves don't work:

1. **Check Python version:**
   Ensure you're using Python 3.8+ with `python --version`.

2. **Verify debugging module imports:**
   Make sure the debug utilities are importable with `python -c "from chatdev.debug_utils import debug_log; print('Success')"`.

3. **Ensure file permissions:**
   Run `chmod +x debug_run.py` to make the debug script executable.

4. **Check for error logs:**
   Look for any error messages in `debug_*.log` files.

## Future Improvements

The debugging system is designed to be extended. Suggested improvements:

1. Add WebUI for visual debugging
2. Implement breakpoint configuration via JSON file
3. Add network traffic monitoring for API calls
4. Improve model compatibility verification
5. Add memory profiling for large projects 