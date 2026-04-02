

# ─── CONFIG ───────────────────────────────────────────────────────────────────



"""
Text-to-SQL Chatbot Backend
- Tables loaded DYNAMICALLY from public schema — no hardcoding
- EXCLUDE_TABLES: only list tables you want to skip (backups, migrations etc.)
- Compact schema cache so 500+ tables don't overflow the LLM context
- Single LLM call, results returned as structured table data
"""
 
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from langchain_ollama import OllamaLLM
from langchain_community.utilities import SQLDatabase
from sqlalchemy import text, create_engine, inspect
import re, json, time, uvicorn, logging
 
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

# Only list tables you want to SKIP — everything else loads automatically.
# Common things to exclude: migration history, backups, audit logs, views.
EXCLUDE_TABLES = {
    "__EFMigrationsHistory",
    "WO_BCK_ALL_0926", "wo_bck_0926",
    "SampleSpecimens_BCK", "Samples_BCK",
    "FormBillingLabors_BCK",
    "view_backup", "view_backup_audit",
    "v_all_ids",
    "totalprojects",
}
 
# How many tables to send to the LLM per question.
# With 500+ tables we can't send all schemas — we pick the most relevant ones.
MAX_TABLES_IN_PROMPT =  8
 
DB_URI = (
    f"postgresql://{DB_CONFIG['username']}:{DB_CONFIG['password']}"
    f"@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
)
 
