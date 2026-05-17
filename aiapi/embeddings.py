import functools

from flask import Blueprint, current_app, jsonify, request
from openai import OpenAI

from aiapi.config import AIAPIConfig

bp = Blueprint("embeddings", __name__)

EMBEDDING_MODEL = "text-embedding-3-small"


def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        secret = request.form.get("secret")
        if secret is None:
            return jsonify("Not Authorized"), 401
        return view(**kwargs)

    return wrapped_view


@bp.route("/embed", methods=["POST"])
@login_required
def embed():
    text = request.form.get("text", "").strip()
    if not text:
        return jsonify({"error": "text is required"}), 400

    client = OpenAI(api_key=current_app.config["AI_API_OPENAI"])
    response = client.embeddings.create(input=text, model=EMBEDDING_MODEL)
    current_app.logger.debug("embed: generated embedding for text of length %d", len(text))
    return jsonify({"embedding": response.data[0].embedding})
