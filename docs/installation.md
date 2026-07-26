# Installation

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
python -m pip install --upgrade pip
pip install -e ".[dev]"
python scripts/generate_demo_data.py
python -m heatsafe serve
```

Open `http://127.0.0.1:8000`. API documentation is at `/docs`.
