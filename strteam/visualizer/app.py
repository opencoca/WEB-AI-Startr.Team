import logging
import requests
import os
from flask import Flask, send_from_directory, request, jsonify
import argparse

# TODO: Modernize this Flask application:
# 1. Use Flask application factory pattern
# 2. Implement proper error handling and logging
# 3. Consider using Flask Blueprints for better organization
# 4. Add proper request validation and error responses
# 5. Replace the simple HTTP request-based message passing with WebSockets

app = Flask(__name__, static_folder='static')
app.logger.setLevel(logging.ERROR)
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)
messages = []
port = [8000]

def send_msg(role, text):
    try:
        data = {"role": role, "text": text}
        response = requests.post(f"http://127.0.0.1:{port[-1]}/send_message", json=data)
    except:
        logging.info("flask app.py did not start for online log")
    # TODO: Improve error handling - catch specific exceptions and provide more informative error messages


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/chain_visualizer")
def chain_visualizer():
    return send_from_directory("static", "chain_visualizer.html")


@app.route("/replay")
def replay():
    return send_from_directory("static", "replay.html")


@app.route("/get_messages")
def get_messages():
    return jsonify(messages)


@app.route("/send_message", methods=["POST"])
def send_message():
    data = request.get_json()
    role = data.get("role")
    text = data.get("text")

    avatarUrl = find_avatar_url(role)

    message = {"role": role, "text": text, "avatarUrl": avatarUrl}
    messages.append(message)
    return jsonify(message)

# Define rout to send team a project
# to run a project we must call the startr.team module
# python -m startr.team [-h] [--config CONFIG] [--org ORG] [--task TASK] [--name NAME] [--model MODEL] [--path PATH]
import subprocess

@app.route("/send_project", methods=["POST"])
def send_project():
    data = request.get_json()
    cmd = ["python3", "-m", "startr.team"]
    
    for arg in ["task", "config", "org", "name", "model", "path"]:
        if data.get(arg):
            cmd.extend([f"--{arg}", data[arg]])
    
    try:
        subprocess.run(cmd, check=True)
        return jsonify({"status": "success"}), 200
    except subprocess.CalledProcessError as e:
        return jsonify({"status": "error", "message": str(e)}), 500


#Define the favicon route
@app.route('/favicon.ico')
def favicon():
    #Return the favicon found in static folder root
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')
def find_avatar_url(role):
    role = role.replace(" ", "%20")
    avatar_filename = f"avatars/{role}.png"
    avatar_url = f"/static/{avatar_filename}"
    return avatar_url

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='argparse')
    parser.add_argument('--port', type=int, default=8000, help="port")
    args = parser.parse_args()
    port.append(args.port)
    print(f"""
=====================================================================
🚀 Startr.Team Visualizer is running!

📊 Main Dashboard:       http://127.0.0.1:{port[-1]}/
📋 Project Chain View:   http://127.0.0.1:{port[-1]}/chain_visualizer
🔄 Log Replay Tool:      http://127.0.0.1:{port[-1]}/replay

💡 Tips:
- For Log Replay: Upload any log file from your WareHouse directory
- For project submission: Use the form on the main dashboard
- In case of port conflicts, use: python3 app.py --port <different_port>
=====================================================================
""")
    app.run(host='0.0.0.0', debug=False, port=port[-1])
