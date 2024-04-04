from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for,jsonify, current_app, logging
)
from werkzeug.exceptions import abort
import functools
import json
from openai import OpenAI

bp = Blueprint('classify', __name__)

def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        key = extract_from_request('secret')
        if key is None:
            return jsonify("Not Authorized")

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
        model="gpt-4-turbo-preview",
        #model="gpt-3.5-turbo",
        messages=build_prompt(url),
            response_format={ "type": "json_object" },
            temperature=0.9,
            max_tokens=512,
            frequency_penalty=0,
            presence_penalty=0
            )
    
    if len(response.choices)>=1:
        current_app.logger.info(response.choices[0].message.content)
        json_return = response.choices[0].message.content
        current_app.logger.info("model %s cost %s", response.model, response.usage)
    else:
        current_app.logger.error("error: with openAPI call. no choices returned %s", response)

    response_json = json.loads(json_return)
    if ref_key is not None:
        response_json['ref_key']=ref_key


    return jsonify(response_json)

def extract_from_request(key):
    value=None
    if request.form.get(key) is not None:
        value = request.form.get(key)
    else:
         current_app.logger.error("error: must supply key for url for classification")
    current_app.logger.info("value to missing for %s", key)
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
    current_app.logger.info("prompt to classify: %s", prompt_string)
    return prompt_string