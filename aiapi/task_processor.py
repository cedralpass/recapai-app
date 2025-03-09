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
            return jsonify("Not Authorized"), 401

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
    prompt_history = extract_from_request('prompt_history')
    prompt_history_json = None
    if prompt_history:
        prompt_history_json = json.loads(prompt_history)

    if prompt is None:
        current_app.logger.error("error: missing prompt")
        return jsonify({"error": "Missing prompt"}), 400
   
    json_return={}
    response_format =  { "type": "json_object" } 

    #create OpenAI request
    client = OpenAI(api_key=current_app.config["AI_API_OPENAI"])
    prompt_array = build_prompt(context, prompt, format, prompt_history_json)

    #make OpenAI Call
    response = client.chat.completions.create(
        model=AIAPIConfig.AI_OPEN_AI_MODEL,
        messages=prompt_array,
            response_format=response_format,
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
        
        response_json = json.loads(json_return)
        if ref_key is not None:
            response_json['ref_key']=ref_key
            current_app.logger.debug("classify: added ref_key to response: " + ref_key)
        else:
            current_app.logger.error("error: missing ref_key")
        
        current_app.logger.debug("classify: full response " + str(response_json))
        return jsonify(response_json)
    else:
        current_app.logger.error("error: with openAPI call. no choices returned %s", response)
        error_response = {"error": "No response from OpenAI"}
        return jsonify(error_response)

def extract_from_request(key):
    value=None
    current_app.logger.debug("classify: request form keys: " + str(request.form.keys()))
    value = request.form.get(key)
    if value is None:
        current_app.logger.error("error: must supply url and secret for url for classification.  Supply a ref_key for refeference to an object.")
        current_app.logger.debug("extract_from_request: value to missing for %s with value", key)
    return value

def build_prompt(context, prompt, format_instructions=None, prompt_history=None):
    """
    Builds a prompt array for an AI model with the given context, prompt, and optional format instructions.

    Args:
        context (str): The context or system message for the prompt.
        prompt (str): The user's prompt or query.
        format_instructions (str, optional): Instructions for formatting the model's response.
        prompt_history (obj, optional): dictonary of prompt and response pairs.

    Returns:
        list: A list of dictionaries representing the prompt array.
    """
    prompt_array = []
    if context:
        prompt_array.append({"role": "system", "content": context})

    prompt_array.append({"role": "user", "content": prompt})

    if prompt_history:
        for pair in prompt_history:
           prompt_array.append({"role": "user", "content": pair["prompt"]})
           prompt_array.append({"role": "system", "content": pair["response"]})

    
    if format_instructions:
        prompt_array.append({"role": "system", "content": format_instructions})


    current_app.logger.debug("Prompt to process: %s", prompt_array)
    return prompt_array


