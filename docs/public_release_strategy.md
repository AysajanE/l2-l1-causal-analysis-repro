# Public Release Strategy for Reproducible Manuscripts

Last updated: 2025-11-20

Goal: Publish only the artifacts needed for peer-review reproducibility while keeping the full research repo private. We will create minimal, outlet-specific public repos (arXiv, Management Science) with clean provenance, stable DOIs, and clear run instructions.

---

## 1) Repo Roles
- **Private root repo (this):** Full history, heavy/intermediate data, exploratory work, CI, QA, all tests. Stays private/internal.
- **Public repro repos (one per outlet):** `project-a-manuscripts/management-science` and `project-a-manuscripts/arxiv`. Each contains only what reviewers need to reproduce the published results.

---

## 2) Source Freeze & Provenance
1. In the root repo, cut a release tag after tests pass (e.g., `v1.0.0-repro`).  
2. Record the source commit SHA in each public repo (README + `CITATION.cff`) as “Source provenance”.  
3. Keep deterministic outputs (figures/tables) generated from that tag.

---

## 3) Build Curated Public Repos
Workflow (per outlet):
1. Start from a clean worktree/clone to avoid stray files.  
2. Copy in only:
   - Minimal entrypoint scripts/notebooks to run end-to-end.
   - Clean configs (no secrets) and env files (`requirements.txt` / `environment.yml`).
   - Necessary lightweight derived data (small Parquet/CSV) for reproducibility.
   - Final figures/tables included in the manuscript.
   - Tests that validate the main claims (smoke tests with key effect sizes).
   - Docs: `README`, `DATA_AVAILABILITY.md`, `LICENSE`, `CITATION.cff`, `Makefile` (or `justfile`) with standard targets.
3. Exclude:
   - Raw data; heavy intermediates; exploratory notebooks; private notes.
   - Secrets/tokens; internal CI configs; unrelated scripts.
4. Add a strict `.gitignore` covering data dumps, build artifacts, logs.  
5. Commit in the new repo; do **not** import full history from the root.

---

## 4) Size & LFS
- Aim to keep files <100 MB and total repo size modest.  
- If unavoidable, track large binaries with `git lfs track "*.parquet"` (but prefer smaller curated datasets).  
- Bundle many small files into ZIPs with an internal README describing contents.  
- If data cannot be redistributed, use scripted download steps with checksums instead of bundling.

---

## 5) Licensing & Attribution
- Code: MIT.  
- Text/figures: CC BY 4.0 (state explicitly).  
- Mixed-license note in README if both apply.  
- Include `LICENSE` and `CITATION.cff` in each public repo.  
- List third-party data licenses and any access restrictions in `DATA_AVAILABILITY.md`.

---

## 6) Determinism & Validation
- Provide a `Makefile` with targets: `env`, `data`, `figures`, `tables`, `tests`, `all`.  
- Pin versions (hash-pinned `requirements.txt` or `environment.yml`), set random seeds, and document hardware/OS assumptions and runtimes.  
- Include smoke tests asserting headline numbers (e.g., main effect estimates) to catch drift.

---

## 7) Zenodo & DOI Workflow
1. For each public repo, keep a `.zenodo.json` (cleaned of TODOs).  
2. Create a GitHub release (tag matches `version` in `.zenodo.json`).  
3. Zenodo mints a version DOI + concept DOI.  
4. Add DOI badge to README; cite the concept DOI, mention the version DOI in release notes.  
5. If any single deposit >50 GB or >100 files, prepare a draft and request a Zenodo quota increase (up to 200 GB).

---

## 8) Data Availability Model
- **Preferred:** Provide small derived datasets needed to run the pipelines + scripts that download raw data with checksums.  
- If redistribution is allowed and size is small, bundle derived data directly.  
- If embargoed data are needed, provide stubs and instructions; keep actual data out of the repo.

---

## 9) Security & PII Hygiene
- Run secret scan (`gitleaks`/`git secrets`) and PII sweep on each public repo before push.  
- Manually review configs for tokens/endpoints.  
- Remove `.env` files; provide `.env.example` if needed.

---

## 10) Release Checklist (per outlet repo)
- [ ] Fresh clone/worktree; curated contents only.  
- [ ] `.gitignore` excludes raw/intermediate data and build artifacts.  
- [ ] `README`, `DATA_AVAILABILITY.md`, `LICENSE`, `CITATION.cff`, `.zenodo.json`, `Makefile`, env files present.  
- [ ] Provenance noted (root tag + SHA).  
- [ ] Tests/smoke checks pass; key numbers validated.  
- [ ] No secrets/PII; secret scan clean.  
- [ ] GitHub release created; Zenodo DOI minted; README badge updated.  
- [ ] Tag pushed; archive snapshot stored.

---

## 11) Next Actions
- Decide data redistribution vs. fetch-on-demand.  
- For each outlet, build the curated folder, add meta files, and run the release checklist.  
- Push to GitHub (public or reviewer-only as needed), then create the Zenodo-linked release.
