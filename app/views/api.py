from flask import Blueprint, jsonify, request, Response, stream_with_context
from app.utils.auth import authenticate_api_key
from app.utils.api_helpers import filter_user_model_messages
from app.services.openai_service import call_azure_openai
from app.services.chat_logger import log_chat_message, log_conversation
import uuid
import json

api_bp = Blueprint('api', __name__)

@api_bp.route('/<api_key>/api/models', methods=['GET'])
@api_bp.route('/<api_key>/api/tags', methods=['GET'])
def api_models_tags(api_key):
    try:
        _, username = authenticate_api_key(api_key)
    except Exception as e:
        return jsonify({"error": str(e)}), 401

    # Model info example
    model_info = {
        "models": [{
            "name": username,
            "model": username,
            "modified_at": "2025-07-18T15:51:16.1962348+03:00",
            "size": 3338801804,
            "digest": "a2af6cc3eb7fa8be8504abaf9b04e88f17a119ec3f04a3addf55f92841195f5a",
            "details": {
                "parent_model": "",
                "format": "gguf",
                "family": "gemma3",
                "families": ["gemma3"],
                "parameter_size": "4.3B",
                "quantization_level": "Q4_K_M"
            }
        }]
    }
    return jsonify(model_info)

@api_bp.route('/<api_key>/api/show', methods=['POST'])
def api_show(api_key):
    try:
        _, username = authenticate_api_key(api_key)
    except Exception as e:
        return jsonify({"error": str(e)}), 401
    # Simulated show response
    show_info = {
        "modelfile": "# Modelfile for fake-gemma3\nFROM fake-gemma3\n",
        "parameters": "top_p 0.95\ntemperature 1\ntop_k 64",
        "template": "{{- range .Messages}}\n<|im_start|>{{ .Role }}\n{{ .Content }}<|im_end|>\n{{- end}}\n<|im_start|>assistant",
        "details": {
            "parent_model": "",
            "format": "gguf",
            "family": "gemma3",
            "families": ["gemma3"],
            "parameter_size": "4.3B",
            "quantization_level": "Q4_K_M"
        },
        "model_info": {
            "general.architecture": "gemma3",
            "general.parameter_count": 4300000000,
            "general.quantization_version": 2
        },
        "capabilities": ["completion", "vision"],
        "modified_at": "2025-07-18T15:51:16.1962348+03:00"
    }
    return jsonify(show_info)

@api_bp.route('/<api_key>/v1/chat/completions', methods=['POST'])
def api_chat_completions(api_key):
    try:
        apikey_id, username = authenticate_api_key(api_key)
    except Exception as e:
        return jsonify({"error": str(e)}), 401

    # Parse request
    request_json = request.get_json(force=True)
    messages = request_json['messages']
    chat_messages = filter_user_model_messages(messages)
    conv_id = str(uuid.uuid4())
    model = request_json.get('model', 'unknown')

    # Log user messages
    log_conversation([chat_messages[-1]], conv_id, username, model, apikey_id)
    # Call Azure OpenAI model
    def event_stream():
        assistant_reply = ""  # Collect full response
        for raw_line in call_azure_openai(chat_messages):
            # Azure streams as: data: {...}
            if raw_line.startswith("data: "):
                data_json = raw_line[len("data: "):].strip()
                if data_json == "[DONE]":
                    yield "data: [DONE]\n\n"
                    break
                try:
                    data_obj = json.loads(data_json)
                    # Collect text for logging
                    delta = data_obj.get("choices", [{}])[0].get("delta", {})
                    if "content" in delta:
                        assistant_reply += delta["content"]
                except Exception:
                    pass  # If the chunk isn't valid JSON, skip collecting
                yield raw_line + "\n\n"  # Forward as-is to client

        # After streaming, log the assistant reply
        log_chat_message(
            conv_id=conv_id,
            order=len(chat_messages),
            role='model',
            text=assistant_reply,
            username=username,
            model=model,
            apikey_id=apikey_id
        )

    return Response(stream_with_context(event_stream()), mimetype='text/event-stream', headers={
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive'
    })

# --- Fallback for 404 ---
@api_bp.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Not found"}), 404