import os
import uuid
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError
from flask import Flask, jsonify, request

DYNAMODB_TABLE_NAME = os.environ.get("DYNAMODB_TABLE_NAME")
if not DYNAMODB_TABLE_NAME:
    raise RuntimeError("DYNAMODB_TABLE_NAME environment variable is required")

region = os.environ.get("AWS_DEFAULT_REGION", "ap-northeast-1")
dynamodb = boto3.resource("dynamodb", region_name=region)
table = dynamodb.Table(DYNAMODB_TABLE_NAME)

app = Flask(__name__)


@app.route("/", methods=["GET"])
def health_check():
    return jsonify({"status": "ok"}), 200


@app.route("/items", methods=["GET"])
def get_items():
    try:
        response = table.scan()
        items = response.get("Items", [])
        return jsonify(items), 200
    except ClientError:
        return jsonify({"error": "Internal server error"}), 500


@app.route("/items", methods=["POST"])
def create_item():
    body = request.get_json(silent=True)
    if not body or not isinstance(body, dict):
        return jsonify({"error": "Invalid request body"}), 400

    name = body.get("name")
    if not name or not isinstance(name, str) or not name.strip():
        return jsonify({"error": "Invalid request body"}), 400

    item_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()

    item = {
        "id": item_id,
        "name": name,
        "created_at": created_at,
    }

    try:
        table.put_item(Item=item)
    except ClientError:
        return jsonify({"error": "Internal server error"}), 500

    return jsonify(item), 201


@app.route("/items/<item_id>", methods=["GET"])
def get_item(item_id):
    try:
        response = table.get_item(Key={"id": item_id})
    except ClientError:
        return jsonify({"error": "Internal server error"}), 500

    item = response.get("Item")
    if not item:
        return jsonify({"error": "Item not found"}), 404

    return jsonify(item), 200
