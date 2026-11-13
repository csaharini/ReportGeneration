"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

/* ------------------------------------------------------------------ */
/*  Design tokens (from the dark-technical login design)               */
/*  page #0a2744 · panel #16405c · card #0e3250 · field #16415f        */
/*  border #2f5b75 · coral #f84f63 · text #f3f8f7 · muted #9fb9c4      */
/* ------------------------------------------------------------------ */

const STEPS = [
  ["01", "Project", "Details & material"],
  ["02", "Report", "Scope & evidence"],
  ["03", "Layout", "Document styling"],
  ["04", "Issue", "Preview & export"],
];

const MATERIAL_IDS = new Set(["material", "fu", "fy", "young", "nu", "rho"]);

const GLOBAL_CSS = `
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap');
.rg { font-family: 'Poppins', ui-sans-serif, system-ui, sans-serif; -webkit-font-smoothing: antialiased; }
.rg *:focus-visible { outline: 2px solid #f84f63; outline-offset: 2px; }
.rg select { color-scheme: dark; }
@media (prefers-reduced-motion: reduce) { .rg * { transition: none !important; animation: none !important; } }
`;

const LABEL = "mb-1.5 block text-xs font-medium text-[#b9d0d8]";
const INPUT =
  "w-full rounded-md border border-[#2f5b75] bg-[#16415f] px-3.5 py-3 text-sm text-white placeholder:text-[#8fa9b5] outline-none transition focus:border-[#f84f63] focus:ring-2 focus:ring-[#f84f63]/25 disabled:opacity-60 read-only:opacity-75";
const CARD = "rounded-2xl border border-[#2a5068] bg-[#0e3250] p-5 sm:p-7";
const INSET = "rounded-xl border border-[#2f5b75]/50 bg-[#0a2744]/70 p-4";
const EYEBROW = "text-sm font-medium text-[#f84f63]";

function messageFor(response) {
  return response
    .json()
    .then((body) => body.detail || body.message || "Request failed.")
    .catch(() => "Request failed.");
}

function Shell({ children }) {
  return (
    <div className="rg min-h-screen bg-[#0a2744] text-[#f3f8f7]">
      <style>{GLOBAL_CSS}</style>
      {children}
    </div>
  );
}

