import requests, uuid, json, os
from dotenv import load_dotenv

load_dotenv()
key = os.getenv("API_KEY_TRANSLATOR")
endpoint = "https://api.cognitive.microsofttranslator.com"
location = "eastus"

path = '/translate'
constructed_url = endpoint + path

params = {
    "api-version": "3.0",
    "from": "en",
    "to": ["fr", "zu"]
}

headers = {
    'Ocp-Apim-Subscription-Key': key,
    'Ocp-Apim-Subscription-Region': location,
    'Content-type': 'application/json',
    'X-ClientTraceId': str(uuid.uuid4())
}
body = [{
    'text': 'fuck'
}]

request = requests.post(constructed_url, params=params, headers=headers, json=body)
response = request.json()

print(json.dumps(response, sort_keys=True, ensure_ascii=False, indent=4, separators=(',', ': ')))
