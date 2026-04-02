"""
Text-to-SQL Chatbot Backend
- Reads ALL table metadata from workorder_metadata.xlsx
- Dynamically discovers DB tables
- Picks relevant tables per question using metadata keywords
- Injects rich schema context (descriptions, FKs, notes) into LLM prompt
- Single LLM call → SQL → execute → stream results
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from langchain_ollama import OllamaLLM
from sqlalchemy import text, create_engine, inspect
from urllib.parse import quote_plus
import pandas as pd
import re, json, time, uvicorn, logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─── CONFIG ───────────────────────────────────────────────────────────────────
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "urock",   # <-- change this
    "username": "postgres",         # <-- change this
    "password": "sa123",         # <-- change this
}
METADATA_FILE = "table_metadata.xlsx"  # must be in same folder as backend.py

EXCLUDE_TABLES = {
    "__EFMigrationsHistory",
    "WO_BCK_ALL_0926", "wo_bck_0926",
    "SampleSpecimens_BCK", "Samples_BCK",
    "FormBillingLabors_BCK",
    "view_backup", "view_backup_audit",
    "v_all_ids", "totalprojects",
}

MAX_TABLES_IN_PROMPT = 10   # max tables sent to LLM per question

DB_URI = (
    f"postgresql://{DB_CONFIG['username']}:{quote_plus(DB_CONFIG['password'])}"
    f"@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
)

# ─── APP ──────────────────────────────────────────────────────────────────────
app = FastAPI(title="DB Chatbot API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

engine       = None
llm          = None
_all_tables  = []
_meta        = {}   # { table_name: { description, name_column, notes, columns: {col: desc}, rels: [...] } }
_schema_cache = {}  # { table_name: full schema string with metadata }
_eco_map     = []   # ecosystem map rows: [{question_type, join_path, filter_example}]
_table_keywords = {} # { table_name: set of keywords for matching }


# ═══════════════════════════════════════════════════════════════════════════════
# EXCEL METADATA READER
# ═══════════════════════════════════════════════════════════════════════════════
def load_excel_metadata(path: str) -> tuple[dict, list]:
    """
    Reads table_metadata.xlsx with 3 flat sheets:
      Tables:        TableName, Description, NameColumn, ImportantNotes
      Columns:       TableName, ColumnName, Description, Relationship
      Relationships: FromTable, FromColumn, ToTable, ToColumn, Notes
    """
    p = Path(path)
    if not p.exists():
        logger.warning(f"Metadata file not found: {path}")
        return {}, []
    try:
        xl = pd.ExcelFile(p)

        # ── Sheet 1: Tables ──
        t_df = xl.parse("Tables", dtype=str).fillna("")
        meta = {}
        for _, row in t_df.iterrows():
            tname = str(row.get("TableName","")).strip()
            if not tname: continue
            meta[tname] = {
                "description": str(row.get("Description","")),
                "name_column": str(row.get("NameColumn","")),
                "notes":       str(row.get("ImportantNotes","")),
                "columns":     {},
                "relationships": [],
            }

        # ── Sheet 2: Columns ──
        c_df = xl.parse("Columns", dtype=str).fillna("")
        for _, row in c_df.iterrows():
            tname = str(row.get("TableName","")).strip()
            cname = str(row.get("ColumnName","")).strip()
            if not tname or not cname: continue
            if tname not in meta:
                meta[tname] = {"description":"","name_column":"","notes":"","columns":{},"relationships":[]}
            meta[tname]["columns"][cname] = {
                "desc": str(row.get("Description","")),
                "rel":  str(row.get("Relationship","")),
            }

        # ── Sheet 3: Relationships ──
        r_df = xl.parse("Relationships", dtype=str).fillna("")
        for _, row in r_df.iterrows():
            ft = str(row.get("FromTable","")).strip()
            if not ft: continue
            if ft not in meta:
                meta[ft] = {"description":"","name_column":"","notes":"","columns":{},"relationships":[]}
            meta[ft]["relationships"].append({
                "from_col": str(row.get("FromColumn","")),
                "to_table": str(row.get("ToTable","")),
                "to_col":   str(row.get("ToColumn","")),
                "note":     str(row.get("Notes","")),
            })

        logger.info(f"Metadata loaded: {len(meta)} tables from Excel")
        return meta, []

    except Exception as ex:
        logger.error(f"Failed to load metadata: {ex}", exc_info=True)
        return {}, []


    except Exception as ex:
        logger.error(f"Failed to load metadata: {ex}", exc_info=True)
        return {}, []


def build_table_keywords(meta: dict) -> dict:
    """
    Build a keyword set per table for smart table selection.
    Extracts words from table name, description, column names, notes.
    """
    kw = {}
    for tname, info in meta.items():
        words = set()
        # From table name (CamelCase split)
        for w in re.findall(r'[A-Z][a-z]+|[A-Z]{2,}(?=[A-Z]|$)', tname):
            words.add(w.lower())
        # From description
        for w in re.findall(r'[a-z]{4,}', info.get("description", "").lower()):
            words.add(w)
        # From column names
        for col in info.get("columns", {}):
            for w in re.findall(r'[A-Z][a-z]+', col):
                words.add(w.lower())
        # From notes
        for note in info.get("notes", []):
            for w in re.findall(r'[a-z]{4,}', note.lower()):
                words.add(w)
        kw[tname] = words
    return kw


def build_schema_from_metadata(tname: str, db_cols: list, meta: dict) -> str:
    """Build rich schema string from flat Excel metadata."""
    info     = meta.get(tname, {})
    col_meta = info.get("columns", {})
    rels     = info.get("relationships", [])
    notes    = info.get("notes", "")       # now a string not list
    desc     = info.get("description", "")
    name_col = info.get("name_column", "")

    lines = []

    # Table header + description
    if desc:
        lines.append(f"-- TABLE: {tname}")
        lines.append(f"-- {desc}")
    else:
        lines.append(f"-- TABLE: {tname}")

    # Important notes (split by period for readability, keep max 3)
    if notes:
        note_parts = [n.strip() for n in notes.split(".") if len(n.strip()) > 10]
        for np in note_parts[:3]:
            lines.append(f"-- NOTE: {np}")

    # Name column hint
    if name_col and name_col in db_cols:
        lines.append(f'-- NAME COLUMN: Use "{tname}"."{name_col}" for display and output')

    # Column definitions with inline descriptions from Excel
    col_parts = []
    for col in db_cols:
        cm    = col_meta.get(col, {})
        cdesc = cm.get("desc", "")
        crel  = cm.get("rel", "")
        annotation = ""
        if cdesc:
            annotation = f"  -- {cdesc}"
            if crel and "->" in crel:
                annotation += f" {crel}"
        elif crel and "->" in crel:
            annotation = f"  -- {crel}"
        col_parts.append(f'  "{col}" TEXT{annotation}')

    lines.append(f'CREATE TABLE "{tname}" (')
    lines.append(",\n".join(col_parts))
    lines.append(");")

    # Relationship lines from Excel
    for r in rels:
        to    = r.get("to_table","").strip()
        tc    = r.get("to_col","").strip()
        fc    = r.get("from_col","").strip()
        note_ = r.get("note","").strip()
        comment = f"  -- {note_}" if note_ else ""
        if to and fc:
            lines.append(f'-- FK: "{tname}"."{fc}" -> "{to}"."{tc}"{comment}')

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# TABLE DISCOVERY & SCHEMA CACHE
# ═══════════════════════════════════════════════════════════════════════════════
def discover_tables(eng) -> list:
    with eng.connect() as conn:
        rows = conn.execute(text(
            "SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname = 'public' ORDER BY tablename"
        ))
        tables = [r[0] for r in rows if r[0] not in EXCLUDE_TABLES]
    logger.info(f"Discovered {len(tables)} tables")
    return tables


def build_schema_cache(eng, tables: list, meta: dict) -> dict:
    insp  = inspect(eng)
    cache = {}
    for t in tables:
        try:
            db_cols = [c["name"] for c in insp.get_columns(t)]
            if t in meta:
                # Use rich metadata schema
                cache[t] = build_schema_from_metadata(t, db_cols, meta)
            else:
                # Fallback: plain CREATE TABLE with just column names
                col_defs = ",\n  ".join(f'"{c}" TEXT' for c in db_cols)
                cache[t] = f'CREATE TABLE "{t}" (\n  {col_defs}\n);'
        except Exception as ex:
            logger.warning(f"Could not inspect {t}: {ex}")
    logger.info(f"Schema cache built for {len(cache)} tables")
    return cache


# ═══════════════════════════════════════════════════════════════════════════════
# TABLE SELECTION
# ═══════════════════════════════════════════════════════════════════════════════
def pick_relevant_tables(question: str, all_tables: list, limit: int) -> list:
    q_lower = question.lower()
    q_words = set(re.findall(r'[a-z]+', q_lower))
    scored  = []

    for t in all_tables:
        score = 0

        # Exact table name match
        if t.lower() in q_lower:
            score += 100

        # CamelCase word match (skip DT_ tables)
        if not t.startswith("DT_"):
            for w in re.findall(r'[A-Z][a-z]+', t):
                if w.lower() in q_words and len(w) >= 4:
                    score += 10

        # Metadata keyword match
        kw = _table_keywords.get(t, set())
        for w in q_words:
            if len(w) >= 5 and w in kw:
                score += 5

        scored.append((score, t))

    scored.sort(key=lambda x: -x[0])
    # ── Reduce score for noisy utility tables unlikely to be needed ──
    noisy_tables = {
        "HierarchyWorkOrderSettings",
        "WorkItemReports", 
        "AbpOrganizationUnitRoles",
        "AbpUserOrganizationUnits",
    }

    # Re-score — only include noisy tables if explicitly mentioned or score > 20
    scored = [(s - 30 if t in noisy_tables else s, t) for s, t in scored]
    selected = [t for s, t in scored if s > 0][:limit]

    # ── Domain-specific forced tables ──
    # Work orders
    if any(w in q_words for w in ["workorder", "work", "order", "orders", "wo"]):
        for t in ["WorkOrders"]:
            if t in all_tables and t not in selected:
                selected.insert(0, t)

    # Users / roles
    if any(w in q_words for w in ["user", "username", "creator", "created", "technician", "manager", "active"]):
        for t in ["AbpUsers"]:
            if t in all_tables and t not in selected:
                selected.insert(0, t)

    if any(w in q_words for w in ["role", "manager", "admin", "permission", "engineer", "dispatcher", "technician"]):
        for t in ["AbpUsers", "AbpUserRoles", "AbpRoles"]:
            if t in all_tables and t not in selected:
                selected.insert(0, t)

    # Projects
    if any(w in q_words for w in ["project", "projects"]):
        if "Projects" in all_tables and "Projects" not in selected:
            selected.insert(0, "Projects")

    # Offices / location
    if any(w in q_words for w in ["office", "location", "city", "branch",
                                    "myers", "fort", "charleston", "miami",
                                    "orlando", "dallas", "houston", "atlanta"]):
        if "Offices" in all_tables and "Offices" not in selected:
            selected.insert(0, "Offices")

    # Specimens / tests
    if any(w in q_words for w in ["specimen", "specimens", "sample", "test", "tests"]):
        for t in ["WorkOrderTests", "SampleSpecimens"]:
            if t in all_tables and t not in selected:
                selected.append(t)

    # Forms
    if any(w in q_words for w in ["form", "forms"]):
        if "Forms" in all_tables and "Forms" not in selected:
            selected.append("Forms")

    selected = list(dict.fromkeys(selected))  # deduplicate keeping order
    return selected[:limit]


def get_eco_hint(question: str) -> str:
    """
    Find matching ecosystem map entry for the question and return as hint.
    """
    q = question.lower()
    matches = []
    for entry in _eco_map:
        qt = entry.get("question_type", "").lower()
        # Score by word overlap
        score = sum(1 for w in qt.split() if len(w) > 3 and w in q)
        if score > 0:
            matches.append((score, entry))

    if not matches:
        return ""

    matches.sort(key=lambda x: -x[0])
    best = matches[0][1]
    hint = (
        f"-- ECOSYSTEM HINT: For '{best['question_type']}' queries:\n"
        f"--   Tables: {best['join_path']}\n"
        f"--   Example: {best['filter_example']}"
    )
    return hint


# ═══════════════════════════════════════════════════════════════════════════════
# STARTUP
# ═══════════════════════════════════════════════════════════════════════════════
try:
    # Load metadata from Excel
    _meta, _eco_map = load_excel_metadata(METADATA_FILE)
    logger.info(f"Metadata tables loaded: {list(_meta.keys())}") 
    _table_keywords = build_table_keywords(_meta)

    # Connect DB
    engine      = create_engine(DB_URI)
    _all_tables = discover_tables(engine)

    # Build schema cache using metadata
    _schema_cache = build_schema_cache(engine, _all_tables, _meta)

    llm = OllamaLLM(
        model="qwen2.5-coder:7b",
        temperature=0.0,
        num_ctx=8192,
        num_predict=400,
    )
    logger.info("LLM ready.")

except Exception as e:
    logger.error(f"Startup error: {e}", exc_info=True)


# ═══════════════════════════════════════════════════════════════════════════════
# PROMPT
# ═══════════════════════════════════════════════════════════════════════════════
SQL_PROMPT = """\
### Instructions:
Convert the question into a single valid PostgreSQL SELECT query.

