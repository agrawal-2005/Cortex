# Cortex

Cortex extracts tribal knowledge from company tools (Slack, Jira, Notion), synthesizes it into structured workflows called "skills," and serves them via API.

## Tech Stack

- **Backend:** FastAPI, Python 3.11+, LangChain, Celery
- **LLM:** Llama 3.1 8B via HuggingFace Inference API
- **Embeddings:** sentence-transformers/all-MiniLM-L6-v2
- **Storage:** PostgreSQL 16, ChromaDB, Redis
- **Frontend:** React + Tailwind CSS

## Quick Start

1. Copy the example environment file and fill in your tokens:

   ```bash
   cp .env.example .env
   ```

2. Start all services:

   ```bash
   docker-compose up --build
   ```

3. Access the application:
   - Backend API: http://localhost:8000
   - Frontend: http://localhost:3000
   - API docs: http://localhost:8000/docs
