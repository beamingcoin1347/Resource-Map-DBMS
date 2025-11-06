# debug app.py - temporary verbose server to diagnose startup problems
import faulthandler, traceback, sys, os, time
faulthandler.enable()
print("DEBUG: starting app.py", flush=True)

try:
    print("DEBUG: importing flask and pymongo...", flush=True)
    from flask import Flask, request, jsonify, send_from_directory
    from flask_cors import CORS
    from pymongo import MongoClient
    from bson.objectid import ObjectId
    print("DEBUG: imports successful", flush=True)
except Exception as e:
    print("ERROR: import failed:", e, flush=True)
    traceback.print_exc()
    sys.exit(1)

# minimal configuration
app = Flask(__name__, static_folder="../frontend", static_url_path="/")
CORS(app)

# use env var if present, else local
MONGO_URI = "mongodb+srv://Shreyan_19:Shreyan19@communityresourcemap.nkvghvk.mongodb.net/?appName=CommunityResourceMap"
print("DEBUG: MONGO_URI preview:", ("<atlas>" if "mongodb+srv" in MONGO_URI else MONGO_URI), flush=True)

# try connect to mongo briefly
try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    client.admin.command("ping")
    print("DEBUG: MongoDB ping OK", flush=True)
except Exception as e:
    print("ERROR: MongoDB connection failed:", e, flush=True)
    traceback.print_exc()
    # do not exit yet — continue so we can still start Flask for diagnosis
    client = None

# safe DB handles (even if client is None)
db = client["community_map"] if client is not None else None
resources_col = db["resources"] if db is not None else None
reviews_col = db["reviews"] if db is not None else None
events_col = db["events"] if db is not None else None

def to_json(doc):
    if not doc:
        return None
    d = dict(doc)
    d["id"] = str(d.pop("_id"))
    return d

@app.route("/")
def serve_frontend():
    try:
        return send_from_directory(app.static_folder, "index.html")
    except Exception as e:
        print("ERROR serving frontend:", e, flush=True)
        return "Frontend not found", 500

@app.route("/api/resources", methods=["GET"])
def get_resources():
    try:
        if resources_col:
            docs = list(resources_col.find({}))
            return jsonify([to_json(d) for d in docs]), 200
        else:
            return jsonify([]), 200
    except Exception as e:
        print("ERROR get_resources:", e, flush=True)
        traceback.print_exc()
        return jsonify({"error": "server"}), 500

@app.route("/api/resource", methods=["POST"])
def add_resource():
    try:
        data = request.json
        if not data or "name" not in data:
            return jsonify({"error": "Invalid data"}), 400
        doc = {
            "name": data.get("name"),
            "category": data.get("category"),
            "address": data.get("address"),
            "latitude": data.get("latitude"),
            "longitude": data.get("longitude"),
            "contact": data.get("contact"),
            "description": data.get("description")
        }
        if resources_col:
            res = resources_col.insert_one(doc)
            return jsonify({"message": "Resource added", "id": str(res.inserted_id)}), 201
        else:
            print("WARNING: resources_col not available; simulating insert", flush=True)
            return jsonify({"message": "Simulated add (no DB)"}), 201
    except Exception as e:
        print("ERROR add_resource:", e, flush=True)
        traceback.print_exc()
        return jsonify({"error": "server"}), 500

# minimal run block - prints and runs server
if __name__ == "__main__":
    try:
        print("DEBUG: entering __main__", flush=True)
        app.run(debug=True, use_reloader=False, port=5000)
    except Exception as e:
        print("FATAL: app.run raised exception:", e, flush=True)
        traceback.print_exc()
        sys.exit(1)
