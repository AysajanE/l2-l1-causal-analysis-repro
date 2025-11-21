# Zenodo Setup Guide (GitHub Integration)

Last updated: 2025-11-20

This project is ready for Zenodo archiving via GitHub releases. Follow these steps to mint a DOI and keep metadata correct.

---

## 1) Prerequisites
- Zenodo account with GitHub linked.
- Admin access to this GitHub repo (needed to enable the Zenodo app).
- Repo contains `.zenodo.json` (already added; update placeholders before release).

---

## 2) Update `.zenodo.json`
File: `.zenodo.json` (repo root). Edit before your first release:
- `creators`: add full names, ORCIDs, affiliations; set `"type": "ProjectMember"`.
- `contributors`: optional; set `"type"` (e.g., Researcher, DataManager).
- `title`, `keywords`, `version`: align with the upcoming Git tag (e.g., `v1.0.0`).
- `license`: keep `mit` for code; if you need CC-BY for docs, note that in description or split deposits.
- `related_identifiers`: add paper DOI or arXiv URL with relation `isSupplementTo`.
- `communities`: add community slug if you want moderation; otherwise remove.
- Remove any remaining `TODO` placeholders.

---

## 3) Enable GitHub → Zenodo
1. Log into Zenodo.
2. Top-right profile → **GitHub**.
3. Click **Sync now** to refresh repos.
4. Toggle this repository **ON**.
5. If the repo is under an org, ensure the Zenodo GitHub app has org access.

Result: Any GitHub release will trigger Zenodo to archive and mint a DOI.

---

## 4) Create the first citable release
1. Update `version` in `.zenodo.json` to match the tag (e.g., `v1.0.0`).
2. Commit `.zenodo.json` and push.
3. Create a GitHub release (tag = same version). Include release notes.
4. Wait ~1–2 minutes; Zenodo will create a record:
   - Versioned DOI (e.g., `10.5281/zenodo.xxxxxxx`)
   - Concept DOI (stable across versions)

---

## 5) Add the DOI badge
After Zenodo mints the DOI, edit `README.md`:
- Replace `PLACEHOLDER_DOI` in the badge with the minted DOI (versioned or concept).
- Keep both concept DOI (for citation) and latest DOI (for specific version) handy in release notes.

Badge pattern:
```
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.xxxxxxx.svg)](https://doi.org/10.5281/zenodo.xxxxxxx)
```

---

## 6) File size and quotas
- Default: ≤50 GB and ≤100 files per deposit.
- Need more? Create a draft, copy its URL, and request a one-time quota increase (up to 200 GB, still ≤100 files).
- Bundle many small files into ZIPs to stay within limits; describe the split in a README inside each ZIP.

---

## 7) Access & licenses
- Access options: `open`, `embargoed`, or `closed`.
- For this repo: code under MIT; docs under CC-BY 4.0. Note in the description if mixed licenses apply.

---

## 8) ORCID and funding
- Ensure each creator has an ORCID in `.zenodo.json`; Zenodo pushes metadata to ORCID after DOI creation.
- Add grant info in `grants` if applicable.

---

## 9) Communities (optional)
- Add the community slug in `.zenodo.json`. Records routed to a community may need moderator approval before becoming public.

---

## 10) Maintenance for future releases
- Update `version` and any metadata changes in `.zenodo.json` before each new GitHub release.
- Create a new GitHub release → Zenodo mints a new version DOI; the concept DOI stays the same.
- Keep `README.md` badge pointing to the concept DOI; mention the specific version DOI in release notes.

---

## 11) Quick checklist before releasing
- [ ] `.zenodo.json` cleaned of TODOs; version matches the tag.
- [ ] License and access level confirmed.
- [ ] Large files within quota or quota increase requested.
- [ ] ORCIDs and affiliations filled.
- [ ] Related identifiers (paper DOI/arXiv) set.
- [ ] Community slug added/removed as desired.
- [ ] GitHub release notes drafted.

---

## Useful links
- GitHub integration enable: https://help.zenodo.org/docs/github/enable-repository/
- JSON metadata reference: https://help.zenodo.org/docs/github/describe-software/zenodo-json/
- Size limits & quota increases: https://support.zenodo.org/help/en-gb/1-upload-deposit/80-what-are-the-size-limitations-of-zenodo/
