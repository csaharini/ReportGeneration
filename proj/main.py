import json, os, secrets, urllib.parse
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, Response, JSONResponse
from fastapi import HTTPException
from starlette.middleware.sessions import SessionMiddleware
import config  # Loads local .env values before database modules are imported.
import engine
import project_lookup
import auth

HERE = os.path.dirname(os.path.abspath(__file__))

app = FastAPI(title="Trailer Certification Report Generator")
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("AUTH_SESSION_SECRET", secrets.token_urlsafe(48)),
    session_cookie="trailer_report_session",
    max_age=60 * 60 * 12,
    same_site="lax",
    https_only=os.getenv("AUTH_COOKIE_SECURE", "0").lower() in ("1", "true", "yes"),
)


def require_user(request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Sign in is required.")
    try:
        user = auth.get_user(user_id)
    except auth.AuthConfigurationError:
        raise HTTPException(status_code=503, detail="Authentication service is unavailable.")
    if not user:
        request.session.clear()
        raise HTTPException(status_code=401, detail="Your session has expired. Sign in again.")
    return user

@app.get("/")
def index(): return FileResponse("static/index.html")

@app.get("/api/schema")
def schema(request: Request):
    require_user(request)
    return engine.schema()


@app.get("/api/auth/me")
def current_user(request: Request):
    return {"user": require_user(request)}


@app.post("/api/auth/signup")
async def signup(request: Request):
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid signup request.")
    try:
        user = auth.create_user(payload.get("display_name"), payload.get("email"), payload.get("password"))
    except auth.AuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except auth.AuthConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    request.session.clear()
    request.session["user_id"] = user["id"]
    return {"user": user}


@app.post("/api/auth/login")
async def login(request: Request):
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid login request.")
    try:
        user = auth.authenticate(payload.get("email"), payload.get("password"))
    except auth.AuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc))
    except auth.AuthConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    request.session.clear()
    request.session["user_id"] = user["id"]
    return {"user": user}


@app.post("/api/auth/logout")
def logout(request: Request):
    request.session.clear()
    return {"ok": True}

@app.get("/api/project-by-rae/{rae_id}")
def project_by_rae(rae_id: str, request: Request):
    """Read-only RAE/subproject lookup used to prefill the project name."""
    require_user(request)
    try:
        result = project_lookup.find_project(rae_id)
    except project_lookup.LookupConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception:
        # Do not reveal host, credentials, or internal database details to a browser.
        raise HTTPException(status_code=502, detail="Project lookup is temporarily unavailable.")
    if not result:
        raise HTTPException(status_code=404, detail="No project was found for this RAE ID.")
    return JSONResponse(result)

@app.get("/api/template")
def template(request: Request):
    require_user(request)
    pdf, _ = engine.build(template=True)
    return Response(pdf, media_type="application/pdf", headers={"Content-Disposition": 'attachment; filename="Trailer_Report_TEMPLATE.pdf"'})

@app.get("/api/template/word")
def template_word(request: Request):
    require_user(request)
    word_path = os.path.join(HERE, "assets", "template_word.docx")
    if not os.path.exists(word_path):
        raise HTTPException(status_code=404, detail="Word template not found.")
    with open(word_path, "rb") as f:
        content = f.read()
    return Response(content, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document", headers={"Content-Disposition": 'attachment; filename="Trailer_Report_TEMPLATE.docx"'})

@app.post("/api/generate")
async def generate(request: Request):
    require_user(request)
    form = await request.form()
    p = json.loads(form["payload"])
    images = {}
    for k, v in form.items():
        if k.startswith("img__") and hasattr(v, "read"):
            b = await v.read()
            if b: images[k[5:]] = b
    output = p.get("output", "pdf")
    data, selected, layout = p.get("data", {}), p.get("selected"), p.get("layout", {})
    extras, removed = p.get("extra_images", {}), p.get("removed_images", [])
    stem = data.get("rae_no") or "Trailer"
    if output == "word":
        content, warns = engine.build_word(data, images, selected, layout, extras, removed)
        name = stem + "_Certification_Report.docx"
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    else:
        content, warns = engine.build(data, images, selected, layout=layout, extras=extras, removed=removed)
        name = stem + "_Certification_Report.pdf"
        media_type = "application/pdf"
    return Response(content, media_type=media_type, headers={
        "Content-Disposition": f'attachment; filename="{name}"',
        "X-Warnings": urllib.parse.quote(json.dumps(warns)),
        "Access-Control-Expose-Headers": "X-Warnings, Content-Disposition"})
