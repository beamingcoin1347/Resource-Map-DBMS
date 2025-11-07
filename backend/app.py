from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from pymongo import MongoClient
from bson.objectid import ObjectId
import os
import logging
import traceback
import sys

logging.basicConfig(level=logging.INFO)

app = Flask(__name__, static_folder="../frontend", static_url_path="/")
CORS(app)

# Load Mongo URI from environment (fallback local)
MONGO_URI = "mongodb+srv://Shreyan_19:Shreyan19@communityresourcemap.nkvghvk.mongodb.net/?appName=CommunityResourceMap"
logger = app.logger

# Connect to Mongo (attempt, but continue if fails)
client = None
try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    client.admin.command("ping")
    logger.info("MongoDB ping OK")
except Exception as e:
    logger.warning("MongoDB connection failed: %s", e)
    client = None

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
    except Exception:
        return "Frontend not found", 404

@app.route("/api/resources", methods=["GET"])
def get_resources():
    try:
        if resources_col is not None:
            docs = list(resources_col.find({}))
            return jsonify([to_json(d) for d in docs]), 200
        return jsonify([]), 200
    except Exception:
        logger.exception("get_resources failed")
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
        if resources_col is not None:
            res = resources_col.insert_one(doc)
            return jsonify({"message": "Resource added", "id": str(res.inserted_id)}), 201
        logger.warning("resources_col not available; simulated insert")
        return jsonify({"message": "Simulated add (no DB)"}), 201
    except Exception:
        logger.exception("add_resource failed")
        return jsonify({"error": "server"}), 500

@app.route("/api/resource/<rid>", methods=["GET"])
def get_resource(rid):
    try:
        doc = None
        if resources_col is not None:
            try:
                doc = resources_col.find_one({"_id": ObjectId(rid)})
            except Exception:
                return jsonify({"error": "Invalid id"}), 400
        if not doc:
            return jsonify({"error": "Not found"}), 404
        return jsonify(to_json(doc)), 200
    except Exception:
        logger.exception("get_resource failed")
        return jsonify({"error": "server"}), 500

@app.route("/api/review", methods=["POST"])
def add_review():
    try:
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
        if reviews_col is not None:
            res = reviews_col.insert_one(review)
            return jsonify({"message": "Review added", "id": str(res.inserted_id)}), 201
        return jsonify({"message": "DB not available; simulated add"}), 201
    except Exception:
        logger.exception("add_review failed")
        return jsonify({"error": "server"}), 500

@app.route("/api/reviews/<resource_id>", methods=["GET"])
def get_reviews(resource_id):
    try:
        if reviews_col is not None:
            docs = list(reviews_col.find({"resource_id": resource_id}))
            return jsonify([to_json(d) for d in docs]), 200
        return jsonify([]), 200
    except Exception:
        logger.exception("get_reviews failed")
        return jsonify({"error": "server"}), 500

@app.route("/api/event", methods=["POST"])
def add_event():
    try:
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
        if events_col is not None:
            res = events_col.insert_one(event)
            return jsonify({"message": "Event added", "id": str(res.inserted_id)}), 201
        return jsonify({"message": "DB not available; simulated add"}), 201
    except Exception:
        logger.exception("add_event failed")
        return jsonify({"error": "server"}), 500

@app.route("/api/events/<resource_id>", methods=["GET"])
def get_events(resource_id):
    try:
        if events_col is not None:
            docs = list(events_col.find({"resource_id": resource_id}))
            return jsonify([to_json(d) for d in docs]), 200
        return jsonify([]), 200
    except Exception:
        logger.exception("get_events failed")
        return jsonify({"error": "server"}), 500

@app.route("/api/resource/<rid>", methods=["DELETE"])
def delete_resource(rid):
    try:
        res = None
        if resources_col is not None:
            try:
                res = resources_col.delete_one({"_id": ObjectId(rid)})
            except Exception:
                return jsonify({"error": "Invalid id"}), 400
        if res and res.deleted_count:
            return jsonify({"message": "Resource deleted"}), 200
        return jsonify({"error": "Not found"}), 404
    except Exception:
        logger.exception("delete_resource failed")
        return jsonify({"error": "server"}), 500

@app.route("/api/review/<rid>", methods=["DELETE"])
def delete_review(rid):
    try:
        res = None
        if reviews_col is not None:
            try:
                res = reviews_col.delete_one({"_id": ObjectId(rid)})
            except Exception:
                return jsonify({"error": "Invalid id"}), 400
        if res and res.deleted_count:
            return jsonify({"message": "Review deleted"}), 200
        return jsonify({"error": "Not found"}), 404
    except Exception:
        logger.exception("delete_review failed")
        return jsonify({"error": "server"}), 500

if __name__ == "__main__":
    try:
        app.run(debug=False, use_reloader=False, port=5000)
    except Exception:
        logger.exception("app.run raised exception")
        sys.exit(1)
