<div align="center">
  <img src="frontend/src/resource/theme.png" alt="AI Database Architect logo" width="128" />
  <h1>AI Database Architect</h1>
  <p>
    <b>Next generation database schema design powered by AI</b>
  </p>
  <p>
    An intelligent, open-source database modeling tool that connects to your databases and turns natural-language requirements into clear ER diagrams and optimized schema designs.
  </p>
  <p>Available for Windows.</p>

<p>
    <a href="https://github.com/sleepy-ailurus/AIDatabaseArchitect/blob/main/LICENSE">
      <img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License" />
    </a>
    <img src="https://img.shields.io/badge/version-v1.0.0-blue.svg" alt="Version" />
    <a href="https://github.com/sleepy-ailurus/AIDatabaseArchitect/releases">
      <img src="https://img.shields.io/badge/downloads-releases-blue.svg" alt="Downloads" />
    </a>
  </p>

<p>
    <a href="https://github.com/sleepy-ailurus/AIDatabaseArchitect">Website</a> |
    <a href="#features">Features</a> |
    <a href="#download-and-installation">Downloads</a> |
    <a href="#development">Development</a>
  </p>
</div>

---

## Screenshot

<div align="center">
  <img src="docs/assets/Screenshot.jpg" alt="AI Database Architect screenshot" width="90%" />
</div>

---

## Features

- **AI-Powered Schema Analysis** — Connect to an existing database, or describe requirements in natural language, and let AI parse tables, fields, and relationships automatically.
- **Interactive ER Modeling** — Drag-and-drop ER diagram editor with automatic layout, relationship rendering, and one-click table editing.
- **Smart Relationship Recommendations** — AI suggests foreign keys and associations based on column names, types, and semantic context.
- **Multi-Database Support** — Design once and target MySQL and PostgreSQL.
- **Export Support** — Export schema documentation as Markdown.
- **LLM Configuration** — Configure your own API key and switch between compatible large language models.
- **Project Management** — Organize multiple database designs into projects with version history.
- **Clean Desktop UI** — Modern Vue3-based interface packaged as a native Windows application.

---

## Download and Installation

### Windows

Requires **Windows 10 or 11** (x64 or ARM64).

1. Go to the [Releases](https://github.com/sleepy-ailurus/AIDatabaseArchitect/releases) page.
2. Download the installer for your architecture:
   - `AIDatabaseArchitect-win-x64-v1.0.0-setup.exe`
   - `AIDatabaseArchitect-win-arm64-v1.0.0-setup.exe`
3. Run the setup wizard and follow the on-screen instructions.
4. Launch **AI Database Architect** from the Start menu or desktop shortcut.

> The application is packaged as a standalone Windows installer. No manual Python or Node.js setup is required.

Want to see what changed? Check the [CHANGELOG](https://github.com/sleepy-ailurus/AIDatabaseArchitect).

---

## Development

AI Database Architect is built with a Python **FastAPI** backend and a **Vue 3 + Vite** frontend.

### Prerequisites

- Python 3.13+
- Node.js 21+
- uv (recommended) or pip

### Backend

```bash
cd backend

# Option 1: uv (recommended)
uv sync
uv run python run.py

# Option 2: pip only
pip install -r requirements.txt
python run.py
```

> The backend starts on http://localhost:8000.

### Frontend

```bash
cd frontend
npm install
npm run dev          # starts on http://localhost:5173
```

The frontend proxies API calls to `http://localhost:8000` during development.

If you have questions or run into issues, feel free to open an [issue](https://github.com/sleepy-ailurus/AIDatabaseArchitect/issues).

---

## License

[MIT](LICENSE)
