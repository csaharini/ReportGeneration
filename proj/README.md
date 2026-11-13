# Trailer Certification Report Generator

The app now has a Next.js + Tailwind frontend in `../frontend` and a FastAPI
backend in this folder. Run both services during development:

```powershell
# Terminal 1 — API, database access, and document generation
cd proj
pip install -r requirements.txt
uvicorn main:app --reload

# Terminal 2 — Next.js ReportGenix UI
cd frontend
npm install
npm run dev
```

Open `http://127.0.0.1:3000`. Next proxies `/api/*` to FastAPI at
`http://127.0.0.1:8000`; configure `BACKEND_ORIGIN` in `frontend/.env.local`
when the API is elsewhere. The backend root URL redirects to the frontend; set
`FRONTEND_ORIGIN` in its environment when deploying.

Frontend routes:

- `/` — report details only.
- `/projects` — material library and Summary of Compliance.
- `/section/background` (and every other section ID) — that section's fields,
  editable main heading, editable image captions, image placement, and uploads.
- `/layout` — global report layout controls.
- `/issue` — preview and PDF/Word export.

- To enable automatic project lookup, set `RAE_DB_HOST`, `RAE_DB_PORT`, `RAE_DB_NAME`, `RAE_DB_USER`, and `RAE_DB_PASSWORD` on the app server; see `.env.example`.
- Entering an RAE ID looks up `projects.project_id` and fills Project name with `projects.project_name`; it also accepts `subprojects.table_id` when a subproject ID is supplied. Projects without subprojects are supported.
- Sign-up and sign-in use the existing `csareport.users` table. Passwords are bcrypt hashes, and authentication uses an HttpOnly, signed session cookie with `SameSite=Strict` plus CSRF protection for every state-changing request.
- The Summary of Compliance section loads its standard and clause dropdowns from `csareport.standards` and `csareport.standard_clauses`. Select **Manual** to add a reusable entry; completed manual entries are automatically upserted by standard code/edition and clause number. `STANDARDS_DB_*` can point at another MySQL database, or can be omitted to reuse `AUTH_DB_*`.
- The Material library loads grades and mechanical properties from `csareport.materials`. Selecting a grade fills the report's material, tensile/yield strength, Young's modulus, Poisson's ratio, and density. Select **Manual** to upsert a new grade; `MATERIALS_DB_*` is optional and otherwise reuses `AUTH_DB_*`.
- For deployment, set `APP_ENV=production`, a unique random `AUTH_SESSION_SECRET` of at least 32 characters, and serve only through HTTPS. The application then requires HTTPS-only cookies. Set `AUTH_COOKIE_SECURE=1` explicitly if desired; do not use the local-development settings in production.
- Work through the four phases: project details, report content and images, layout, then review/export.
- Use **Preview** to render the actual PDF before downloading it. You can set global text/heading/image placement and override the position and heading placement of each image.
- Download either the controlled-layout PDF or a Word (.docx) companion document.
- "Blank template PDF" downloads the standard template with all placeholders.
- Standard wording lives in engine.py (REQ, ROWS, section builders) - edit there to change the template.
- Template PDF: image headings and the materials table are fillable form fields (type in any PDF reader). Image boxes are blank dashed areas.
- In the app, each image has an editable heading, and material table values start blank.
