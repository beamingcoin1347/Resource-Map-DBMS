from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from pymongo import MongoClient
from bson.objectid import ObjectId
import os

app = Flask(__name__, static_folder="../frontend", static_url_path="/")
CORS(app)

MONGO_URI = "mongodb+srv://Shreyan_19:Shreyan19@communityresourcemap.nkvghvk.mongodb.net/?appName=CommunityResourceMap"
client = MongoClient(MONGO_URI)
try:
    client.admin.command("ping")
except Exception:
    # If DB not reachable, app still runs but DB operations will be unavailable
    client = None

db = client["community_map"] if client is not None else None
resources_col = db["resources"] if db is not None else None
reviews_col = db["reviews"] if db is not None else None
events_col = db["events"] if db is not None else None

def to_json(doc):
    if not doc:
        return None
    doc = dict(doc)
    doc["id"] = str(doc.pop("_id"))
    return doc

@app.route("/")
def serve_frontend():
    return send_from_directory(app.static_folder, "index.html")

@app.route("/api/resource", methods=["POST"])
def add_resource():
    data = request.json
    if not data or "name" not in data:
        return jsonify({"error": "Invalid data, 'name' required"}), 400
    resource = {
        "name": data.get("name"),
        "category": data.get("category"),
        "address": data.get("address"),
        "latitude": data.get("latitude"),
        "longitude": data.get("longitude"),
        "contact": data.get("contact"),
        "description": data.get("description")
    }
    if resources_col:
        res = resources_col.insert_one(resource)
        return jsonify({"message": "Resource added", "id": str(res.inserted_id)}), 201
    return jsonify({"message": "DB not available; simulated add"}), 201

@app.route("/api/resources", methods=["GET"])
def get_resources():
    category = request.args.get("category")
    query = {}
    if category:
        query["category"] = category
    if resources_col:
        docs = list(resources_col.find(query))
        return jsonify([to_json(d) for d in docs]), 200
    return jsonify([]), 200

@app.route("/api/resource/<rid>", methods=["GET"])
def get_resource(rid):
    try:
        doc = resources_col.find_one({"_id": ObjectId(rid)}) if resources_col else None
    except Exception:
        return jsonify({"error": "Invalid id"}), 400
    if not doc:
        return jsonify({"error": "Not found"}), 404
    return jsonify(to_json(doc)), 200

@app.route("/api/review", methods=["POST"])
def add_review():
    data = request.json
    if not data or "resource_id" not in data or "rating" not in data:
        return jsonify({"error": "Invalid data"}), 400
    review = {
        "resource_id": data.get("resource_id"),
        "user_name": data.get("user_name"),
        "rating": data.get("rating"),
        "comment": data.get("comment"),
        "date": data.get("date")
    }
    if reviews_col:
        res = reviews_col.insert_one(review)
        return jsonify({"message": "Review added", "id": str(res.inserted_id)}), 201
    return jsonify({"message": "DB not available; simulated add"}), 201

@app.route("/api/reviews/<resource_id>", methods=["GET"])
def get_reviews(resource_id):
    if reviews_col:
        docs = list(reviews_col.find({"resource_id": resource_id}))
        return jsonify([to_json(d) for d in docs]), 200
    return jsonify([]), 200

@app.route("/api/event", methods=["POST"])
def add_event():
    data = request.json
    if not data or "resource_id" not in data or "title" not in data:
        return jsonify({"error": "Invalid data"}), 400
    event = {
        "resource_id": data.get("resource_id"),
        "title": data.get("title"),
        "description": data.get("description"),
        "date": data.get("date"),
        "time": data.get("time")
    }
    if events_col:
        res = events_col.insert_one(event)
        return jsonify({"message": "Event added", "id": str(res.inserted_id)}), 201
    return jsonify({"message": "DB not available; simulated add"}), 201

@app.route("/api/events/<resource_id>", methods=["GET"])
def get_events(resource_id):
    if events_col:
        docs = list(events_col.find({"resource_id": resource_id}))
        return jsonify([to_json(d) for d in docs]), 200
    return jsonify([]), 200

@app.route("/api/resource/<rid>", methods=["DELETE"])
def delete_resource(rid):
    try:
        res = resources_col.delete_one({"_id": ObjectId(rid)}) if resources_col else None
    except Exception:
        return jsonify({"error": "Invalid id"}), 400
    if res and res.deleted_count:
        return jsonify({"message": "Resource deleted"}), 200
    return jsonify({"error": "Not found"}), 404

@app.route("/api/review/<rid>", methods=["DELETE"])
def delete_review(rid):
    try:
        res = reviews_col.delete_one({"_id": ObjectId(rid)}) if reviews_col else None
    except Exception:
        return jsonify({"error": "Invalid id"}), 400
    if res and res.deleted_count:
        return jsonify({"message": "Review deleted"}), 200
    return jsonify({"error": "Not found"}), 404

if __name__ == "__main__":
    app.run(debug=False, port=5000)
