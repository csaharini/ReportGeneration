import json, os, secrets, urllib.parse
from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.responses import RedirectResponse, Response, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi import HTTPException
from starlette.middleware.sessions import SessionMiddleware
import config  # Loads local .env values before database modules are imported.
import engine
import project_lookup
import auth
import standards_library
import materials_library

HERE = os.path.dirname(os.path.abspath(__file__))
AVATAR_DIR = os.path.join(HERE, "uploads", "avatars")
os.makedirs(AVATAR_DIR, exist_ok=True)


def _enabled(value):
    return str(value or "").strip().lower() in ("1", "true", "yes", "on")


_environment = os.getenv("APP_ENV", "development").strip().lower()
_production = _environment in {"production", "prod"}
_configured_secret = os.getenv("AUTH_SESSION_SECRET", "").strip()

# A random development secret is convenient locally, but a deployment must use
# a stable, private secret. Otherwise sessions could be forged or invalidated
# whenever the service restarts.
if not _configured_secret or _configured_secret == "replace-with-a-long-random-secret":
    if _production:
        raise RuntimeError("AUTH_SESSION_SECRET must be set in production.")
    _configured_secret = secrets.token_urlsafe(48)
elif len(_configured_secret) < 32:
    raise RuntimeError("AUTH_SESSION_SECRET must contain at least 32 characters.")

_secure_cookie = _enabled(os.getenv("AUTH_COOKIE_SECURE", "1" if _production else "0"))
if _production and not _secure_cookie:
    raise RuntimeError("AUTH_COOKIE_SECURE must be enabled in production.")

app = FastAPI(title="Trailer Certification Report Generator")
app.add_middleware(
    SessionMiddleware,
    secret_key=_configured_secret,
    session_cookie="trailer_report_session",
    max_age=60 * 60 * 12,
    # SessionMiddleware cookies are always HttpOnly. Strict blocks the browser
    # from sending this cookie with cross-site navigation and requests.
    same_site="strict",
    https_only=_secure_cookie,
)
app.mount("/avatars", StaticFiles(directory=AVATAR_DIR), name="avatars")


def _csrf_token(request: Request):
    token = request.session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        request.session["csrf_token"] = token
    return token


def require_csrf(request: Request):
    expected = request.session.get("csrf_token")
    supplied = request.headers.get("X-CSRF-Token", "")
    if not expected or not secrets.compare_digest(str(expected), supplied):
        raise HTTPException(status_code=403, detail="Invalid or missing CSRF token.")


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("Permissions-Policy", "camera=(), geolocation=(), microphone=()")
    # The page contains inline styling and scripts, so these are allowed while
    # all other script/style sources remain restricted to this application.
    response.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'; object-src 'none'; "
        "frame-src 'self' blob:; img-src 'self' data: blob:; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'",
    )
    if request.url.path.startswith("/api/"):
        response.headers.setdefault("Cache-Control", "no-store")
    if _secure_cookie:
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    return response


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

@app.get("/", include_in_schema=False)
def index():
    """Open the Next.js application; FastAPI remains the secured API service."""
    return RedirectResponse(os.getenv("FRONTEND_ORIGIN", "http://127.0.0.1:3000"))

@app.get("/api/schema")
def schema(request: Request):
    require_user(request)
    return engine.schema()


@app.get("/api/auth/me")
def current_user(request: Request):
    return {"user": require_user(request), "csrf_token": _csrf_token(request)}


@app.put("/api/auth/profile")
async def update_profile(request: Request):
    require_csrf(request)
    user = require_user(request)
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid profile request.")
    try:
        updated = auth.update_user_profile(user["id"], payload)
    except auth.AuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except auth.AuthConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    if not updated:
        raise HTTPException(status_code=400, detail="No valid profile fields provided.")
    request.session.clear()
    request.session["user_id"] = updated["id"]
    return {"user": updated, "csrf_token": _csrf_token(request)}


@app.post("/api/auth/reset-password")
async def reset_password(request: Request):
    require_csrf(request)
    user = require_user(request)
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid password reset request.")
    current_password = payload.get("current_password", "")
    new_password = payload.get("new_password", "")
    if not current_password or not new_password:
        raise HTTPException(status_code=400, detail="Current password and new password are required.")
    try:
        updated = auth.reset_password(user["id"], current_password, new_password)
    except auth.AuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except auth.AuthConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    if not updated:
        raise HTTPException(status_code=400, detail="Password reset failed.")
    request.session.clear()
    request.session["user_id"] = updated["id"]
    return {"user": updated, "csrf_token": _csrf_token(request)}


