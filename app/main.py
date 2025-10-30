from flask import Flask, jsonify

app = Flask(__name__)

@app.route("/")
def hello():
    return jsonify({"message": "Hello from Checkpoint 1 Sample App!"})

@app.route("/metrics")
def metrics():
    # Simple metrics example
    return "app_requests_total 42\n", 200, {"Content-Type": "text/plain; version=0.0.4"}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