Rules:
- Only use tables and columns listed in the schema below
- Always double-quote table and column names: "TableName"."ColumnName"
- Read ALL comments (-- lines) carefully — they explain column purpose, FKs, and warnings
- Use ILIKE for case-insensitive text search: WHERE "OfficeName" ILIKE '%Fort Myers%'
- Boolean columns use actual booleans: "IsDeleted" = false (not 'false')
- "AbpRoles"."DisplayName" is the human-readable role name — ALWAYS use for WHERE and SELECT
- "WorkOrders"."WorkOrderNumber" is TEXT — never use as integer. Use Id for JOINs.
- To filter active users use "AbpUsers"."IsActive" = true
- Return ONLY the SQL query, no explanation, no markdown

{eco_hint}

### Question:
{question}

### Schema:
{schema}

### SQL:
SELECT"""


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════
def get_schema_for_question(question: str) -> tuple[str, list]:
    selected = pick_relevant_tables(question, _all_tables, MAX_TABLES_IN_PROMPT)
    lines    = [_schema_cache[t] for t in selected if t in _schema_cache]
    return "\n\n".join(lines), selected


def extract_sql(raw: str) -> str:
    raw = re.sub(r"```sql", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"```", "", raw)
    raw = raw.strip()
    if not raw.upper().startswith(("SELECT", "WITH")):
        raw = "SELECT " + raw
    match = re.search(r"(SELECT|WITH)\b.*", raw, flags=re.IGNORECASE | re.DOTALL)
    if match:
        sql = match.group(0).strip()
        if ";" in sql:
            sql = sql[:sql.index(";") + 1]
        return sql
    return raw


def run_query(sql: str):
    try:
        with engine.connect() as conn:
            result   = conn.execute(text(sql))
            cols     = list(result.keys())
            raw_rows = result.fetchmany(50)

        def safe(v):
            if v is None: return None
            if isinstance(v, (int, float, bool)): return v
            if isinstance(v, str): return v
            return str(v)

        rows = [[safe(v) for v in row] for row in raw_rows]
        return rows, cols, None
    except Exception as ex:
        return [], [], str(ex)


def sse(t: str, data: dict) -> str:
    return f"data: {json.dumps({'type': t, **data})}\n\n"


def generate_metadata(question: str, cols: list, rows: list) -> dict:
    sample = rows[:3] if rows else []
    prompt = (
        f'Given this question and results, return JSON with two fields:\n'
        f'"title": short 5-8 word summary\n'
        f'"chart_type": "pie", "bar", "line", or null\n\n'
        f'Question: {question}\nColumns: {cols}\nSample: {sample}\n\n'
        f'Return ONLY JSON: {{"title": "...", "chart_type": null}}'
    )
    try:
        raw   = llm.invoke(prompt).strip()
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            data = json.loads(match.group(0))
            return {
                "title":      str(data.get("title", question[:50])),
                "chart_type": data.get("chart_type") if data.get("chart_type") in ["pie","bar","line"] else None,
            }
    except Exception:
        pass
    return {"title": question[:50].capitalize(), "chart_type": None}


# ═══════════════════════════════════════════════════════════════════════════════
# STREAM HANDLER
# ═══════════════════════════════════════════════════════════════════════════════
async def chat_stream(question: str):
    try:
        schema, selected = get_schema_for_question(question)
        logger.info(f"Schema sent to LLM:\n{schema}")
        eco_hint         = get_eco_hint(question)

        logger.info(f"Tables selected ({len(selected)}): {selected}")
        logger.info(f"Eco hint: {eco_hint[:120] if eco_hint else 'none'}")

        prompt = SQL_PROMPT.format(
            schema=schema,
            question=question,
            eco_hint=eco_hint if eco_hint else "",
        )
        logger.info(f"Prompt size: {len(prompt)} chars")

        yield sse("status",      {"text": "Generating SQL…"})
        yield sse("tables_used", {"tables": selected})

        t0  = time.time()
        raw = llm.invoke(prompt)
        t1  = time.time()
        logger.info(f"LLM {t1-t0:.1f}s | Raw: {raw[:400]}")

        sql = extract_sql(str(raw))
        logger.info(f"SQL: {sql}")

        if not sql or len(sql) < 7:
            yield sse("error", {"text": "Could not generate SQL. Try rephrasing."})
            return

        yield sse("sql",    {"text": sql, "time": round(t1 - t0, 1)})
        yield sse("status", {"text": "Running query…"})

        t2 = time.time()
        rows, cols, err = run_query(sql)
        t3 = time.time()

        if err:
            yield sse("error", {"text": f"SQL error: {err}"})
            return

        meta        = generate_metadata(question, cols, rows)
        chart_type  = meta["chart_type"]
        title       = meta["title"]
        chart_title = title if chart_type else None

        yield sse("result", {
            "columns":     cols,
            "rows":        rows,
            "count":       len(rows),
            "title":       title,
            "chart_type":  chart_type,
            "chart_title": chart_title,
            "timings": {
                "sql_gen":  round(t1 - t0, 1),
                "db_query": round(t3 - t2, 1),
                "total":    round(t3 - t0, 1),
            }
        })

    except Exception as ex:
        logger.error(f"Stream error: {ex}", exc_info=True)
        yield sse("error", {"text": str(ex)})


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════
class AskRequest(BaseModel):
    message: str

@app.post("/chat")
async def chat(req: AskRequest):
    if not llm or not engine:
        raise HTTPException(503, "Backend not ready.")
    return StreamingResponse(
        chat_stream(req.message),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

@app.get("/health")
def health():
    return {
        "status":        "ok" if (engine and llm) else "error",
        "model":         "qwen2.5-coder:7b",
        "total_tables":  len(_all_tables),
        "metadata_tables": len(_meta),
        "tables":        _all_tables,
    }

@app.get("/tables")
def list_tables():
    return {"total": len(_all_tables), "tables": _all_tables}

@app.get("/debug/schema")
def debug_schema(question: str = "work orders in Fort Myers"):
    schema, selected = get_schema_for_question(question)
    logger.info(f"Schema sent to LLM:\n{schema}")
    eco = get_eco_hint(question)
    return {
        "tables_selected": selected,
        "eco_hint":        eco,
        "schema":          schema,
        "chars":           len(schema),
    }

@app.get("/debug/prompt")
def debug_prompt(question: str = "work orders in Fort Myers"):
    schema, selected = get_schema_for_question(question)
    eco   = get_eco_hint(question)
    prompt = SQL_PROMPT.format(schema=schema, question=question, eco_hint=eco)
    return {"tables_selected": selected, "chars": len(prompt), "prompt": prompt}

@app.get("/debug/metadata")
def debug_metadata(table: str = "WorkOrders"):
    return _meta.get(table, {"error": f"{table} not found in metadata"})

@app.get("/test/speed")
def test_speed():
    t0 = time.time()
    out = llm.invoke("Return only: SELECT 1")
    return {"elapsed_seconds": round(time.time() - t0, 2), "output": out}


if __name__ == "__main__":
    uvicorn.run("backend_metadata:app", host="0.0.0.0", port=8000, reload=True)
