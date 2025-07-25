def filter_user_model_messages(messages):
    return [m for m in messages if m['role'] in ('user', 'assistant', 'model')]