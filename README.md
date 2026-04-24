# Web Check - Piximi Beta QA

Automated browser tests for finding bugs, UI issues, and regressions in the beta version of [Piximi](https://piximi-beta.vercel.app) -- an open-source image annotation tool for biology.

Uses [Playwright](https://playwright.dev/python/) (headless Chromium) to exercise the app end-to-end and produce detailed issue reports with screenshots.

## What gets tested

| Test script | Coverage |
|---|---|
| `test_piximi.py` | Page load, console errors, UI elements, navigation, responsive layout, links/buttons, accessibility, performance, network errors, file upload, error boundaries |
| `test_piximi_deep.py` | MNIST example project, workspace interaction, sidebar/categories, new project flow, upload project flow, keyboard navigation, broken images, mobile usability, meta tags |
| `test_piximi_models.py` | Loading classification and segmentation models (remote and local) |
| `test_piximi_upload_workflows.py` | Image upload, segmentation, and classification workflows using real microscopy images |
| `test_piximi_final.py` | Targeted regression tests (mobile dialog overlap, etc.) |

## Reports

Test results are written as Markdown reports:

- [`piximi_test_report.md`](piximi_test_report.md) -- Full issue report with severity ratings
- [`piximi_test_report_2026-04-24.md`](piximi_test_report_2026-04-24.md) -- Dated report snapshot

## Setup

```bash
pip install playwright openslide-python openslide-bin
python -m playwright install chromium
```

## Running tests

```bash
# Full surface-level audit
python test_piximi.py

# Deep interaction tests (example projects, workspace, keyboard nav)
python test_piximi_deep.py

# Model loading tests
python test_piximi_models.py

# Image upload and annotation workflows
python test_piximi_upload_workflows.py

# Targeted regression checks
python test_piximi_final.py
```

Screenshots are saved to `piximi_screenshots/`.

## Example images

The `example_images/` directory contains real microscopy images (JUMP Cell Painting `.tif` files and others) used by `test_piximi_upload_workflows.py` to test image upload and processing. Large `.tif` files are tracked with Git LFS.

## Project structure

```
.
├── test_piximi.py                  # Broad automated audit
├── test_piximi_deep.py             # Deep interaction testing
├── test_piximi_models.py           # Model loading tests
├── test_piximi_upload_workflows.py # Upload + annotation workflows
├── test_piximi_final.py            # Targeted regression tests
├── piximi_test_report.md           # Latest issue report
├── example_images/                 # Test images (JUMP, MNIST, etc.)
└── piximi_screenshots/             # Screenshots captured during runs
```
