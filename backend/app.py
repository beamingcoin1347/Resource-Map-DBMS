# backend/app.py
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from pymongo import MongoClient
from bson.objectid import ObjectId
import os, json, time, uuid, logging, sys
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
app = Flask(__name__, static_folder="../frontend", static_url_path="/")
CORS(app)
logger = app.logger

# Connect to Mongo DB
MONGO_URI =  "mongodb+srv://Shreyan_19:Shreyan19@communityresourcemap.nkvghvk.mongodb.net/?appName=CommunityResourceMap"
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "Admin123")  # set in env for real use

# Error handling for mongo connection
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

#Storage
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)
LOCAL_RESOURCE_FILE = os.path.join(DATA_DIR, "resources.json")
LOCAL_REVIEW_FILE = os.path.join(DATA_DIR, "reviews.json")
LOCAL_EVENT_FILE = os.path.join(DATA_DIR, "events.json")

def load_local(path):
    try:
        if os.path.exists(path):
            return json.loads(open(path, "r", encoding="utf8").read())
    except Exception:
        logger.exception("load_local failed for %s", path)
    return []

def save_local(path, obj):
    try:
        open(path, "w", encoding="utf8").write(json.dumps(obj, ensure_ascii=False, indent=2))
        return True
    except Exception:
        logger.exception("save_local failed for %s", path)
        return False

local_resources = load_local(LOCAL_RESOURCE_FILE) if resources_col is None else None
local_reviews = load_local(LOCAL_REVIEW_FILE) if reviews_col is None else None
local_events = load_local(LOCAL_EVENT_FILE) if events_col is None else None

# --- Helpers ---
def normalize_resource_doc(doc):
    """Return resource dict with 'id' field and consistent keys for frontend."""
    if not doc:
        return None
    d = dict(doc)
    # handle pymongo ObjectId
    if "_id" in d:
        d["id"] = str(d.pop("_id"))
    # if local doc uses _id string, convert
    if "id" not in d and "_id" in d:
        d["id"] = str(d["_id"])
    # ensure avg_rating exists or None
    if "avg_rating" not in d:
        d["avg_rating"] = None
    return d

def normalize_review_doc(doc):
    if not doc:
        return None
    d = dict(doc)
    if "_id" in d:
        d["id"] = str(d.pop("_id"))
    return d

def normalize_event_doc(doc):
    if not doc:
        return None
    d = dict(doc)
    if "_id" in d:
        d["id"] = str(d.pop("_id"))
    return d

# --- Frontend serve ---
@app.route("/")
def serve_frontend():
    try:
        return send_from_directory(app.static_folder, "index.html")
    except Exception:
        return "Frontend not found", 404

# --- Resources: list (supports category filter & search) ---
@app.route("/api/resources", methods=["GET"])
def get_resources():
    try:
        category = request.args.get("category")
        q = request.args.get("q")
        if resources_col is not None:
            query = {}
            if category:
                query["category"] = category
            docs = list(resources_col.find(query))
            out = [normalize_resource_doc(d) for d in docs]
            if q:
                ql = q.lower()
                out = [r for r in out if ql in (r.get("name","") + r.get("address","")).lower()]
            return jsonify(out), 200
        else:
            out = list(local_resources or [])
            # local resources may have _id; ensure id exists
            for r in out:
                if "_id" in r and "id" not in r:
                    r["id"] = str(r["_id"])
            if category:
                out = [r for r in out if r.get("category")==category]
            if q:
                ql = q.lower()
                out = [r for r in out if ql in (r.get("name","") + r.get("address","")).lower()]
            return jsonify(out), 200
    except Exception:
        logger.exception("get_resources failed")
        return jsonify({"error":"server"}), 500

