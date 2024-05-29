import httpx
from environs import Env
from flask import current_app

class AiApiHelper:
    @staticmethod
    def ClassifyUrl(url, reference):
        current_app.logger.debug("AiApiHelper: calling service to classify for url: %s and reference %s", url, reference)
        env = Env()
        env.read_env()
        ai_url = env("RECAP_AI_API_URL")
        current_app.logger.debug('AiApiHelper: calling post to %s', ai_url)
        request_data = {'url': url, 'ref_key': reference, 'secret':"abc123"}
        
        r = httpx.post(ai_url, data=request_data, timeout=60)
        results_json = r.json()
        current_app.logger.debug("AiApiHelper: recieved results as %s", results_json)
        return results_json