# ─── APP ──────────────────────────────────────────────────────────────────────
app = FastAPI(title="DB Chatbot API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
 
db            = None
llm           = None
engine        = None
_all_tables   = []     # all discovered table names
_full_schema  = {}     # { table_name: "TableName(col1, col2, ...)" }
 
 
# ─── DYNAMIC TABLE DISCOVERY ──────────────────────────────────────────────────
def discover_tables(eng) -> list:
    """Read all table names from public schema, minus excluded ones."""
    with eng.connect() as conn:
        rows = conn.execute(text("""
            SELECT tablename
            FROM pg_catalog.pg_tables
            WHERE schemaname = 'public'
            ORDER BY tablename
        """))
        tables = [r[0] for r in rows if r[0] not in EXCLUDE_TABLES]
    logger.info(f"Discovered {len(tables)} tables from public schema")
    return tables
 
 
def build_full_schema_cache(eng, tables: list):
    insp  = inspect(eng)
    cache = {}
    for t in tables:
        try:
            cols     = [c["name"] for c in insp.get_columns(t)]
            col_defs = ", ".join(f'"{c}" TEXT' for c in cols)

            fk_lines = []
            for fk in insp.get_foreign_keys(t):
                ref_table  = fk["referred_table"]
                local_col  = fk["constrained_columns"][0]
                remote_col = fk["referred_columns"][0]
                fk_lines.append(
                    f'-- FK: "{t}"."{local_col}" -> "{ref_table}"."{remote_col}"'
                )

            # Manually add known relationships missing from DB constraints
            manual_fks = {
                "WorkOrders": ['-- FK: "WorkOrders"."CreatorUserId" -> "AbpUsers"."Id"'],
                "Projects":   ['-- FK: "Projects"."CreatorUserId" -> "AbpUsers"."Id"'],
                "Forms":      ['-- FK: "Forms"."CreatorUserId" -> "AbpUsers"."Id"'],
                "Samples":    ['-- FK: "Samples"."CreatorUserId" -> "AbpUsers"."Id"'],
                "AbpUserRoles": ['-- FK: "AbpUserRoles"."RoleId" -> "AbpRoles"."Id"','-- FK: "AbpUserRoles"."UserId" -> "AbpUsers"."Id"'],
            }
            if t in manual_fks:
                fk_lines.extend(manual_fks[t])

            fk_str = ("\n" + "\n".join(fk_lines)) if fk_lines else ""

            # Auto-hint DisplayName vs Name based on actual columns
            table_comment = ""
            if "DisplayName" in cols and "Name" in cols:
                table_comment = f'\n-- HINT: Always use "{t}"."DisplayName" for both display AND WHERE filters. "Name" column contains GUIDs — never use it for matching role names.'
            elif "DisplayName" in cols:
                table_comment = f'\n-- HINT: Use "{t}"."DisplayName" for display output.'

            # Name column hints for key tables
            manual_display_hints = {
                "Projects":   "ProjectName",
                "WorkOrders": "Subject",
                "Clients":    "Name",
                "Companies":  "Name",
            }
            name_hint = ""
            if t in manual_display_hints:
                col = manual_display_hints[t]
                if col in cols:
                    name_hint = f'\n-- NAME COLUMN: Use "{t}"."{col}" as the display name for this table'

            cache[t] = f'CREATE TABLE "{t}" ({col_defs});{fk_str}{table_comment}{name_hint}'

        except Exception as e:
            logger.warning(f"Could not inspect {t}: {e}")
    logger.info(f"Schema cache built for {len(cache)} tables")
    return cache
 
 
def pick_relevant_tables(question: str, all_tables: list, limit: int) -> list:
    q_lower = question.lower()
    q_words = set(re.findall(r'[a-z]+', q_lower))
    scored  = []

    for t in all_tables:
        score = 0
        if t.lower() in q_lower:          # exact table name in question = top priority
            score += 100
        if not t.startswith("DT_"):        # skip DT_* word matching (prevents false hits)
            words = re.findall(r'[A-Z][a-z]+', t)
            for w in words:
                if w.lower() in q_words and len(w) >= 4:
                    score += 10
        scored.append((score, t))

    scored.sort(key=lambda x: -x[0])
    selected = [t for s, t in scored if s > 0][:limit]

    # Force AbpUsers when question mentions user/username/creator
    if any(w in q_words for w in ["user", "username", "created", "creator", "ssanka"]):
        if "AbpUsers" not in selected and "AbpUsers" in all_tables:
            selected.insert(0, "AbpUsers")
            if len(selected) > limit:
                selected = selected[:limit]
    if any(w in q_words for w in ["role", "manager", "admin", "permission", "active"]):
        for tbl in ["AbpUsers", "AbpUserRoles", "AbpRoles"]:
            if tbl not in selected and tbl in all_tables:
                selected.insert(0, tbl)
        selected = selected[:limit]            

    if any(w in q_words for w in ["project", "projects"]):
        if "Projects" not in selected and "Projects" in all_tables:
            selected.insert(0, "Projects")
            if len(selected) > limit:
                selected = selected[:limit]

    return selected[:limit]
 
# ─── STARTUP ──────────────────────────────────────────────────────────────────
try:
    engine       = create_engine(DB_URI)
    _all_tables  = discover_tables(engine)
    _full_schema = build_full_schema_cache(engine, _all_tables)
 
    # LangChain SQLDatabase — used only for metadata; pass all tables
    db = SQLDatabase.from_uri(
        DB_URI,
        sample_rows_in_table_info=0,
        include_tables=_all_tables,
    )
    logger.info(f"SQLDatabase ready with {len(_all_tables)} tables")
 
    llm = OllamaLLM(
        model="qwen2.5-coder:7b",
        temperature=0.0,
        num_ctx=8192,
        num_predict=400,
    )
    logger.info("LLM ready.")
 
except Exception as e:
    logger.error(f"Startup error: {e}")
 
 
# ─── PROMPT ──────────────────────────────────────────────────────────────────

SQL_PROMPT = """\
### Instructions:
Your task is to convert a question into a SQL query, given a Postgres database schema.
Adhere to these rules:
- Only use tables and columns from the schema below
- Always quote BOTH table names AND column names with double quotes e.g. "Projects"."Id"
- Never write TableName.ColumnName — always write "TableName"."ColumnName"
- "WorkOrders"."CreatorUserId" links to "AbpUsers"."Id" for user lookups
- Return ONLY the SQL query, no explanation
- Column names must be taken exactly from the schema — never guess or invent column names
- The roles table is "AbpRoles" — never use "Roles"
- The user-roles mapping table is "AbpUserRoles" — use it to count users per role
- Only use "DisplayName" if it is explicitly listed in that table's schema — never assume a table has it
- If the schema hint says to use "DisplayName", prefer it for output; otherwise use whatever name column exists in the schema
- Use the NAME COLUMN hint in the schema to identify the correct display name column for each table
- Boolean columns like "IsDeleted", "IsActive" store actual booleans — use "IsDeleted" = false (not 'False')
- For "AbpRoles", always use "DisplayName" for both SELECT and WHERE — the "Name" column contains GUIDs not readable names



### Example:
Question: count work orders created by user ssanka
SQL: SELECT COUNT(*) FROM "WorkOrders" w JOIN "AbpUsers" u ON w."CreatorUserId" = u."Id" WHERE u."UserName" = 'ssanka';

### Input:
Generate a SQL query that answers the question: {question}

### Database Schema:
{schema}

### Response:
SELECT"""
 
 
# ─── HELPERS ──────────────────────────────────────────────────────────────────
def get_schema_for_question(question: str) -> tuple[str, list]:
    """Return (compact_schema_string, selected_table_names) for this question."""
    selected = pick_relevant_tables(question, _all_tables, MAX_TABLES_IN_PROMPT)
    lines    = [_full_schema[t] for t in selected if t in _full_schema]
    return "\n".join(lines), selected
 
 
def extract_sql(raw: str) -> str:
    raw = re.sub(r"```sql", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"```",    "", raw)
    raw = raw.strip()
    if not raw.upper().startswith("SELECT") and not raw.upper().startswith("WITH"):
        raw = "SELECT " + raw
    match = re.search(r"(SELECT|WITH)\b.*", raw, flags=re.IGNORECASE | re.DOTALL)
    if match:
        sql = match.group(0).strip()
        if ";" in sql:
            sql = sql[: sql.index(";") + 1]
        return sql
    return raw
 
 
def run_query(sql: str):
    """Execute SQL, return (rows, cols, error)."""
    try:
        with engine.connect() as conn:
            result = conn.execute(text(sql))
            cols   = list(result.keys())
            raw_rows = result.fetchmany(50)

        # Convert all values to JSON-safe types
        def safe(v):
            if v is None:
                return None
            if isinstance(v, (int, float, bool)):
                return v
            if isinstance(v, str):
                return v
            # date, datetime, Decimal, UUID, etc → string
            return str(v)

        rows = [[safe(v) for v in row] for row in raw_rows]
        return rows, cols, None
    except Exception as e:
        return [], [], str(e)
 
 
def sse(t: str, data: dict) -> str:
    return f"data: {json.dumps({'type': t, **data})}\n\n"
 
def generate_title(question: str, sql: str, cols: list, rows: list) -> str:
    """Generate a short human-readable title from the question and results."""
    q = question.lower().strip()

    # Count queries
    if "count" in q or (len(cols) == 1 and rows and len(rows) == 1):
        val = rows[0][0] if rows else 0
        if "project" in q:   return f"Total Projects: {val}"
        if "workorder" in q or "work order" in q: return f"Total Work Orders: {val}"
        if "user" in q:      return f"Total Users: {val}"
        if "form" in q:      return f"Total Forms: {val}"
        if "sample" in q:    return f"Total Samples: {val}"
        return f"Count Result: {val}"

    # Chart queries
    if "pie" in q:   return question.replace("generate", "").replace("pie chart", "").strip().capitalize() + " — Pie Chart"
    if "bar" in q:   return question.replace("generate", "").replace("bar chart", "").strip().capitalize() + " — Bar Chart"
    if "line" in q:  return question.replace("generate", "").replace("line chart", "").strip().capitalize() + " — Line Chart"

    # List/table queries
    if rows:
        return f"{cols[0] if cols else 'Results'} — {len(rows)} record(s)"

    return question.strip().capitalize()

def generate_metadata(question: str, cols: list, rows: list) -> dict:
    """Ask LLM to generate title and chart type from question + results."""
    sample = rows[:3] if rows else []
    prompt = f"""\
Given this question and query results, return a JSON object with exactly two fields:
- "title": a short 5-10 word human-readable title summarizing the result
- "chart_type": one of "pie", "bar", "line", or null (only if the question explicitly asks for a chart)

Question: {question}
Columns: {cols}
Sample rows: {sample}

Return ONLY valid JSON. Example: {{"title": "Work Orders Per Day", "chart_type": "bar"}}
JSON:"""

    try:
        raw = llm.invoke(prompt)
        raw = raw.strip()
        # Extract JSON from response
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            data = json.loads(match.group(0))
            return {
                "title":      str(data.get("title", question[:50])),
                "chart_type": data.get("chart_type") if data.get("chart_type") in ["pie","bar","line"] else None,
            }
    except Exception as e:
        logger.warning(f"Metadata generation failed: {e}")

    return {"title": question[:50].capitalize(), "chart_type": None}

# ─── STREAM HANDLER ───────────────────────────────────────────────────────────
async def chat_stream(question: str):
    try:
        schema, selected = get_schema_for_question(question)
        logger.info(f"Schema sent to LLM:\n{schema}")   # ← add this line

        logger.info(f"Using {len(selected)} tables for: {question}")
        logger.info(f"Tables selected: {selected}")
 
        prompt = SQL_PROMPT.format(schema=schema, question=question)
        logger.info(f"Prompt size: {len(prompt)} chars")
 
        yield sse("status", {"text": "Generating SQL…"})
        yield sse("tables_used", {"tables": selected})
 
        t0  = time.time()
        raw = llm.invoke(prompt)
        t1  = time.time()
 
        logger.info(f"LLM took {t1-t0:.1f}s | Raw output: {raw[:400]}")
 
        sql = extract_sql(str(raw))
        logger.info(f"Extracted SQL: {sql}")
 
        if not sql or len(sql) < 7:
            yield sse("error", {"text": "Could not generate SQL. Try rephrasing."})
            return
 
        yield sse("sql", {"text": sql, "time": round(t1 - t0, 1)})
        yield sse("status", {"text": "Running query…"})
 
        t2 = time.time()
        rows, cols, err = run_query(sql)
        t3 = time.time()
 
        if err:
            yield sse("error", {"text": f"SQL error: {err}"})
            return



        meta        = generate_metadata(question, cols, rows)
        title       = meta["title"]
        chart_type  = meta["chart_type"]
        chart_title = title if chart_type else None

        yield sse("result", {
            "columns": cols,
            "rows":    rows,
            "count":   len(rows),
            "chart_type":  chart_type,
            "chart_title": chart_title,
            "title":       title, 
            "timings": {
                "sql_gen":  round(t1 - t0, 1),
                "db_query": round(t3 - t2, 1),
                "total":    round(t3 - t0, 1),
            }
        })
 
    except Exception as e:
        logger.error(f"Stream error: {e}", exc_info=True)
        yield sse("error", {"text": str(e)})
 
 
# ─── ENDPOINTS ────────────────────────────────────────────────────────────────
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
        "status":      "ok" if (engine and llm) else "error",
        "model":       "qwen2.5-coder:7b",
        "total_tables": len(_all_tables),
        "tables":      _all_tables,
    }
 
@app.get("/tables")
def list_tables():
    return {"total": len(_all_tables), "tables": _all_tables}
 
@app.get("/test/speed")
def test_speed():
    t0 = time.time()
    out = llm.invoke("Return only: SELECT 1")
    t1 = time.time()
    return {"elapsed_seconds": round(t1 - t0, 2), "output": out}
 
@app.get("/debug/schema")
def debug_schema(question: str = "How many projects are there?"):
    schema, selected = get_schema_for_question(question)
    return {"tables_selected": selected, "schema": schema, "chars": len(schema)}
 
@app.get("/debug/prompt")
def debug_prompt(question: str = "How many projects are there?"):
    schema, selected = get_schema_for_question(question)
    prompt = SQL_PROMPT.format(schema=schema, question=question)
    return {"tables_selected": selected, "chars": len(prompt), "prompt": prompt}
 
 
if __name__ == "__main__":
    uvicorn.run("backend:app", host="0.0.0.0", port=8000, reload=True)