# --- Add resource ---
@app.route("/api/resource", methods=["POST"])
def add_resource():
    try:
        data = request.json
        if not data or "name" not in data:
            return jsonify({"error":"Invalid data"}), 400
        doc = {
            "name": data.get("name"),
            "category": data.get("category"),
            "address": data.get("address"),
            "latitude": data.get("latitude"),
            "longitude": data.get("longitude"),
            "contact": data.get("contact"),
            "description": data.get("description"),
            "verified": False,
            "avg_rating": None,
            "created_at": time.time()
        }
        if resources_col is not None:
            res = resources_col.insert_one(doc)
            return jsonify({"message":"Resource added", "id": str(res.inserted_id)}), 201
        else:
            # local fallback
            doc["_id"] = str(uuid.uuid4())
            doc["id"] = str(doc["_id"])
            local_resources.append(doc)
            save_local(LOCAL_RESOURCE_FILE, local_resources)
            return jsonify({"message":"Resource added (local)", "id": doc["id"]}), 201
    except Exception:
        logger.exception("add_resource failed")
        return jsonify({"error":"server"}), 500

# --- Get single resource ---
@app.route("/api/resource/<rid>", methods=["GET"])
def get_resource(rid):
    try:
        if resources_col is not None:
            try:
                doc = resources_col.find_one({"_id": ObjectId(rid)})
            except Exception:
                return jsonify({"error":"Invalid id"}), 400
            if not doc:
                return jsonify({"error":"Not found"}), 404
            return jsonify(normalize_resource_doc(doc)), 200
        else:
            for r in (local_resources or []):
                if r.get("id")==rid or r.get("_id")==rid:
                    # ensure id key
                    if "_id" in r and "id" not in r:
                        r["id"] = str(r["_id"])
                    return jsonify(r), 200
            return jsonify({"error":"Not found"}), 404
    except Exception:
        logger.exception("get_resource failed")
        return jsonify({"error":"server"}), 500

# --- Reviews: add and list ---
@app.route("/api/resource/<rid>/reviews", methods=["GET"])
def get_reviews_for_resource(rid):
    try:
        if reviews_col is not None:
            docs = list(reviews_col.find({"resource_id": rid}))
            return jsonify([normalize_review_doc(d) for d in docs]), 200
        else:
            out = [r for r in (local_reviews or []) if r.get("resource_id")==rid]
            for r in out:
                if "_id" in r and "id" not in r:
                    r["id"] = str(r["_id"])
            return jsonify(out), 200
    except Exception:
        logger.exception("get_reviews_for_resource failed")
        return jsonify({"error":"server"}), 500

@app.route("/api/resource/<rid>/review", methods=["POST"])
def add_review_to_resource(rid):
    try:
        data = request.json
        if not data or "rating" not in data:
            return jsonify({"error":"Invalid data"}), 400
        review = {
            "resource_id": rid,
            "user_name": data.get("user_name"),
            "rating": float(data.get("rating")),
            "comment": data.get("comment"),
            "created_at": time.time()
        }
        if reviews_col is not None:
            res = reviews_col.insert_one(review)
        else:
            review["_id"] = str(uuid.uuid4())
            review["id"] = review["_id"]
            local_reviews.append(review)
            save_local(LOCAL_REVIEW_FILE, local_reviews)
        # update avg rating
        try:
            if reviews_col is not None and resources_col is not None:
                docs = list(reviews_col.find({"resource_id": rid}))
                if docs:
                    avg = sum([d.get("rating",0) for d in docs]) / len(docs)
                else:
                    avg = None
                resources_col.update_one({"_id": ObjectId(rid)}, {"$set": {"avg_rating": avg}})
            else:
                rs = [r for r in (local_reviews or []) if r.get("resource_id")==rid]
                avg = (sum(r.get("rating",0) for r in rs) / len(rs)) if rs else None
                for resrc in (local_resources or []):
                    if resrc.get("id")==rid or resrc.get("_id")==rid:
                        resrc["avg_rating"] = avg
                save_local(LOCAL_RESOURCE_FILE, local_resources)
        except Exception:
            logger.exception("Failed updating average rating")
        return jsonify({"message":"Review added"}), 201
    except Exception:
        logger.exception("add_review_to_resource failed")
        return jsonify({"error":"server"}), 500

