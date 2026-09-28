# Campus Customs (HW4)

A Yale apparel storefront with an AI shopping assistant.

- **Frontend:** React + Vite + TypeScript (`frontend/`).
- **Backend:** FastAPI (`backend/main.py`) serving the catalogue, accounts and a PydanticAI chat agent. The agent is four files: `backend/prompts/prompt.md`, `agent.py`, `tools.py` and `models.py`.
- **Data:** the provided SQLite database and product photos (not in this repo).

The assistant answers price, stock and size questions from the database, shows category searches as product cards on the page, remembers logged-in customers, knows which product page you're on, and appends every chat run to `output/audit_trail.json`.

## Requirements

- Python 3.10+ (tested with 3.14)
- Node.js 20.19+ with npm (tested with Node 24)
- A Portkey API key with access to an OpenAI model (default `gpt-5.6-luna`)

## 1. Get the code and place the data pack

```bash
git clone https://github.com/vitaackerman/hw4.git
cd hw4
```

The database and product images aren't in git. Put the provided data pack in a `data/` folder in the repo root, so it looks like this:

```
hw4/
└── data/
    ├── campus_customs.db
    └── products/        # the product .jpg files referenced by the catalogue
```

## 2. Add your API key

```bash
cp .env.example .env
```

Open `.env` and replace `your-portkey-api-key-here` with your Portkey key. The backend looks for `.env` in the repo root or any parent folder. `OPENAI_MODEL` and `SESSION_SECRET` are optional.

## 3. Run the backend (terminal 1)

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r ../requirements.txt
uvicorn main:app --reload --port 8000
```

The backend runs at http://127.0.0.1:8000 (check it with http://127.0.0.1:8000/api/health). On first start it builds transparent product cutouts from `data/products/` in the background, which takes about 20 seconds, into `backend/.cache/` (gitignored).

Next time, you only need:

```bash
cd backend
source .venv/bin/activate
uvicorn main:app --reload --port 8000
```

## 4. Run the frontend (terminal 2)

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. Vite forwards `/api` and `/media` requests to the backend on port 8000, so start the backend first.

## Try it

- **Log in** with the seed test account `test@campuscustoms.yale.edu` / `password`, or create your own account.
- **Chat (bottom right):**
  - "What hoodies do you have?" puts every matching hoodie on the page as product cards.
  - "How much is the Boola Boola T Shirt, and do you have it in large?" should say $32, sold out in L, and offer similar tees that have L.
  - On any product page, "do you have this in XL?" answers for that product.
- **Products page:** filter by size in stock, price, color and category, and sort.
- **Audit trail:** each chat prints `Chat tools used (…)` in the backend terminal and appends an entry to `output/audit_trail.json`.

## Project layout

```
hw4/
├── AI_prompts.md            # prompts used for each problem
├── requirements.txt         # backend Python packages
├── .env.example             # placeholders only; copy to .env
├── README.md
├── frontend/                # Vite React TypeScript app
├── backend/
│   ├── main.py              # FastAPI app: uvicorn main:app --reload --port 8000
│   ├── agent.py             # PydanticAI agent: model, prompt loading, limits, output checks
│   ├── models.py            # all structured Pydantic types
│   ├── tools.py             # read-only database tools for the agent
│   ├── prompts/prompt.md    # system prompt: voice, tool rules, safety rules
│   ├── auth.py              # accounts, password hashing, session tokens
│   ├── chat_store.py        # saved chat history for logged-in customers
│   ├── audit.py             # append-only audit trail
│   └── cutouts.py           # transparent product image cutouts
└── output/
    ├── harness.md           # full system description (models, tools, safety, limits, memory, audit)
    ├── design.md            # storefront design decisions
    ├── usability.md         # usability improvements
    ├── app_check.html       # screenshot proof page (open by double-clicking)
    ├── app_check_images/    # screenshots linked from app_check.html
    └── audit_trail.json     # append-only log of agent runs
```

## Troubleshooting

- **`uvicorn: command not found` or `No module named 'fastapi'`:** the virtual environment isn't active. Run `source .venv/bin/activate` inside `backend/`.
- **Chat says "Can't reach the server":** the backend isn't running on port 8000, or it's running old code. Restart it with the command in step 3.
- **Chat says "The chat assistant isn't set up yet":** `PORTKEY_API_KEY` is missing from `.env`.
- **Products don't load or the backend fails at startup:** check that `data/campus_customs.db` and `data/products/` are in the repo root.

More detail on how everything works is in [`output/harness.md`](output/harness.md).
