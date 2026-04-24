# Web Check

Automated browser testing and issue reports for web applications, using Playwright (headless Chromium).

## Reports

- [Piximi Beta](piximi_test_report.md) - UI/accessibility audit of [piximi-beta.vercel.app](https://piximi-beta.vercel.app)
- [quasimorphic.com](quasimorphic_test_report.md) - UI/accessibility/SEO audit of [quasimorphic.com](https://quasimorphic.com)

## Screenshots

Screenshots are stored in separate directories per site:

- `piximi_screenshots/` - Piximi test screenshots
- `quasimorphic_screenshots/` - quasimorphic.com test screenshots

## Example Images

Test images for Piximi upload workflows, stored via Git LFS (`.tif` files).

See [example_images/README.md](example_images/README.md) for reproduction instructions.

## Running Tests

```bash
pip install playwright openslide-python openslide-bin
python -m playwright install chromium

# Run tests
python test_piximi_final.py
python test_quasimorphic.py
```