# --- Events: list for a resource, add an event, list upcoming events ---
@app.route("/api/resource/<rid>/events", methods=["GET"])
def get_events_for_resource(rid):
    try:
        if events_col is not None:
            docs = list(events_col.find({"resource_id": rid}))
            return jsonify([normalize_event_doc(d) for d in docs]), 200
        else:
            out = [e for e in (local_events or []) if e.get("resource_id")==rid]
            for e in out:
                if "_id" in e and "id" not in e:
                    e["id"] = str(e["_id"])
            return jsonify(out), 200
    except Exception:
        logger.exception("get_events_for_resource failed")
        return jsonify({"error":"server"}), 500

@app.route("/api/resource/<rid>/event", methods=["POST"])
def add_event_to_resource(rid):
    try:
        data = request.json
        if not data or "title" not in data or "date" not in data:
            return jsonify({"error":"Invalid data, require title and date"}), 400
        ev = {
            "resource_id": rid,
            "title": data.get("title"),
            "description": data.get("description"),
            "date": data.get("date"),
            "time": data.get("time"),
            "created_at": time.time()
        }
        if events_col is not None:
            res = events_col.insert_one(ev)
            return jsonify({"message":"Event added", "id": str(res.inserted_id)}), 201
        else:
            ev["_id"] = str(uuid.uuid4())
            ev["id"] = ev["_id"]
            local_events.append(ev)
            save_local(LOCAL_EVENT_FILE, local_events)
            return jsonify({"message":"Event added (local)", "id": ev["id"]}), 201
    except Exception:
        logger.exception("add_event_to_resource failed")
        return jsonify({"error":"server"}), 500

@app.route("/api/events", methods=["GET"])
def get_upcoming_events():
    try:
        days = int(request.args.get("days", 30))
        cutoff = (datetime.utcnow() + timedelta(days=days)).date().isoformat()
        if events_col is not None:
            docs = list(events_col.find({"date": {"$lte": cutoff}}))
            return jsonify([normalize_event_doc(d) for d in docs]), 200
        else:
            out = [e for e in (local_events or []) if e.get("date") <= cutoff]
            for e in out:
                if "_id" in e and "id" not in e:
                    e["id"] = str(e["_id"])
            return jsonify(out), 200
    except Exception:
        logger.exception("get_upcoming_events failed")
        return jsonify({"error":"server"}), 500

# --- Verify resource (admin-only) ---
@app.route("/api/resource/<rid>/verify", methods=["POST"])
def verify_resource(rid):
    try:
        token = request.headers.get("X-ADMIN-TOKEN", "")
        if token != ADMIN_TOKEN:
            return jsonify({"error":"unauthorized"}), 401
        if resources_col is not None:
            resources_col.update_one({"_id": ObjectId(rid)}, {"$set": {"verified": True}})
            return jsonify({"message":"Resource verified"}), 200
        else:
            # local
            for r in (local_resources or []):
                if r.get("id")==rid or r.get("_id")==rid:
                    r["verified"] = True
            save_local(LOCAL_RESOURCE_FILE, local_resources)
            return jsonify({"message":"Resource verified (local)"}), 200
    except Exception:
        logger.exception("verify_resource failed")
        return jsonify({"error":"server"}), 500

# --- Delete endpoints (optional) ---
@app.route("/api/resource/<rid>", methods=["DELETE"])
def delete_resource(rid):
    try:
        if resources_col is not None:
            try:
                res = resources_col.delete_one({"_id": ObjectId(rid)})
            except Exception:
                return jsonify({"error":"Invalid id"}), 400
            if res.deleted_count:
                return jsonify({"message":"Deleted"}), 200
            return jsonify({"error":"Not found"}), 404
        else:
            local_resources[:] = [r for r in (local_resources or []) if not (r.get("id")==rid or r.get("_id")==rid)]
            save_local(LOCAL_RESOURCE_FILE, local_resources)
            return jsonify({"message":"Deleted (local)"}), 200
    except Exception:
        logger.exception("delete_resource failed")
        return jsonify({"error":"server"}), 500

if __name__ == "__main__":
    try:
        app.run(debug=False, use_reloader=False, port=5000)
    except Exception:
        logger.exception("app.run raised exception")
        sys.exit(1)
