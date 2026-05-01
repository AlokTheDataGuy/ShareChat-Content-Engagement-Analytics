from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.core.database import query, get_connection
import sqlite3

router = APIRouter(prefix="/query", tags=["query"])

BLOCKED = ["drop", "delete", "insert", "update", "alter", "create", "attach", "detach", "pragma"]


class QueryRequest(BaseModel):
    sql: str


@router.post("/execute")
def execute_query(req: QueryRequest):
    sql_lower = req.sql.strip().lower()
    for word in BLOCKED:
        if sql_lower.startswith(word) or f" {word} " in sql_lower:
            raise HTTPException(status_code=400, detail=f"Statement type '{word}' is not allowed.")
    try:
        rows = query(req.sql)
        return {"rows": rows, "count": len(rows)}
    except sqlite3.Error as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/tables")
def list_tables():
    rows = query("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    return [r["name"] for r in rows]


@router.get("/schema/{table}")
def get_schema(table: str):
    rows = query(f"PRAGMA table_info({table})")
    return rows