function ActionButton({ children, variant = "primary", className = "", ...props }) {
  const styles = {
    primary: "bg-[#f84f63] text-[#0a1f36] hover:bg-[#ff667a]",
    secondary: "border border-[#2f5b75] bg-[#16415f] text-[#f3f8f7] hover:bg-[#1c4d6f]",
    ghost: "border border-[#2f5b75] bg-transparent text-[#c6dce2] hover:bg-white/5",
  };
  return (
    <button
      className={`inline-flex items-center justify-center rounded-md px-5 py-3 text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-50 ${styles[variant]} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}

function Labeled({ label, className = "", children }) {
  return (
    <label className={`block ${className}`}>
      <span className={LABEL}>{label}</span>
      {children}
    </label>
  );
}

function Field({ field, value, onChange, readOnly = false }) {
  const label = `${field.label}${field.unit ? ` (${field.unit})` : ""}`;
  if (field.type === "textarea") {
    return (
      <Labeled label={label}>
        <textarea className={`${INPUT} min-h-28 resize-y`} value={value ?? ""} onChange={(e) => onChange(e.target.value)} readOnly={readOnly} />
      </Labeled>
    );
  }
  if (field.type === "select") {
    return (
      <Labeled label={label}>
        <select className={INPUT} value={value ?? ""} onChange={(e) => onChange(e.target.value)} disabled={readOnly}>
          {field.opts.map((option) => (
            <option key={option} value={option}>{option}</option>
          ))}
        </select>
      </Labeled>
    );
  }
  return (
    <Labeled label={label}>
      <input
        className={INPUT}
        type={field.type === "number" ? "number" : field.type === "date" ? "date" : "text"}
        step={field.type === "number" ? "any" : undefined}
        value={value ?? ""}
        onChange={(e) => onChange(e.target.value)}
        readOnly={readOnly}
      />
    </Labeled>
  );
}

/* ------------------------------------------------------------------ */
/*  Login / sign up                                                    */
/* ------------------------------------------------------------------ */

const AUTH_INPUT =
  "w-full rounded-md border border-[#2f5b75] bg-[#153a57] px-5 py-4 text-base text-white placeholder:text-[#8fa9b5] outline-none transition focus:border-[#f84f63] focus:ring-2 focus:ring-[#f84f63]/25";
const AUTH_LABEL = "mb-2 block text-sm font-medium text-[#f84f63]";

function LoginScreen({ authMode, setAuthMode, authForm, setAuthForm, submit, status, busy, onForgot }) {
  const signup = authMode === "signup";
  const [show, setShow] = useState(false);
  const set = (key) => (event) => setAuthForm((form) => ({ ...form, [key]: event.target.value }));

  return (
    <Shell>
      <main className="grid min-h-screen lg:grid-cols-[minmax(0,.9fr)_minmax(0,1.1fr)] lg:gap-6 lg:p-6 xl:p-9">
        {/* Left: form */}
        <section className="flex flex-col justify-center px-6 py-10 sm:px-12 lg:px-[7%] lg:py-8">
          <div className="mx-auto w-full max-w-[480px] lg:mx-0 lg:max-w-[520px]">
            {/* compact brand shown only when the right panel is hidden */}
            <div className="mb-10 flex items-center gap-3 lg:hidden">
              <img src="/csa_logo.webp" alt="CSA Engineering" className="h-12 w-auto object-contain" />
              <span className="border-l border-[#2f5b75] pl-3 text-lg font-semibold">ReportGenix</span>
            </div>

            <h1 className="text-3xl font-normal tracking-tight sm:text-4xl xl:text-[2.6rem] xl:leading-tight">
              {signup ? "Create your account" : "Login to your account"}
            </h1>

            <div className="mt-8 grid grid-cols-2 rounded-md bg-[#16405c] p-1.5 text-center text-base font-medium sm:mt-10" role="tablist">
              {[["login", "Login"], ["signup", "Sign up"]].map(([mode, text]) => (
                <button
                  key={mode}
                  type="button"
                  role="tab"
                  aria-selected={authMode === mode}
                  onClick={() => setAuthMode(mode)}
                  className={`rounded px-3 py-3 transition ${authMode === mode ? "bg-[#f84f63] font-semibold text-[#0a1f36]" : "text-[#e6f1f0] hover:bg-white/5"}`}
                >
                  {text}
                </button>
              ))}
            </div>

            <h2 className="mt-12 text-3xl font-normal sm:text-4xl">{signup ? "Get started" : "Welcome back"}</h2>
            <p className="mt-2 text-sm text-[#a9c1ca]">{signup ? "Enter your details to create an account." : "Enter your details to log in."}</p>

            <form className="mt-9 space-y-6" onSubmit={submit}>
              {signup && (
                <label className="block">
                  <span className={AUTH_LABEL}>Full name *</span>
                  <input required value={authForm.full_name} onChange={set("full_name")} className={AUTH_INPUT} placeholder="Your full name" autoComplete="name" />
                </label>
              )}
              <label className="block">
                <span className={AUTH_LABEL}>Email address *</span>
                <input required type="email" autoComplete="email" value={authForm.email} onChange={set("email")} className={AUTH_INPUT} placeholder="you@example.com" />
              </label>
              <label className="block">
                <span className={AUTH_LABEL}>Password *</span>
                <div className="relative">
                  <input
                    required
                    minLength={8}
                    type={show ? "text" : "password"}
                    autoComplete={signup ? "new-password" : "current-password"}
                    value={authForm.password}
                    onChange={set("password")}
                    className={`${AUTH_INPUT} pr-20`}
                    placeholder="Enter your password"
                  />
                  <button
                    type="button"
                    onClick={() => setShow((value) => !value)}
                    className="absolute inset-y-0 right-4 text-sm font-medium text-[#f84f63] hover:text-[#ff8393]"
                    aria-label={show ? "Hide password" : "Show password"}
                  >
                    {show ? "Hide" : "Show"}
                  </button>
                </div>
              </label>

              {!signup && (
                <div className="-mt-2 text-right">
                  <button type="button" onClick={onForgot} className="text-sm text-[#c9dede] hover:text-white">
                    Forgot password?
                  </button>
                </div>
              )}

              {status && <p role="alert" className="text-sm text-[#ff8e9c]">{status}</p>}

              <ActionButton type="submit" disabled={busy === "auth"} className="w-full py-4 text-lg">
                {busy === "auth" ? "Please wait…" : signup ? "Create account" : "Log in"}
              </ActionButton>
            </form>
          </div>
        </section>

        {/* Right: brand panel */}
        <aside className="relative hidden min-h-[640px] overflow-hidden rounded-[28px] bg-[#16405c] lg:block">
          <div className="relative z-10 px-10 pt-9 xl:px-14 xl:pt-11">
            <img src="/csa_logo.webp" alt="CSA Engineering" className="h-16 w-auto object-contain xl:h-20" />
            <h2 className="mt-14 text-[clamp(3.2rem,6.2vw,7rem)] font-semibold leading-none tracking-tight text-[#f3f8f7]">ReportGenix</h2>
            <p className="mt-5 text-lg font-light text-[#a9ccc9] xl:text-xl">Engineering Reports Automated</p>
          </div>
          <img
            src="/fea-trailer.webp"
            alt=""
            aria-hidden="true"
            className="pointer-events-none absolute bottom-0 left-0 h-[62%] w-full select-none object-cover object-left-top"
          />
        </aside>
      </main>
    </Shell>
  );
}

/* ------------------------------------------------------------------ */
/*  Material library                                                   */
/* ------------------------------------------------------------------ */

function MaterialEditor({ catalog, mode, setMode, selectedId, setSelectedId, data, setData, materialMeta, setMaterialMeta, status }) {
  const selected = catalog.find((item) => String(item.id) === String(selectedId));
  const num = (id, label, unit) => ({ id, label, unit, type: "number" });
  const materialFields = [
    { id: "material", label: "Material", type: "text" },
    num("fu", "Tensile strength", "MPa"),
    num("fy", "Yield strength", "MPa"),
    num("young", "Young's modulus", "GPa"),
    num("nu", "Poisson's ratio"),
    num("rho", "Density", "kg/m3"),
  ];
  const apply = (material) => {
    setSelectedId(material.id);
    setData((current) => ({
      ...current,
      material: material.grade,
      fu: material.tensile_mpa ?? "",
      fy: material.yield_mpa ?? "",
      young: material.youngs_modulus_gpa ?? "",
      nu: material.poisson_ratio ?? "",
      rho: material.density_kg_m3 ?? "",
    }));
    setMaterialMeta({
      material_type: material.material_type || "",
      category: material.category || "steel",
      source_standard_id: material.source_standard_id || "",
      notes: material.notes || "",
    });
  };
  const meta = (key) => (event) => setMaterialMeta((value) => ({ ...value, [key]: event.target.value }));

  return (
    <section className={CARD}>
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className={EYEBROW}>Material library</p>
          <h2 className="mt-1 text-xl font-semibold text-white">Mechanical properties</h2>
        </div>
        <span className="rounded-full border border-[#77c2bd]/30 bg-[#77c2bd]/10 px-3 py-1 text-xs text-[#bde1dc]">Database linked</span>
      </div>

      <div className="mb-6 grid gap-4 md:grid-cols-[200px_1fr]">
        <Labeled label="Entry type">
          <select className={INPUT} value={mode} onChange={(e) => setMode(e.target.value)}>
            <option value="library">Library</option>
            <option value="manual">Manual / edit</option>
          </select>
        </Labeled>
        {mode === "library" && (
          <Labeled label="Select material grade">
            <select
              className={INPUT}
              value={selectedId}
              onChange={(e) => {
                const next = catalog.find((item) => String(item.id) === e.target.value);
                if (next) apply(next);
              }}
            >
              <option value="">Select a material</option>
              {catalog.map((item) => (
                <option key={item.id} value={item.id}>{item.grade} — {item.material_type}</option>
              ))}
            </select>
          </Labeled>
        )}
      </div>

      {mode === "manual" && (
        <div className={`${INSET} mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3`}>
          <Labeled label="Material type *">
            <input value={materialMeta.material_type} onChange={meta("material_type")} className={INPUT} />
          </Labeled>
          <Labeled label="Category">
            <select value={materialMeta.category} onChange={meta("category")} className={INPUT}>
              <option value="steel">Steel</option>
              <option value="weld_metal">Weld metal</option>
              <option value="bolt">Bolt</option>
            </select>
          </Labeled>
          <Labeled label="Source standard ID">
            <input type="number" value={materialMeta.source_standard_id} onChange={meta("source_standard_id")} className={INPUT} />
          </Labeled>
          <Labeled label="Notes" className="sm:col-span-2 lg:col-span-3">
            <input value={materialMeta.notes} onChange={meta("notes")} className={INPUT} placeholder="Optional material notes" />
          </Labeled>
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {materialFields.map((item) => (
          <Field key={item.id} field={item} value={data[item.id]} readOnly={mode === "library"} onChange={(value) => setData((current) => ({ ...current, [item.id]: value }))} />
        ))}
      </div>

      <p className={`mt-4 text-xs ${status?.error ? "text-[#ff8e9c]" : "text-[#9bc8c6]"}`}>
        {status?.text ||
          (mode === "manual"
            ? "Changes save automatically when the material grade, type, and tensile strength are complete."
            : selected
              ? `${selected.notes || selected.material_type} loaded from the materials library.`
              : "Select a material to populate report values.")}
      </p>
    </section>
  );
}

/* ------------------------------------------------------------------ */
/*  Summary of compliance                                              */
/* ------------------------------------------------------------------ */

function ComplianceEditor({ rows, setRows, catalog, request }) {
  const manualTimers = useRef({});

  const addRow = () =>
    setRows((current) => [
      ...current,
      {
        id: crypto.randomUUID(),
        source: "library",
        conformity: "Full Compliance",
        standardId: "",
        clauseId: "",
        clauses: [],
        standard: "",
        requirement: "",
        manual: { code: "", edition_year: "", standard_title: "", clause_no: "", clause_title: "", requirement_text: "" },
      },
    ]);

  const update = (id, patch) => setRows((current) => current.map((row) => (row.id === id ? { ...row, ...patch } : row)));

  const selectStandard = async (row, standardId) => {
    update(row.id, { standardId, clauseId: "", clauses: [], standard: "", requirement: "", error: "" });
    if (!standardId) return;
    try {
      // request() returns a Response, so read the JSON body before using it
      const response = await request(`/api/standards/${standardId}/clauses`);
      const result = await response.json();
      update(row.id, { clauses: result.clauses || [] });
    } catch (error) {
      update(row.id, { error: error.message });
    }
  };

  const selectClause = (row, clauseId) => {
    const clause = row.clauses.find((item) => String(item.id) === String(clauseId));
    if (!clause) return;
    const code = catalog.find((item) => String(item.id) === String(row.standardId))?.code || "";
    update(row.id, {
      clauseId,
      standard: clause.summary_standard || `${code} - ${clause.clause_no}`,
      requirement: clause.summary_requirement || [clause.title, clause.requirement_text].filter(Boolean).join("\n"),
    });
  };

  const saveManual = async (rowId, manual) => {
    try {
      update(rowId, { saveStatus: "Saving to standards library…", saveError: false });
      const response = await request("/api/standards/manual", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(manual),
      });
      const payload = await response.json();
      update(rowId, {
        standardId: payload.standard.id,
        clauseId: payload.clause.id,
        standard: payload.clause.summary_standard || [manual.code, manual.clause_no].filter(Boolean).join(" - "),
        requirement: payload.clause.summary_requirement || [manual.clause_title, manual.requirement_text].filter(Boolean).join("\n"),
        saveStatus: "Saved to the standards library.",
      });
    } catch (error) {
      update(rowId, { saveStatus: error.message, saveError: true });
    }
  };

  const manualUpdate = (row, key, value) => {
    const manual = { ...row.manual, [key]: value };
    update(row.id, {
      manual,
      standard: [manual.code, manual.clause_no].filter(Boolean).join(" - "),
      requirement: [manual.clause_title, manual.requirement_text].filter(Boolean).join("\n"),
      saveStatus: "Complete code, edition, standard title, clause number and clause title to save.",
      saveError: false,
    });
    window.clearTimeout(manualTimers.current[row.id]);
    if (manual.code && manual.edition_year && manual.standard_title && manual.clause_no && manual.clause_title) {
      manualTimers.current[row.id] = window.setTimeout(() => saveManual(row.id, manual), 850);
    }
  };

  const removeRow = (id) => {
    window.clearTimeout(manualTimers.current[id]);
    setRows((current) => current.filter((item) => item.id !== id));
  };

  return (
    <section className={CARD}>
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className={EYEBROW}>Compliance library</p>
          <h2 className="mt-1 text-xl font-semibold text-white">Summary of compliance</h2>
        </div>
        <ActionButton onClick={addRow} className="w-full sm:w-auto">+ Add standard</ActionButton>
      </div>
      <p className="mb-5 text-sm text-[#b3ced0]">Select database records to build the report summary, or enter a manual row.</p>

      {rows.length === 0 && (
        <div className="rounded-xl border border-dashed border-[#2f5b75] p-6 text-center text-sm text-[#a9c1ca]">
          No standards added yet. Use “Add standard” to create the first row.
        </div>
      )}

      <div className="space-y-4">
        {rows.map((row, index) => (
          <div key={row.id} className={INSET}>
            <div className="mb-4 flex items-center justify-between">
              <span className="text-sm font-medium text-[#80bfbe]">Row {index + 1}</span>
              <button onClick={() => removeRow(row.id)} className="text-sm font-semibold text-[#ff8393] hover:text-[#ffb0ba]">Remove</button>
            </div>

            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-[150px_minmax(0,1fr)_minmax(0,1fr)_190px]">
              <Labeled label="Entry type">
                <select className={INPUT} value={row.source} onChange={(e) => update(row.id, { source: e.target.value })}>
                  <option value="library">Library</option>
                  <option value="manual">Manual</option>
                </select>
              </Labeled>

              {row.source === "library" ? (
                <>
                  <Labeled label="Standard">
                    <select className={INPUT} value={row.standardId} onChange={(e) => selectStandard(row, e.target.value)}>
                      <option value="">Select a standard</option>
                      {catalog.map((item) => (
                        <option key={item.id} value={item.id}>
                          {item.code}{item.edition_year ? ` (${item.edition_year})` : ""} — {item.title}
                        </option>
                      ))}
                    </select>
                  </Labeled>
                  <Labeled label="Clause">
                    <select disabled={!row.standardId} className={INPUT} value={row.clauseId} onChange={(e) => selectClause(row, e.target.value)}>
                      <option value="">Select a clause</option>
                      {row.clauses.map((item) => (
                        <option key={item.id} value={item.id}>{item.clause_no ? `${item.clause_no} — ` : ""}{item.title}</option>
                      ))}
                    </select>
                  </Labeled>
                </>
              ) : (
                <>
                  <Labeled label="Standard code *">
                    <input value={row.manual.code} onChange={(e) => manualUpdate(row, "code", e.target.value)} className={INPUT} />
                  </Labeled>
                  <Labeled label="Clause number *">
                    <input value={row.manual.clause_no} onChange={(e) => manualUpdate(row, "clause_no", e.target.value)} className={INPUT} />
                  </Labeled>
                </>
              )}

              <Labeled label="Conformity" className="sm:col-span-2 xl:col-span-1">
                <select className={INPUT} value={row.conformity} onChange={(e) => update(row.id, { conformity: e.target.value })}>
                  <option>Full Compliance</option>
                  <option>Partial Compliance</option>
                  <option>Not Compliant</option>
                  <option>Not Assessed</option>
                </select>
              </Labeled>
            </div>

            {row.error && <p className="mt-3 text-xs text-[#ff8e9c]">{row.error}</p>}

            {row.source === "manual" && (
              <div className="mt-4 grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
                <Labeled label="Edition *">
                  <input value={row.manual.edition_year} onChange={(e) => manualUpdate(row, "edition_year", e.target.value)} className={INPUT} placeholder="e.g. 2002" />
                </Labeled>
                <Labeled label="Standard title *" className="xl:col-span-2">
                  <input value={row.manual.standard_title} onChange={(e) => manualUpdate(row, "standard_title", e.target.value)} className={INPUT} />
                </Labeled>
                <Labeled label="Clause title *">
                  <input value={row.manual.clause_title} onChange={(e) => manualUpdate(row, "clause_title", e.target.value)} className={INPUT} />
                </Labeled>
                <Labeled label="Compliance requirement" className="xl:col-span-2">
                  <input value={row.manual.requirement_text} onChange={(e) => manualUpdate(row, "requirement_text", e.target.value)} className={INPUT} />
                </Labeled>
                <p className={`text-xs sm:col-span-2 xl:col-span-3 ${row.saveError ? "text-[#ff8e9c]" : "text-[#9bc8c6]"}`}>
                  {row.saveStatus || "Manual entries are saved automatically."}
                </p>
              </div>
            )}

            {row.standard && (
              <div className="mt-4 grid gap-3 rounded-lg border border-[#77c2bd]/20 bg-[#77c2bd]/5 p-3 text-sm md:grid-cols-2">
                <p><b className="font-semibold text-[#99cfca]">Standard:</b> {row.standard}</p>
                <p className="whitespace-pre-line"><b className="font-semibold text-[#99cfca]">Requirement:</b> {row.requirement}</p>
              </div>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}

/* ------------------------------------------------------------------ */
/*  Report sections                                                    */
/* ------------------------------------------------------------------ */

function SectionEditor({ section, data, setData, files, setFiles, selected, setSelected, children }) {
  const enabled = selected.includes(section.id);
  return (
    <section className={`overflow-hidden rounded-2xl border ${enabled ? "border-[#2a5068] bg-[#0e3250]" : "border-[#2a5068]/50 bg-[#0b2b47]/60 opacity-70"}`}>
      <header className="flex flex-wrap items-center justify-between gap-3 border-b border-[#2a5068]/60 px-5 py-4">
        <div>
          <h3 className="font-semibold text-white">{section.title}</h3>
          <p className="mt-0.5 text-xs text-[#9bbcc0]">Report section</p>
        </div>
        <button
          onClick={() => setSelected((current) => (enabled ? current.filter((id) => id !== section.id) : [...current, section.id]))}
          aria-pressed={enabled}
          className={`rounded-full px-4 py-1.5 text-xs font-semibold transition ${enabled ? "bg-[#77c2bd]/15 text-[#afdfd8]" : "bg-white/5 text-[#b8cdcf] hover:bg-white/10"}`}
        >
          {enabled ? "Included" : "Excluded"}
        </button>
      </header>

      {enabled && (
        <div className="space-y-5 p-5 sm:p-6">
          {children}
          {section.fields.length > 0 && (
            <div className="grid gap-4 md:grid-cols-2">
              {section.fields.map((field) => (
                <Field key={field.id} field={field} value={data[field.id]} onChange={(value) => setData((current) => ({ ...current, [field.id]: value }))} />
              ))}
            </div>
          )}
          {section.images.length > 0 && (
            <div className="grid gap-4 md:grid-cols-2">
              {section.images.map((image) => (
                <label key={image.id} className="block rounded-xl border border-dashed border-[#2f5b75] bg-[#0a2744]/60 p-4">
                  <span className="mb-2 block text-sm font-medium text-[#d3e9e7]">{image.label}</span>
                  <input
                    type="file"
                    accept="image/*"
                    className="block w-full text-xs text-[#a8c9ca] file:mr-3 file:cursor-pointer file:rounded-md file:border-0 file:bg-[#f84f63] file:px-3 file:py-2 file:text-xs file:font-semibold file:text-[#0a1f36]"
                    onChange={(e) => setFiles((current) => ({ ...current, [image.id]: e.target.files?.[0] || null }))}
                  />
                  {files[image.id] && <p className="mt-2 break-all text-xs text-[#8fd0c8]">Attached: {files[image.id].name}</p>}
                </label>
              ))}
            </div>
          )}
        </div>
      )}
    </section>
  );
}

/* ------------------------------------------------------------------ */
/*  App                                                                */
/* ------------------------------------------------------------------ */

export default function ReportGenix() {
  const [ready, setReady] = useState(false);
  const [user, setUser] = useState(null);
  const [csrf, setCsrf] = useState("");
  const [authMode, setAuthMode] = useState("login");
  const [authForm, setAuthForm] = useState({ full_name: "", email: "", password: "" });
  const [authStatus, setAuthStatus] = useState("");
  const [schema, setSchema] = useState(null);
  const [data, setData] = useState({});
  const [standardsCatalog, setStandardsCatalog] = useState([]);
  const [materialsCatalog, setMaterialsCatalog] = useState([]);
  const [standards, setStandards] = useState([]);
  const [selected, setSelected] = useState([]);
  const [files, setFiles] = useState({});
  const [layout, setLayout] = useState({ heading_align: "left", text_align: "justify", image_align: "center", caption_position: "below", caption_align: "center" });
  const [materialMode, setMaterialMode] = useState("library");
  const [selectedMaterialId, setSelectedMaterialId] = useState("");
  const [materialMeta, setMaterialMeta] = useState({ material_type: "", category: "steel", source_standard_id: "", notes: "" });
  const [materialStatus, setMaterialStatus] = useState(null);
  const [step, setStep] = useState(1);
  const [previewUrl, setPreviewUrl] = useState("");
  const [busy, setBusy] = useState("");

  const request = useCallback(
    async (path, options = {}) => {
      const method = (options.method || "GET").toUpperCase();
      const headers = new Headers(options.headers || {});
      if (method !== "GET" && method !== "HEAD" && csrf) headers.set("X-CSRF-Token", csrf);
      const response = await fetch(path, { ...options, headers, cache: options.cache || "no-store" });
      if (!response.ok) throw new Error(await messageFor(response));
      return response;
    },
    [csrf]
  );

  const loadStudio = useCallback(async () => {
    const [schemaResponse, standardsResponse, materialsResponse] = await Promise.all([request("/api/schema"), request("/api/standards"), request("/api/materials")]);
    const [nextSchema, nextStandards, nextMaterials] = await Promise.all([schemaResponse.json(), standardsResponse.json(), materialsResponse.json()]);
    setSchema(nextSchema);
    setStandardsCatalog(nextStandards.standards || []);
    setMaterialsCatalog(nextMaterials.materials || []);
    setData((current) =>
      Object.fromEntries(
        nextSchema.general.map((field) => [field.id, current[field.id] ?? field.default ?? (field.type === "date" ? new Date().toISOString().slice(0, 10) : "")])
      )
    );
    setSelected(nextSchema.sections.map((section) => section.id));
  }, [request]);

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const csrfResponse = await fetch("/api/auth/csrf", { cache: "no-store" });
        const csrfPayload = await csrfResponse.json();
        if (!active) return;
        setCsrf(csrfPayload.csrf_token || "");
        const meResponse = await fetch("/api/auth/me", { cache: "no-store" });
        if (meResponse.ok) {
          const mePayload = await meResponse.json();
          setUser(mePayload.user);
          setCsrf(mePayload.csrf_token || csrfPayload.csrf_token || "");
        }
      } catch (error) {
        if (active) setAuthStatus("Could not connect to the report service.");
      } finally {
        if (active) setReady(true);
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (user && csrf) loadStudio().catch((error) => setAuthStatus(error.message));
  }, [user, csrf, loadStudio]);

  useEffect(() => {
    window.scrollTo({ top: 0 });
  }, [step]);

  useEffect(() => {
    if (materialMode !== "manual" || !data.material || !materialMeta.material_type || !data.fu || !csrf) return;
    const timer = window.setTimeout(async () => {
      try {
        setMaterialStatus({ text: "Saving material changes…" });
        const response = await request("/api/materials/manual", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            grade: data.material,
            material_type: materialMeta.material_type,
            tensile_mpa: data.fu,
            yield_mpa: data.fy,
            youngs_modulus_gpa: data.young,
            poisson_ratio: data.nu,
            density_kg_m3: data.rho,
            ...materialMeta,
          }),
        });
        const payload = await response.json();
        setMaterialsCatalog((current) => {
          const next = current.filter((item) => item.id !== payload.material.id);
          return [...next, payload.material].sort((a, b) => a.grade.localeCompare(b.grade));
        });
        setSelectedMaterialId(payload.material.id);
        setMaterialStatus({ text: "Material saved to the library." });
      } catch (error) {
        setMaterialStatus({ text: error.message, error: true });
      }
    }, 850);
    return () => window.clearTimeout(timer);
  }, [materialMode, data.material, data.fu, data.fy, data.young, data.nu, data.rho, materialMeta, csrf, request]);

  const submitAuth = async (event) => {
    event.preventDefault();
    setAuthStatus("");
    setBusy("auth");
    try {
      const response = await request(authMode === "signup" ? "/api/auth/signup" : "/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(authForm),
      });
      const payload = await response.json();
      setUser(payload.user);
      setCsrf(payload.csrf_token || csrf);
      setAuthForm((form) => ({ ...form, password: "" }));
    } catch (error) {
      setAuthStatus(error.message);
    } finally {
      setBusy("");
    }
  };

  const logout = async () => {
    try {
      await request("/api/auth/logout", { method: "POST" });
    } finally {
      setUser(null);
      setSchema(null);
      setStandards([]);
      setFiles({});
      setPreviewUrl("");
      setStep(1);
    }
  };

  const reportRows = useMemo(
    () => standards.filter((row) => row.standard || row.requirement).map(({ standard, requirement, conformity }) => ({ standard, requirement, conformity })),
    [standards]
  );

  const generate = async (output) => {
    setBusy(output);
    try {
      const form = new FormData();
      form.append(
        "payload",
        JSON.stringify({
          data: { ...data, standards: reportRows },
          standards: reportRows,
          selected,
          layout,
          extra_images: {},
          removed_images: [],
          output: output === "preview" ? "pdf" : output,
        })
      );
      Object.entries(files).forEach(([key, file]) => {
        if (file) form.append(`img__${key}`, file);
      });
      const response = await request("/api/generate", { method: "POST", body: form });
      const blob = await response.blob();
      if (output === "preview") {
        if (previewUrl) URL.revokeObjectURL(previewUrl);
        setPreviewUrl(URL.createObjectURL(blob));
      } else {
        const extension = output === "word" ? "docx" : "pdf";
        const link = document.createElement("a");
        link.href = URL.createObjectURL(blob);
        link.download = `${data.rae_no || "Trailer"}_Certification_Report.${extension}`;
        link.click();
        window.setTimeout(() => URL.revokeObjectURL(link.href), 1000);
      }
    } catch (error) {
      window.alert(error.message);
    } finally {
      setBusy("");
    }
  };

  const downloadTemplate = async (format) => {
    try {
      const response = await request(format === "word" ? "/api/template/word" : "/api/template");
      const blob = await response.blob();
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = format === "word" ? "Trailer_Report_TEMPLATE.docx" : "Trailer_Report_TEMPLATE.pdf";
      link.click();
      window.setTimeout(() => URL.revokeObjectURL(link.href), 1000);
    } catch (error) {
      window.alert(error.message);
    }
  };

  if (!ready) {
    return (
      <Shell>
        <main className="grid min-h-screen place-items-center">
          <p className="animate-pulse text-sm font-medium text-[#b9dcda]">Loading ReportGenix…</p>
        </main>
      </Shell>
    );
  }

  if (!user) {
    return (
      <LoginScreen
        authMode={authMode}
        setAuthMode={(mode) => { setAuthMode(mode); setAuthStatus(""); }}
        authForm={authForm}
        setAuthForm={setAuthForm}
        submit={submitAuth}
        status={authStatus}
        busy={busy}
        onForgot={() => setAuthStatus("Password reset isn't available yet. Contact your administrator.")}
      />
    );
  }

  if (!schema) {
    return (
      <Shell>
        <main className="grid min-h-screen place-items-center px-6 text-center">
          <p className="animate-pulse text-sm font-medium text-[#b9dcda]">{authStatus || "Loading report workspace…"}</p>
        </main>
      </Shell>
    );
  }

  const generalFields = schema.general.filter((field) => !MATERIAL_IDS.has(field.id));
  const reportSections = schema.sections.filter((section) => section.id !== "summary");
  const layoutOptions = [
    ["heading_align", "Heading alignment", ["left", "center", "right"]],
    ["text_align", "Body alignment", ["justify", "left", "center", "right"]],
    ["image_align", "Image alignment", ["center", "left", "right"]],
    ["caption_position", "Caption placement", ["below", "above"]],
    ["caption_align", "Caption alignment", ["center", "left", "right"]],
  ];

  return (
    <Shell>
      <header className="sticky top-0 z-30 border-b border-[#2a5068]/60 bg-[#0a2744]/95 px-4 py-3 backdrop-blur sm:px-6 lg:px-10">
        <div className="mx-auto flex max-w-[1600px] items-center gap-3">
          <img src="/csa_logo.webp" alt="CSA Engineering" className="h-9 w-auto" />
          <span className="border-l border-[#2f5b75] pl-3 text-base font-semibold">ReportGenix</span>
          <div className="ml-auto flex items-center gap-2">
            <span className="hidden max-w-[220px] truncate text-sm text-[#b9d2d3] md:inline">{user.full_name || user.email}</span>
            <ActionButton variant="ghost" onClick={() => downloadTemplate("pdf")} className="hidden !px-4 !py-2 sm:inline-flex">Blank PDF</ActionButton>
            <ActionButton variant="ghost" onClick={logout} className="!px-4 !py-2">Sign out</ActionButton>
          </div>
        </div>
      </header>

      <div className="mx-auto max-w-[1600px] px-4 py-6 sm:px-6 sm:py-8 lg:px-10">
        <section className="relative mb-6 overflow-hidden rounded-3xl bg-[#16405c] px-6 py-8 sm:mb-8 sm:px-10 sm:py-10">
          <img src="/fea-trailer.webp" alt="" aria-hidden="true" className="pointer-events-none absolute inset-y-0 right-0 hidden h-full w-1/2 select-none object-cover object-left opacity-40 md:block" />
          <div className="relative max-w-2xl">
            <p className={EYEBROW}>CSA Engineering</p>
            <h1 className="mt-2 text-3xl font-semibold tracking-tight text-white sm:text-4xl">Trailer Certification Studio</h1>
            <p className="mt-3 text-sm leading-6 text-[#b6d3d4] sm:text-base">
              Build structured compliance reports, attach FEA evidence, and issue a controlled PDF or editable Word document.
            </p>
          </div>
        </section>

        <nav className="mb-6 grid grid-cols-2 gap-3 sm:mb-8 xl:grid-cols-4" aria-label="Report steps">
          {STEPS.map(([number, title, subtitle], index) => {
            const active = step === index + 1;
            return (
              <button
                key={number}
                onClick={() => setStep(index + 1)}
                aria-current={active ? "step" : undefined}
                className={`rounded-xl border p-3.5 text-left transition sm:p-4 ${active ? "border-[#f84f63] bg-[#f84f63] text-[#0a1f36]" : "border-[#2a5068] bg-[#0e3250] text-[#d2e8e6] hover:bg-[#16415f]"}`}
              >
                <span className="text-xs font-semibold opacity-75">{number}</span>
                <span className="mt-0.5 block font-semibold">{title}</span>
                <span className="mt-0.5 hidden text-xs opacity-75 sm:block">{subtitle}</span>
              </button>
            );
          })}
        </nav>

        {step === 1 && (
          <div className="grid gap-6">
            <section className={CARD}>
              <p className={EYEBROW}>Project information</p>
              <h2 className="mt-1 text-xl font-semibold text-white">Report details</h2>
              <div className="mt-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
                {generalFields.map((field) => (
                  <Field key={field.id} field={field} value={data[field.id]} onChange={(value) => setData((current) => ({ ...current, [field.id]: value }))} />
                ))}
              </div>
            </section>
            <MaterialEditor
              catalog={materialsCatalog}
              mode={materialMode}
              setMode={setMaterialMode}
              selectedId={selectedMaterialId}
              setSelectedId={setSelectedMaterialId}
              data={data}
              setData={setData}
              materialMeta={materialMeta}
              setMaterialMeta={setMaterialMeta}
              status={materialStatus}
            />
          </div>
        )}

        {step === 2 && (
          <div className="space-y-6">
            <ComplianceEditor rows={standards} setRows={setStandards} catalog={standardsCatalog} request={request} />
            {reportSections.map((section) => (
              <SectionEditor key={section.id} section={section} data={data} setData={setData} files={files} setFiles={setFiles} selected={selected} setSelected={setSelected}>
                {section.id === "requirements" && <p className="text-sm text-[#b7d1d2]">Requirements are generated from the Summary of Compliance rows above.</p>}
              </SectionEditor>
            ))}
          </div>
        )}

        {step === 3 && (
          <section className={CARD}>
            <p className={EYEBROW}>Report layout</p>
            <h2 className="mt-1 text-xl font-semibold text-white">Document styling</h2>
            <div className="mt-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
              {layoutOptions.map(([key, label, options]) => (
                <Labeled key={key} label={label}>
                  <select className={INPUT} value={layout[key]} onChange={(e) => setLayout((current) => ({ ...current, [key]: e.target.value }))}>
                    {options.map((option) => (
                      <option key={option}>{option}</option>
                    ))}
                  </select>
                </Labeled>
              ))}
            </div>
          </section>
        )}

        {step === 4 && (
          <section className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_340px]">
            <div className={CARD}>
              <p className={EYEBROW}>Ready to issue</p>
              <h2 className="mt-1 text-2xl font-semibold text-white">Review and export</h2>
              <p className="mt-3 max-w-2xl text-sm leading-6 text-[#b6d3d4]">
                Preview uses the same report engine as the final download. Check warnings and attached evidence before issuing the certification.
              </p>
              <div className="mt-7 flex flex-wrap gap-3">
                <ActionButton onClick={() => generate("preview")} disabled={Boolean(busy)} className="flex-1 sm:flex-none">
                  {busy === "preview" ? "Creating preview…" : "Preview PDF"}
                </ActionButton>
                <ActionButton variant="secondary" onClick={() => generate("pdf")} disabled={Boolean(busy)} className="flex-1 sm:flex-none">
                  {busy === "pdf" ? "Creating PDF…" : "Download PDF"}
                </ActionButton>
                <ActionButton variant="secondary" onClick={() => generate("word")} disabled={Boolean(busy)} className="flex-1 sm:flex-none">
                  {busy === "word" ? "Creating Word…" : "Download Word"}
                </ActionButton>
                <ActionButton variant="ghost" onClick={() => downloadTemplate("word")} className="flex-1 sm:flex-none">Blank Word</ActionButton>
              </div>
              {previewUrl && (
                <div className="mt-7 overflow-hidden rounded-xl border border-[#2a5068] bg-[#061d31]">
                  <iframe title="Generated report preview" src={previewUrl} className="h-[70vh] min-h-[420px] w-full lg:h-[720px]" />
                </div>
              )}
            </div>

            <aside className="h-fit rounded-2xl border border-[#2a5068] bg-[#0b2b47] p-6">
              <h3 className="font-semibold text-white">Issue checklist</h3>
              <div className="mt-5 space-y-4 text-sm text-[#bdd6d6]">
                <p><b className="text-[#f84f63]">{selected.length}</b> sections included</p>
                <p><b className="text-[#f84f63]">{reportRows.length}</b> compliance rows</p>
                <p><b className="text-[#f84f63]">{Object.values(files).filter(Boolean).length}</b> evidence files attached</p>
              </div>
              <div className="mt-8 rounded-xl bg-[#77c2bd]/10 p-4 text-xs leading-5 text-[#cbe3df]">
                The certificate includes the standard verification QR and Australia watermark automatically.
              </div>
            </aside>
          </section>
        )}

        <div className="mt-8 flex items-center justify-between gap-3">
          <ActionButton variant="ghost" onClick={() => setStep((value) => Math.max(1, value - 1))} disabled={step === 1}>Back</ActionButton>
          {step < 4 && <ActionButton onClick={() => setStep((value) => Math.min(4, value + 1))}>Continue</ActionButton>}
        </div>
      </div>
    </Shell>
  );
}
