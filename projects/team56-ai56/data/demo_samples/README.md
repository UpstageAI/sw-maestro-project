# Demo Samples

This folder contains ready-to-use sample text files for the current Streamlit demo.

## Suggested order

1. Create a job with one of the files in `jds/`
2. Confirm the suggested criteria in the UI
3. Upload one or more files from `candidates/`
4. Review:
   - masking preview
   - GitHub verification status
   - ranking
   - candidate detail
   - audit logs

## Fastest demo path

- Job: `jds/jd_backend_intern_ko.txt`
- Candidate 1: `candidates/candidate_backend_strong_ko.txt`
- Candidate 2: `candidates/candidate_backend_mixed_ko.txt`
- Candidate 3: `candidates/candidate_backend_github_fail_ko.txt`

## Expanded cohorts

- Backend cohort: 11 candidates
- Frontend cohort: 4 candidates
- Seed manifest: `scenarios/demo_seed_manifest.json`

## What each sample is for

- `candidate_backend_strong_ko.txt`: strong backend match, public GitHub URL included
- `candidate_backend_mixed_ko.txt`: some fit, but less direct evidence
- `candidate_backend_github_fail_ko.txt`: invalid GitHub user to test failure handling
- `candidate_no_github_ko.txt`: no GitHub URL case
- `candidate_masking_focus_ko.txt`: lots of PII-like fields to verify masking preview
- `candidate_backend_low_fit_ko.txt`: intentionally weaker backend fit
- `candidate_frontend_dashboard_strong_ko.txt`: strong dashboard-focused frontend fit
- `candidate_frontend_low_fit_ko.txt`: intentionally weaker frontend fit

See `scenarios/manual_test_checklist_ko.md` for a concrete testing order.
