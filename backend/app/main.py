from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import overview, users, content, monetisation, retention, ab_test, language, query

app = FastAPI(title="ShareChat Analytics API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://localhost:\d+",
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(overview.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(content.router, prefix="/api")
app.include_router(monetisation.router, prefix="/api")
app.include_router(retention.router, prefix="/api")
app.include_router(ab_test.router, prefix="/api")
app.include_router(language.router, prefix="/api")
app.include_router(query.router, prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok"}
