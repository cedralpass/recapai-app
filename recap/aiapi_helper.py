import httpx
from environs import Env

class AiApiHelper:
    @staticmethod
    def ClassifyUrl(url, reference):
        env = Env()
        env.read_env()
        ai_url = env("RECAP_AI_API_URL")
        request_data = {'url': url, 'ref_key': reference, 'secret':"abc123"}
        print(ai_url)
        print('calling post to %s', ai_url)
        r = httpx.post(ai_url, data=request_data, timeout=60)
        return r.json()