# Bootcamp IA

AI project using LangChain and Streamlit.

## Tech Stack
- **LangChain**: LLM orchestration.
- **Streamlit**: Web UI.
- **Python**: Core logic.
- **OpenAI/Google GenAI**: LLM providers.

## Requirements
- Python 3.9+
- API Keys (OpenAI or Google)

## Setup
1. Clone repo.
2. Setup virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Install deps:
   ```bash
   pip install -r requirements.txt
   ```
4. Configure `GOOGLE_API_KEY` environment variable.

## Run
```bash
streamlit run app_history_users.py
```