@app.post("/api/auth/avatar")
async def upload_avatar(request: Request):
    require_csrf(request)
    user = require_user(request)
    try:
        form = await request.form()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid avatar upload request.")
    file = form.get("file")
    if not file or not hasattr(file, "read") or not file.filename:
        raise HTTPException(status_code=400, detail="No avatar file provided.")
    try:
        contents = await file.read()
    except Exception:
        raise HTTPException(status_code=400, detail="Failed to read avatar file.")
    content_type = file.content_type or "application/octet-stream"
    try:
        updated = auth.upload_avatar(user["id"], contents, file.filename, content_type)
    except auth.AuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except auth.AuthConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    if not updated:
        raise HTTPException(status_code=400, detail="Avatar upload failed.")
    request.session.clear()
    request.session["user_id"] = updated["id"]
    return {"user": updated, "csrf_token": _csrf_token(request)}


@app.get("/api/auth/csrf")
def csrf_token(request: Request):
    """Issue a same-origin CSRF token for the sign-in and sign-up forms."""
    return {"csrf_token": _csrf_token(request)}


@app.post("/api/auth/signup")
async def signup(request: Request):
    require_csrf(request)
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid signup request.")
    try:
        user = auth.create_user(payload.get("full_name") or payload.get("display_name"), payload.get("email"), payload.get("password"))
    except auth.AuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except auth.AuthConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    request.session.clear()
    request.session["user_id"] = user["id"]
    return {"user": user, "csrf_token": _csrf_token(request)}


@app.post("/api/auth/login")
async def login(request: Request):
    require_csrf(request)
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
    return {"user": user, "csrf_token": _csrf_token(request)}


@app.post("/api/auth/logout")
def logout(request: Request):
    require_csrf(request)
    request.session.clear()
    return {"ok": True, "csrf_token": _csrf_token(request)}

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


@app.get("/api/standards")
def standards(request: Request):
    require_user(request)
    try:
        return {"standards": standards_library.list_standards()}
    except standards_library.StandardsLibraryError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@app.get("/api/standards/{standard_id}/clauses")
def standard_clauses(standard_id: int, request: Request):
    require_user(request)
    try:
        return {"clauses": standards_library.list_clauses(standard_id)}
    except standards_library.StandardsValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except standards_library.StandardsLibraryError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@app.post("/api/standards/manual")
async def save_manual_standard(request: Request):
    require_csrf(request)
    require_user(request)
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid standards-library entry.")
    try:
        return standards_library.save_manual_entry(payload)
    except standards_library.StandardsValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except standards_library.StandardsLibraryError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@app.get("/api/materials")
def materials(request: Request):
    require_user(request)
    try:
        return {"materials": materials_library.list_materials()}
    except materials_library.MaterialsLibraryError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@app.post("/api/materials/manual")
async def save_manual_material(request: Request):
    require_csrf(request)
    require_user(request)
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid material-library entry.")
    try:
        return {"material": materials_library.save_manual_material(payload)}
    except materials_library.MaterialsValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except materials_library.MaterialsLibraryError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

@app.get("/api/template")
def template(request: Request):
    require_user(request)
    pdf, _ = engine.build(template=True)
    return Response(pdf, media_type="application/pdf", headers={"Content-Disposition": 'attachment; filename="Trailer_Report_TEMPLATE.pdf"'})

@app.get("/api/template/word")
def template_word(request: Request):
    require_user(request)
    # Generate this from the current report definition.  A checked-in DOCX
    # becomes stale whenever template fields such as the standards table change.
    content, _ = engine.build_word(template=True)
    return Response(content, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document", headers={"Content-Disposition": 'attachment; filename="Trailer_Report_TEMPLATE.docx"'})

@app.post("/api/generate")
async def generate(request: Request):
    require_csrf(request)
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
    if not isinstance(data, dict):
        data = {}
    standards = p.get("standards", [])
    data["standards"] = standards if isinstance(standards, list) else []
    extras, removed = p.get("extra_images", {}), p.get("removed_images", [])
    stem = data.get("rae_no") or "Trailer"
    if output == "word":
        content, warns = engine.build_word(data, images, selected, layout=layout, extras=extras, removed=removed)
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
