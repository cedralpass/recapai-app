from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for,jsonify, current_app, logging
)
from werkzeug.exceptions import abort
import functools
import json
from openai import OpenAI
from aiapi.config import AIAPIConfig

bp = Blueprint('classify', __name__)

def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        key = extract_from_request('secret')
        if key is None:
            return jsonify("Not Authorized"), 401
        return view(**kwargs)

    return wrapped_view

@bp.route('/classify_url',methods=('GET', 'POST'))
@login_required
def classify_url():
    url = None
    ref_key = None
    url = extract_from_request('url')
    ref_key = extract_from_request('ref_key')
    
    json_return={}

    #create OpenAI request
    client = OpenAI(api_key=current_app.config["AI_API_OPENAI"])
    
    #make OpenAI Call
    response = client.chat.completions.create(
        model=AIAPIConfig.AI_OPEN_AI_MODEL,
        messages=build_prompt(url),
            response_format={ "type": "json_object" },
            temperature=0.9,
            max_tokens=512,
            frequency_penalty=0,
            presence_penalty=0
            )
    
    if len(response.choices)>=1:
        current_app.logger.info("classify: recieved response with >=1 choice from OpenAI")
        current_app.logger.debug(response.choices[0].message.content)
        json_return = response.choices[0].message.content
        current_app.logger.info("model %s cost %s", response.model, response.usage)
    else:
        current_app.logger.error("error: with openAPI call. no choices returned %s", response)

    response_json = json.loads(json_return)
    if ref_key is not None:
        response_json['ref_key']=ref_key
        current_app.logger.debug("classify: added ref_key to response: " + ref_key)
    else:
        current_app.logger.error("error: missing ref_key")
    
    current_app.logger.debug("classify: full response " + str(response_json))
    return jsonify(response_json)

def extract_from_request(key):
    value=None
    current_app.logger.debug("classify: request form keys: " + str(request.form.keys()))
    value = request.form.get(key)
    if value is None:
        current_app.logger.error("error: must supply url and secret for url for classification.  Supply a ref_key for refeference to an object.")
        current_app.logger.debug("extract_from_request: value to missing for %s with value", key)
    return value

def build_prompt(url):
    classify_content  = "please classify  this blog post: " + str(url)
    prompt_string =  [
            {
                "role": "system",
                "content": "Using these content categories as examples: Software Architecture, Leadership, Business Strategy, and Artificial Intelligence.  If the content does not fit a category, recommend a new category. Please respond with category, url of blog, blog title, author, summarize the content into a short paragraph, extract three key topics as bullet points, and extract three sub categories as bullet points. respond in a structured JSON response with keys: author, blog_title, category, summary, key_topics, sub_categories, url. "
            },
            {
                "role": "user",
                "content": classify_content
            }]
    current_app.logger.debug("prompt to classify: %s", prompt_string)
    return prompt_string