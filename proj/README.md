# Trailer Certification Report Generator
pip install -r requirements.txt
uvicorn main:app --reload      # open http://127.0.0.1:8000

- To enable automatic project lookup, set `RAE_DB_HOST`, `RAE_DB_PORT`, `RAE_DB_NAME`, `RAE_DB_USER`, and `RAE_DB_PASSWORD` on the app server; see `.env.example`.
- Entering an RAE ID looks up `projects.project_id` and fills Project name with `projects.project_name`; it also accepts `subprojects.table_id` when a subproject ID is supplied. Projects without subprojects are supported.
- Sign-up and sign-in use the existing `csareport.users` table. Set the `AUTH_DB_*` and `AUTH_SESSION_SECRET` environment variables; enable `AUTH_COOKIE_SECURE=1` when the app is served over HTTPS.
- Work through the four phases: project details, report content and images, layout, then review/export.
- Use **Preview** to render the actual PDF before downloading it. You can set global text/heading/image placement and override the position and heading placement of each image.
- Download either the controlled-layout PDF or a Word (.docx) companion document.
- "Blank template PDF" downloads the standard template with all placeholders.
- Standard wording lives in engine.py (REQ, ROWS, section builders) - edit there to change the template.
- Template PDF: image headings and the materials table are fillable form fields (type in any PDF reader). Image boxes are blank dashed areas.
- In the app, each image has an editable heading, and material table values start blank.
