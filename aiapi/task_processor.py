from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for,jsonify, current_app, logging
)
from werkzeug.exceptions import abort
import functools
import json
from openai import OpenAI
from aiapi.config import AIAPIConfig

bp = Blueprint('task_processor', __name__)

def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        key = extract_from_request('secret')
        if key is None:
            return jsonify("Not Authorized")

        return view(**kwargs)

    return wrapped_view

@bp.route('/process_task',methods=(['POST']))
@login_required
def process_task():
    url = None
    ref_key = None
    context = extract_from_request('context')
    prompt = extract_from_request('prompt')
    format = extract_from_request('format')
    ref_key = extract_from_request('ref_key')
    
    json_return={}

    #create OpenAI request
    client = OpenAI(api_key=current_app.config["AI_API_OPENAI"])
    
    #make OpenAI Call
    response = client.chat.completions.create(
        model=AIAPIConfig.AI_OPEN_AI_MODEL,
        messages=build_prompt(context, prompt, format),
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
        current_app.logger.debug("extract_from_request: value to missing for %s with value", key, value)
    return value

def build_prompt(context, prompt, format):
    
    context_element =  {
                "role": "system",
                "content": context
            }
    

    prompt_element=        {
                "role": "user",
                "content": prompt
            }
    
    prompt_array = [context_element , prompt_element]
    
    if format:
     format_element =  {
                "role": "system",
                "content": format
            }
     prompt_array.append(format_element)
     
    
    current_app.logger.debug("prompt to classify: %s", prompt_array)
    return prompt_array

