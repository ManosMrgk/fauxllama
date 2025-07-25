import os
import requests
import json

def call_azure_openai(messages):
    endpoint = os.environ["AZURE_OPENAI_ENDPOINT"]
    deployment = os.environ["AZURE_OPENAI_DEPLOYMENT"]
    key = os.environ["AZURE_OPENAI_KEY"]
    version = os.environ.get("AZURE_OPENAI_VERSION", "2024-12-01-preview")

    url = f"{endpoint}/openai/deployments/{deployment}/chat/completions?api-version={version}"
    headers = {"api-key": key, "Content-Type": "application/json"}
    data = {
        "messages": messages,
        "temperature": 0.1,
        "top_p": 1,
        "n": 1,
        "stream": True
    }
    with requests.post(url, headers=headers, json=data, stream=True) as resp:
        resp.raise_for_status()
        for line in resp.iter_lines():
            if line:
                yield line.decode("utf-8")