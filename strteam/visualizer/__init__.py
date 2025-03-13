"""
strteam Visualizer

This package provides a web-based visualization interface for strteam projects.

Features:
- Main Dashboard for project submission and overview
- Chain Visualizer for viewing project execution chains
- Log Replay Tool for reviewing project logs
- Real-time message display and interaction

The visualizer acts as a frontend for the strteam framework, allowing users to
submit projects, monitor execution, and review results through an intuitive web interface.

Usage:
    To run the visualizer directly:
    ```
    python -m strteam.visualizer.app [--port PORT]
    ```

    Or through the module:
    ```
    python -m strteam.visualizer [--port PORT]
    ```

Configuration:
    PORT: The HTTP port to serve the visualizer (default: 8000)
"""

__version__ = "1.0.0"

# Import main components for easier access
from flask import Flask

def create_app(test_config=None):
    """
    Application factory function to create and configure the Flask app.
    
    Args:
        test_config (dict, optional): Configuration for testing. Defaults to None.
        
    Returns:
        Flask: Configured Flask application instance
    """
    from .app import app
    return app