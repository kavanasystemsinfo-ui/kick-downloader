# Project Roadmap

> Kick Downloader - API service for downloading Kick.com videos as MP3/MP4

## Document status

- **Status:** Active.
- **Last updated:** 2026-06-28.
- **Current phase:** Production Deployment Ready.
- **Primary source of truth:** This file plus the project README, architecture docs, and test suite.

## Working principles

1. Read context before modifying code.
2. Prefer small, reversible changes.
3. Write tests before changing business logic.
4. Keep NotebookLM outputs as research aids, not source of truth.
5. Update this roadmap only after the relevant tests are green.

## Current phase

**Phase:** Production Deployment Ready.

### Goal

Backend API complete with systemd service, nginx reverse proxy, rate limiting, and APK integration guide.

### Why this phase matters

The backend is production-ready for deployment on Hetzner VPS. All core functionality tested and documented.

### Entry criteria

- [x] Relevant architecture docs reviewed.
- [x] Existing tests near the target behavior identified.
- [x] Current technical debt reviewed.
- [x] Smallest next behavior defined.

### Exit criteria

- [x] Spec written first.
- [x] Red failure verified.
- [x] Minimal implementation added.
- [x] Green tests verified.
- [x] Relevant docs updated.
- [x] No known data-loss or security regression introduced.

## Completed milestones

| Milestone | Date | Verification gate | Status |
|---|---:|---|---|
| Project setup with TDD kit | 2026-06-28 | Kit files in place | Completed |
| URL validation logic | 2026-06-28 | `pytest tests/test_main.py::TestKickUrlValidation -v` passed | Completed |
| File extension logic | 2026-06-28 | `pytest tests/test_main.py::TestFileExtension -v` passed | Completed |
| /download endpoint validation | 2026-06-28 | `pytest tests/test_main.py::TestDownloadEndpoint -v` passed | Completed |
| /files endpoint serving | 2026-06-28 | `pytest tests/test_main.py::TestFilesEndpoint -v` passed | Completed |
| Integration tests | 2026-06-28 | `pytest tests/test_integration.py -v` passed | Completed |
| Full test suite | 2026-06-28 | `pytest tests/ -v` (22 tests) passed | Completed |
| Rate limiting with slowapi | 2026-06-28 | Tests pass with rate limiter | Completed |
| Systemd service file | 2026-06-28 | `deploy/kick-downloader.service` created | Completed |
| Nginx reverse proxy config | 2026-06-28 | `deploy/nginx.conf` created | Completed |
| APK blocks guide | 2026-06-28 | `docs/apk_blocks_guide.md` created | Completed |

## Next steps

1. Deploy to Hetzner VPS using systemd service.
2. Configure nginx with SSL (Let's Encrypt).
3. Build Android APK with Kodular/Roocode using blocks guide.
4. Add monitoring (Prometheus/Grafana) and logging.
5. Consider API key authentication for shared usage.

## Blocked decisions

| Decision | Blocker | Owner | Next action |
|---|---|---|---|
| Cleanup strategy for large files | Need to verify client download completion | TBD | Research BackgroundTasks vs polling |
| Production authentication | Not needed for personal use | TBD | Add API key if shared |

## Validation commands

```bash
# Python project validation
python -m py_compile main.py
pytest tests/ -v

# Deployment validation
sudo systemctl daemon-reload
sudo systemctl enable kick-downloader
sudo systemctl start kick-downloader
sudo systemctl status kick-downloader

# Nginx validation
sudo nginx -t
sudo systemctl reload nginx

# SSL certificate (Let's Encrypt)
sudo certbot --nginx -d your-domain.com
```

## Notes

- Keep this file concise.
- Do not record every implementation detail here.
- Use audit changelogs or commit messages for detailed history.
