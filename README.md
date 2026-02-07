## Code Documentation Generator

This project aims to automatically generate high-quality documentation from source code.  
It combines static analysis, language models, and a simple frontend to let you:
- **Scan repositories** (local or remote, such as GitHub)
- **Analyze source code** using pluggable analyzers
- **Generate documentation** in formats like Markdown, DOCX, or HTML

### Project Structure

- **`backend/`**: Python backend logic
  - **`backend/__init__.py`**: Marks the backend package and will host high-level wiring.
  - **`backend/llm_handler.py`**: Entry point for interacting with LLM providers (e.g., Groq).
  - **`backend/analyzers/`**: Home for language- or framework-specific analyzers.
- **`frontend/`**: Frontend/UI layer (for example, a Gradio or web UI) to trigger analysis and view generated docs.
- **`output/`**: Default folder where generated documentation artifacts are saved.

### Prerequisites

- **Python 3.10+** (recommended)
- A **Groq API key** (for LLM-based analysis)
- A **GitHub personal access token** (if you want to fetch code directly from GitHub)

### Setup Instructions

1. **Create and activate a virtual environment (recommended)**  
   On Windows (PowerShell):

   ```bash
   python -m venv .venv
   .venv\\Scripts\\Activate.ps1
   ```

2. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**

   Edit the `.env` file at the project root and fill in your real values:

   ```env
   GROQ_API_KEY=your_groq_api_key_here
   GITHUB_TOKEN=your_github_token_here
   ```

4. **Run the backend / UI (placeholder)**

   Implementation details will depend on how you wire `llm_handler.py` and the frontend.  
   A typical pattern will look like:

   ```bash
   python -m backend.llm_handler
   ```

   or, if you expose a Gradio app:

   ```bash
   python -m backend.app
   ```

### Next Steps

- Implement concrete analyzers under `backend/analyzers/` (e.g., Python, JS/TS, React, etc.).
- Wire the backend to a simple UI in `frontend/` (Gradio or web).
- Define the format and schema of generated documentation in `output/`.

