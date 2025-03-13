"""
Main entry point for the visualizer when run as a module.

This file allows running the visualizer with:
python -m strteam.visualizer [--port PORT]
"""

import argparse
from .app import app, port

def main():
    """
    Run the visualizer application with command line arguments.
    """
    parser = argparse.ArgumentParser(description='strteam Visualizer')
    parser.add_argument('--port', type=int, default=8000, help="HTTP port to serve the visualizer")
    args = parser.parse_args()
    port.append(args.port)
    
    print(f"""
=====================================================================
🚀 strteam Visualizer is running!

📊 Main Dashboard:       http://127.0.0.1:{port[-1]}/
📋 Project Chain View:   http://127.0.0.1:{port[-1]}/chain_visualizer
🔄 Log Replay Tool:      http://127.0.0.1:{port[-1]}/replay

💡 Tips:
- For Log Replay: Upload any log file from your WareHouse directory
- For project submission: Use the form on the main dashboard
- In case of port conflicts, use: python -m strteam.visualizer --port <different_port>
=====================================================================
""")
    app.run(host='0.0.0.0', debug=False, port=port[-1])

if __name__ == "__main__":
    main()