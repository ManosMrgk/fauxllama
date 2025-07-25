# 🦙 fauxllama

**fauxllama** is a drop-in Ollama-compatible API server designed to simulate a local `Ollama` instance for GitHub Copilot Chat integrations. It allows developers to bring their own model backend — including Azure OpenAI, RAG pipelines, or finetuned models — and seamlessly use them in **Visual Studio Code** through the `byok.ollamaEndpoint` setting.

> TL;DR: fauxllama tricks VS Code into thinking it's talking to Ollama — but it's actually your own custom backend.

---

## ✨ Features

- ✅ **Ollama-compatible API** for Copilot Chat BYOK (`byok.ollamaEndpoint`)
- 🔐 **API Key Management** with per-user access control
- 💬 **Chat Logging** for dataset generation and training
- 🔁 **Streaming Responses** via Azure OpenAI-compatible completions
- 🧠 **Model Metadata Simulation** (e.g., family, quantization, digest)
- 📈 **Admin Panel** with basic auth to manage API keys
- 🐘 PostgreSQL-backed, with Flask-Migrate for schema control
- 🐳 Ready to deploy via `docker-compose`

---

## 📦 Project Structure
```
fauxllama/
├── server.py                      # Main Flask API server (entry point)
├── requirements.txt               # Python dependencies
├── Dockerfile                    # Backend container
├── docker-compose.yml             # App + PostgreSQL orchestration
├── .env.example                  # Environment variable template
├── migrations/                   # Flask-Migrate migration scripts

├── app/                         # Application package
│   ├── __init__.py              # Flask app factory & extensions initialization
│   ├── models.py                # SQLAlchemy models
│   ├── views/                   # Flask route handlers
│   │   ├── __init__.py
│   │   ├── api.py               # API endpoints
│   │   └── admin.py             # Flask-Admin setup & views
│   ├── utils/                   # Helper utilities
│   │   ├── __init__.py
│   │   ├── auth.py              # Auth (API key + HTTP Basic Auth)
│   │   ├── azure_openai.py      # Azure OpenAI integration helpers
│   │   ├── db_helpers.py        # DB helper functions (logging etc.)
│   │   └── limiter.py           # Rate limiting config
│   └── extensions.py            # Flask extensions (db, migrate, limiter, admin)
│
└── README.md                    
```

---

## 🚀 Use Case

The main use case is enabling **Copilot Chat** in VS Code to interact with your **own model infrastructure**, such as:

- Azure OpenAI deployments (GPT-4, GPT-3.5)
- Fine-tuned or private-hosted LLMs
- RAG pipelines or local inference stacks

By configuring VS Code like so:

```json
"github.copilot.chat.byok.ollamaEndpoint": "http://localhost:11434/YOUR_API_KEY"
```

---

## 🛠️ Setup Instructions

1. Clone the repo
```bash
git clone https://github.com/your-org/fauxllama.git
cd fauxllama
```
2. Create your environment config
```bash
cp .env.example .env
```
3. Start with Docker Compose
```bash
docker-compose up --build
```

Once running, the API will be live at:
http://localhost:11434

---

## 🔑 API Key Management
To create and manage API keys:

Visit the admin panel at:
http://localhost:11434/

Login using your ADMIN_PASSWORD from .env

Create a new API key per user

Each key maps to a user and is required for accessing chat endpoints.

---

## 📡 API Overview
All requests must include a valid API_KEY in the URL path:

```bash
POST /<API_KEY>/v1/chat/completions
```

---

## 🖥 VS Code Integration
To use fauxllama as your GitHub Copilot Chat backend:

1. Open VS Code settings.json

2. Add:

    ```json
    "github.copilot.chat.byok.ollamaEndpoint": "http://localhost:11434/YOUR_API_KEY"
    ```
3. Restart VS Code

Now, Copilot Chat will route requests through fauxllama.

---
**fauxllama** – Not a real llama. Just your LLM in disguise. 🦙
