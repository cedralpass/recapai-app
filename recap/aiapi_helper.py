import httpx
from environs import Env
from flask import current_app

class AiApiHelper:
    @staticmethod
    def ClassifyUrl(url, reference):
        current_app.logger.debug("AiApiHelper: calling service to classify for url: %s and reference %s", url, reference)
        env = Env()
        env.read_env()
        ai_url = env("RECAP_AI_API_URL")+"/classify_url"
        current_app.logger.debug('AiApiHelper: calling post to %s', ai_url)
        results_json={}
        request_data = {'url': url, 'ref_key': reference, 'secret':"abc123"}
        try:
            r = httpx.post(ai_url, data=request_data, timeout=60)
            current_app.logger.debug("AiApiHelper: recieved results as %s", r)
            results_json = r.json()
            current_app.logger.debug("AiApiHelper: recieved results as %s", results_json)
        except httpx.HTTPError as http_err:
            current_app.logger.error(f'HTTP error occurred: {http_err}')
        except httpx.RequestError as req_err:
            current_app.logger.error(f'An error occurred while requesting: {req_err}')
        except httpx.HTTPStatusError as status_err:
            current_app.logger.error(f'Error response: {status_err}')
        except (ConnectionError, TimeoutError) as conn_err:
            current_app.logger.error(f'An error connecting to the API occurred: {conn_err}')
        except ValueError as value_err:
            current_app.logger.error(f'JSON decoding failed: {value_err}')
        except Exception as err:
            current_app.logger.error(f'An unexpected error occurred: {err}')
        return results_json
    
    @staticmethod
    def PerformTask(context, prompt, format, ref_key):
        current_app.logger.debug("AiApiHelper: calling service to perform task for context: %s, prompt: %s, format: %s, ref_key: %s", context, prompt, format, ref_key)
        env = Env()
        env.read_env()
        results_json={}
        ai_url = env("RECAP_AI_API_URL")+"/process_task"
        current_app.logger.debug('AiApiHelper: calling post to %s', ai_url)
        request_data = {'context': context, 'prompt': format, 'format': format , 'secret':"abc123", 'ref_key':ref_key}
        try:
            r = httpx.post(ai_url, data=request_data, timeout=60)
            results_json = r.json()
            current_app.logger.debug("AiApiHelper: recieved results as %s", results_json)
        except httpx.HTTPError as http_err:
            current_app.logger.error(f'HTTP error occurred: {http_err}')
        except httpx.RequestError as req_err:
            current_app.logger.error(f'An error occurred while requesting: {req_err}')
        except httpx.HTTPStatusError as status_err:
            current_app.logger.error(f'Error response: {status_err}')
        except (ConnectionError, TimeoutError) as conn_err:
            current_app.logger.error(f'An error connecting to the API occurred: {conn_err}')
        except ValueError as value_err:
            current_app.logger.error(f'JSON decoding failed: {value_err}')
        except Exception as err:
            current_app.logger.error(f'An unexpected error occurred: {err}')
        return results_json
    
    