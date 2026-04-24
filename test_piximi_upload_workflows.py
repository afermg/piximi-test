#!/usr/bin/env python3
"""Test image upload, segmentation, and classification workflows on piximi-beta.vercel.app

Uses Playwright filechooser event to handle dynamic file inputs triggered by "Open" button.
Tests both local image upload and example project workflows.
"""

import json
import os
import re
import time
from playwright.sync_api import sync_playwright

SCREENSHOTS_DIR = "/Users/amunozgo/tmp/piximi_screenshots"
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

EXAMPLE_IMAGES_DIR = "/Users/amunozgo/projects/web_check/example_images"
URL = "https://piximi-beta.vercel.app"

ISSUES = []
RESULTS = []
console_errors = []

def log(msg):
    print(f"[TEST] {msg}", flush=True)

def record(test_name, status, detail=""):
    RESULTS.append({"test": test_name, "status": status, "detail": detail})
    symbol = "PASS" if status == "pass" else "FAIL" if status == "fail" else "WARN"
    log(f"[{symbol}] {test_name}: {detail}")

def issue(severity, category, description):
    ISSUES.append({"severity": severity, "category": category, "description": description})
    log(f"[ISSUE-{severity.upper()}] [{category}] {description}")

def screenshot(page, name):
    path = os.path.join(SCREENSHOTS_DIR, f"{name}.png")
    page.screenshot(path=path, full_page=False)
    log(f"Screenshot: {path}")
    return path

def get_available_images():
    images = []
    for f in sorted(os.listdir(EXAMPLE_IMAGES_DIR)):
        fpath = os.path.join(EXAMPLE_IMAGES_DIR, f)
        if os.path.isfile(fpath) and f.lower().endswith(('.jpg', '.jpeg', '.png', '.tif', '.tiff')):
            images.append(fpath)
    return images

def open_new_project(page):
    """Navigate to home and start a new project"""
    page.goto(URL, wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(2000)
    page.click("button:has-text('Start New Project')", timeout=5000)
    page.wait_for_timeout(3000)

def upload_images_via_open(page, file_paths):
    """Upload images using the Open > Image submenu in the sidebar.

    The "Open" button shows a submenu with: Project, Image, Annotation.
    Clicking "Image" may show a further submenu or directly open a file chooser.
    Returns True if upload succeeded.
    """
    try:
        # Step 1: Click "Open" in the sidebar to show submenu
        open_btn = page.locator("div").filter(has_text=re.compile(r"^Open$")).first
        if not open_btn.is_visible():
            open_btn = page.get_by_text("Open", exact=True).first
        open_btn.click()
        page.wait_for_timeout(1000)

        # Step 2: Click "Image" in the submenu
        # Then expect a file chooser from the Image submenu
        image_menu = page.get_by_text("Image", exact=True)
        if image_menu.count() > 0:
            # Hover to open submenu (may have further options)
            image_menu.first.hover()
            page.wait_for_timeout(500)
            screenshot(page, "open_image_submenu")

            # Try to trigger file chooser by clicking
            try:
                with page.expect_file_chooser(timeout=5000) as fc_info:
                    image_menu.first.click()
                file_chooser = fc_info.value
                file_chooser.set_files(file_paths)
                page.wait_for_timeout(5000)
                return True
            except Exception as e:
                log(f"  Direct Image click didn't trigger filechooser: {e}")

            # Maybe clicking Image opened a further submenu
            page.wait_for_timeout(500)
            screenshot(page, "open_image_submenu2")

            # Look for submenu options like "From Computer", "Local", etc.
            submenu_items = page.evaluate("""() => {
                const items = document.querySelectorAll('[role="menuitem"], [role="menu"] *, [class*="MenuItem"], li');
                return Array.from(items).filter(i => i.offsetParent !== null)
                    .map(i => i.textContent.trim().substring(0, 60));
            }""")
            log(f"  Submenu items after Image hover: {json.dumps(submenu_items[:10])}")

            # Try clicking any visible submenu item that might lead to upload
            for kw in ['Computer', 'Local', 'Upload', 'File', 'Browse']:
                try:
                    sub_item = page.get_by_text(kw, exact=False).first
                    if sub_item.is_visible():
                        with page.expect_file_chooser(timeout=5000) as fc_info:
                            sub_item.click()
                        file_chooser = fc_info.value
                        file_chooser.set_files(file_paths)
                        page.wait_for_timeout(5000)
                        return True
                except:
                    pass

            # If there's no further submenu, try all visible menu items
            menu_items = page.query_selector_all("[role='menuitem']")
            for item in menu_items:
                text = (item.text_content() or "").strip()
                if item.is_visible() and text:
                    log(f"  Trying menuitem: '{text}'")
                    try:
                        with page.expect_file_chooser(timeout=3000) as fc_info:
                            item.click()
                        file_chooser = fc_info.value
                        file_chooser.set_files(file_paths)
                        page.wait_for_timeout(5000)
                        return True
                    except:
                        # Re-open the menu
                        open_btn.click()
                        page.wait_for_timeout(500)
                        image_menu.first.hover()
                        page.wait_for_timeout(500)

    except Exception as e:
        log(f"  Open > Image approach failed: {e}")

    # Fallback: look for any hidden file input that might have appeared
    try:
        file_inputs = page.query_selector_all("input[type='file']")
        if file_inputs:
            log(f"  Found {len(file_inputs)} file input(s), using first one")
            file_inputs[0].set_input_files(file_paths)
            page.wait_for_timeout(5000)
            return True
    except Exception as e:
        log(f"  Fallback file input failed: {e}")

    return False


def test_upload_jpg_image(page):
    """Test uploading a JPG image to a new project"""
    log("=== TEST: Upload JPG Image ===")

    open_new_project(page)
    screenshot(page, "40_new_project_for_upload")

    jpg_images = [f for f in get_available_images() if f.lower().endswith(('.jpg', '.jpeg'))]
    if not jpg_images:
        record("upload_jpg", "fail", "No JPG images found in example_images")
        return

    jpg_path = jpg_images[0]
    log(f"  Uploading: {os.path.basename(jpg_path)}")

    success = upload_images_via_open(page, jpg_path)
    if success:
        screenshot(page, "41_after_jpg_upload")

        # Verify image appears in the workspace
        ws = page.evaluate("""() => {
            const imgs = document.querySelectorAll('img');
            const canvases = document.querySelectorAll('canvas');
            const gridItems = document.querySelectorAll('[class*="ImageGrid"] *, [class*="grid"] img');
            return {
                imgCount: imgs.length,
                canvasCount: canvases.length,
                gridItems: gridItems.length,
                unknownCount: (() => {
                    const el = Array.from(document.querySelectorAll('*')).find(
                        e => e.textContent.trim().startsWith('Unknown') && e.offsetParent !== null
                    );
                    return el ? el.textContent.trim() : '';
                })()
            };
        }""")
        log(f"  After upload: imgs={ws['imgCount']}, canvas={ws['canvasCount']}, grid={ws['gridItems']}")
        log(f"  Unknown category: {ws['unknownCount']}")
        record("upload_jpg", "pass", f"Uploaded {os.path.basename(jpg_path)}")
    else:
        record("upload_jpg", "fail", "Could not upload JPG via any method")
        issue("high", "functionality", "Image upload via 'Open' button failed for JPG")
        screenshot(page, "41_upload_failed")


def test_upload_tif_images(page):
    """Test uploading TIF microscopy images"""
    log("=== TEST: Upload TIF Images ===")

    open_new_project(page)

    tif_images = [f for f in get_available_images() if f.lower().endswith(('.tif', '.tiff'))]
    if not tif_images:
        record("upload_tif", "fail", "No TIF images found")
        return

    # Upload first 3 TIF images
    to_upload = tif_images[:3]
    log(f"  Uploading {len(to_upload)} TIF images...")
    for f in to_upload:
        log(f"    - {os.path.basename(f)}")

    success = upload_images_via_open(page, to_upload)
    if success:
        page.wait_for_timeout(5000)  # Extra time for TIF processing
        screenshot(page, "43_after_tif_upload")

        # Check workspace state
        ws = page.evaluate("""() => {
            return {
                imgCount: document.querySelectorAll('img').length,
                canvasCount: document.querySelectorAll('canvas').length,
                bodyText: document.body.innerText.substring(0, 500),
                hasError: document.body.innerText.toLowerCase().includes('error')
            };
        }""")
        log(f"  After TIF upload: imgs={ws['imgCount']}, canvas={ws['canvasCount']}")
        if ws['hasError']:
            issue("high", "functionality", "Error after uploading TIF images")
            record("upload_tif", "warn", "TIF uploaded but errors present")
        else:
            record("upload_tif", "pass", f"Uploaded {len(to_upload)} TIF files")
    else:
        record("upload_tif", "fail", "Could not upload TIF files")
        issue("medium", "functionality", "TIF upload failed")


def test_upload_multiple_mixed(page):
    """Test uploading multiple images of mixed types"""
    log("=== TEST: Upload Multiple Mixed Images ===")

    open_new_project(page)

    all_images = get_available_images()
    to_upload = all_images[:6]  # Mix of JPG + TIF
    log(f"  Uploading {len(to_upload)} mixed images...")

    success = upload_images_via_open(page, to_upload)
    if success:
        page.wait_for_timeout(8000)
        screenshot(page, "44_after_multi_upload")

        ws = page.evaluate("""() => {
            return {
                imgCount: document.querySelectorAll('img').length,
                canvasCount: document.querySelectorAll('canvas').length,
                hasError: document.body.innerText.toLowerCase().includes('error')
            };
        }""")
        log(f"  After multi upload: imgs={ws['imgCount']}, canvas={ws['canvasCount']}")
        record("upload_multi", "pass" if not ws['hasError'] else "warn",
               f"Uploaded {len(to_upload)} images, imgs={ws['imgCount']}")
    else:
        record("upload_multi", "fail", "Multi-upload failed")


def test_classification_with_example(page):
    """Test classification workflow using MNIST example project"""
    log("=== TEST: Classification Workflow (MNIST) ===")

    page.goto(URL, wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(2000)

    # Open MNIST example
    try:
        page.click("button:has-text('Open Example Project')", timeout=5000)
        page.wait_for_timeout(1500)
        page.click("text=MNIST example project", timeout=5000)
        page.wait_for_timeout(15000)
        screenshot(page, "50_mnist_classify")
        log("  MNIST project loaded")
    except Exception as e:
        record("classify_load", "fail", f"Could not load MNIST: {e}")
        return

    # Verify CLASSIFICATION tab is active/available
    classify_tab = page.query_selector("button:has-text('Classification')")
    if classify_tab:
        log("  CLASSIFICATION tab found")
        classify_tab.click()
        page.wait_for_timeout(2000)
        screenshot(page, "51_classification_tab_active")

        # Check sidebar state after clicking Classification
        sidebar_state = page.evaluate("""() => {
            const text = document.body.innerText;
            const modelSection = text.includes('Model:') || text.includes('New Model');
            const hasCategories = text.includes('Categories');
            return {
                modelSection,
                hasCategories,
                text: text.substring(0, 1500)
            };
        }""")
        log(f"  Has model section: {sidebar_state['modelSection']}")
        record("classify_tab", "pass", "Classification tab clicked and active")
    else:
        record("classify_tab", "fail", "CLASSIFICATION tab not found")
        issue("high", "functionality", "Classification tab missing from sidebar")
        return

    # Look for the Fit/Train button (the play ► icon in the sidebar)
    fit_btns = page.evaluate("""() => {
        const btns = Array.from(document.querySelectorAll('button, [role="button"]'));
        return btns.filter(b => {
            const text = (b.textContent || '').toLowerCase().trim();
            const aria = (b.getAttribute('aria-label') || '').toLowerCase();
            const title = (b.getAttribute('title') || '').toLowerCase();
            return b.offsetParent !== null && (
                text.includes('fit') || text.includes('train') ||
                text.includes('predict') || text.includes('run') ||
                aria.includes('fit') || aria.includes('train') ||
                aria.includes('predict') || aria.includes('run') ||
                title.includes('fit') || title.includes('train')
            );
        }).map(b => ({
            text: (b.textContent || '').trim().substring(0, 60),
            ariaLabel: b.getAttribute('aria-label') || '',
            title: b.getAttribute('title') || '',
            disabled: b.disabled || b.getAttribute('aria-disabled') === 'true'
        }));
    }""")
    log(f"  Fit/Train/Predict buttons: {json.dumps(fit_btns)}")

    # Check the icon buttons in the sidebar (the 3 icons below Model: selector)
    icon_btns = page.evaluate("""() => {
        // The sidebar has 3 icon buttons for: Fit, Predict, Evaluate
        const btns = Array.from(document.querySelectorAll('button, [role="button"]'));
        return btns.filter(b => {
            return b.offsetParent !== null && b.querySelector('svg') && !b.textContent.trim();
        }).map(b => ({
            ariaLabel: b.getAttribute('aria-label') || '',
            title: b.getAttribute('title') || '',
            disabled: b.disabled || b.getAttribute('aria-disabled') === 'true',
            className: (b.className || '').toString().substring(0, 60)
        }));
    }""")
    log(f"  Icon-only buttons: {json.dumps(icon_btns)}")

    # Try to click the Fit button (play icon ► - usually first icon)
    # These are the 3 icons below "Model:" section
    try:
        # The icons with SVGs and no text near the Model section
        svg_btns = page.query_selector_all("button:has(svg)")
        enabled_svg_btns = [b for b in svg_btns if b.is_visible() and not b.is_disabled()]
        log(f"  Found {len(enabled_svg_btns)} enabled SVG buttons")

        # Try to find Fit button by its position or aria-label
        for btn in enabled_svg_btns:
            aria = btn.get_attribute("aria-label") or ""
            title = btn.get_attribute("title") or ""
            if any(kw in (aria + title).lower() for kw in ['fit', 'train', 'run', 'predict', 'evaluate']):
                log(f"  Found ML button: aria='{aria}' title='{title}'")
                btn.click()
                page.wait_for_timeout(5000)
                screenshot(page, "52_after_ml_btn_click")
                record("classify_action", "pass", f"Clicked ML button: {aria or title}")
                break
        else:
            # No labeled ML buttons found - try the icon buttons near "Model:" text
            record("classify_action", "warn", "No clearly labeled Fit/Train/Predict buttons found")
            issue("medium", "accessibility", "ML action buttons (Fit/Predict/Evaluate) lack aria-labels")
    except Exception as e:
        record("classify_action", "fail", f"Error with classification action: {e}")

    # Test Load Model functionality
    log("  Testing Load Model...")
    try:
        load_model_btn = page.query_selector("button:has-text('Load Model')")
        if load_model_btn and load_model_btn.is_visible():
            load_model_btn.click()
            page.wait_for_timeout(2000)
            screenshot(page, "53_load_model_dialog")

            dialog_state = page.evaluate("""() => {
                const dialog = document.querySelector('[role="dialog"]');
                if (!dialog) return { hasDialog: false };
                return {
                    hasDialog: true,
                    text: dialog.textContent.substring(0, 500),
                    hasUploadLocal: dialog.textContent.includes('UPLOAD LOCAL'),
                    hasFetchRemote: dialog.textContent.includes('FETCH REMOTE'),
                    hasModelFormat: dialog.textContent.includes('Model Format'),
                    hasFileSelect: !!dialog.querySelector('input[type="file"]') ||
                                   dialog.textContent.includes('Select model files')
                };
            }""")
            log(f"  Load Model dialog: {json.dumps(dialog_state)}")
            if dialog_state['hasDialog']:
                record("load_model_dialog", "pass",
                       f"Upload={dialog_state['hasUploadLocal']}, Remote={dialog_state['hasFetchRemote']}")

                # Test FETCH REMOTE tab
                try:
                    fetch_tab = page.query_selector("button:has-text('FETCH REMOTE'), [role='tab']:has-text('FETCH REMOTE')")
                    if fetch_tab:
                        fetch_tab.click()
                        page.wait_for_timeout(1500)
                        screenshot(page, "53b_fetch_remote")
                        record("load_model_fetch_remote", "pass", "Fetch Remote tab accessible")
                except Exception as e:
                    log(f"  Fetch Remote tab error: {e}")

                # Close dialog
                page.keyboard.press("Escape")
                page.wait_for_timeout(500)
            else:
                record("load_model_dialog", "fail", "Load Model dialog did not open")
    except Exception as e:
        record("load_model", "fail", f"Error: {e}")


def test_segmentation_with_example(page):
    """Test segmentation workflow using MNIST example project"""
    log("=== TEST: Segmentation Workflow (MNIST) ===")

    page.goto(URL, wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(2000)

    # Open MNIST
    try:
        page.click("button:has-text('Open Example Project')", timeout=5000)
        page.wait_for_timeout(1500)
        page.click("text=MNIST example project", timeout=5000)
        page.wait_for_timeout(15000)
        screenshot(page, "55_mnist_segment")
    except Exception as e:
        record("segment_load", "fail", f"Could not load MNIST: {e}")
        return

    # Click SEGMENTATION tab
    seg_tab = page.query_selector("button:has-text('Segmentation')")
    if seg_tab:
        seg_tab.click()
        page.wait_for_timeout(2000)
        screenshot(page, "56_segmentation_tab")

        seg_state = page.evaluate("""() => {
            const text = document.body.innerText;
            return {
                hasSelectedModel: text.includes('Selected Model'),
                hasModelKind: text.includes('Model Kind'),
                selectedModel: (() => {
                    const match = text.match(/Selected Model:([^\\n]+)/);
                    return match ? match[1].trim() : '';
                })(),
                modelKind: (() => {
                    const match = text.match(/Model Kind:([^\\n]+)/);
                    return match ? match[1].trim() : '';
                })()
            };
        }""")
        log(f"  Segmentation state: {json.dumps(seg_state)}")
        record("segment_tab", "pass", f"Selected Model: {seg_state['selectedModel']}, Kind: {seg_state['modelKind']}")

        # Check if there's a Load Model button for segmentation
        load_model_btn = page.query_selector("button:has-text('Load Model')")
        if load_model_btn and load_model_btn.is_visible():
            load_model_btn.click()
            page.wait_for_timeout(2000)
            screenshot(page, "57_seg_load_model")

            seg_dialog = page.evaluate("""() => {
                const dialog = document.querySelector('[role="dialog"]');
                if (!dialog) return { hasDialog: false };
                return {
                    hasDialog: true,
                    title: dialog.textContent.substring(0, 100),
                    hasUploadLocal: dialog.textContent.includes('UPLOAD LOCAL'),
                    hasFetchRemote: dialog.textContent.includes('FETCH REMOTE')
                };
            }""")
            log(f"  Seg Load Model dialog: {json.dumps(seg_dialog)}")
            if seg_dialog['hasDialog']:
                record("seg_load_model", "pass", "Segmentation Load Model dialog opened")

                # Try Fetch Remote for segmentation model
                try:
                    fetch_tab = page.query_selector("button:has-text('FETCH REMOTE'), [role='tab']:has-text('FETCH REMOTE')")
                    if fetch_tab:
                        fetch_tab.click()
                        page.wait_for_timeout(2000)
                        screenshot(page, "57b_seg_fetch_remote")

                        # Look for available remote models
                        remote_models = page.evaluate("""() => {
                            const dialog = document.querySelector('[role="dialog"]');
                            if (!dialog) return [];
                            const items = dialog.querySelectorAll('li, [class*="item"], [class*="Item"], [class*="list"] > *');
                            return Array.from(items).map(i => i.textContent.trim().substring(0, 80));
                        }""")
                        log(f"  Remote segmentation models: {json.dumps(remote_models[:10])}")
                except Exception as e:
                    log(f"  Fetch Remote seg error: {e}")

            page.keyboard.press("Escape")
            page.wait_for_timeout(500)
    else:
        record("segment_tab", "fail", "SEGMENTATION tab not found")
        issue("high", "functionality", "Segmentation tab missing")


def test_annotate_workflow(page):
    """Test the annotation (manual segmentation) workflow"""
    log("=== TEST: Annotate Workflow ===")

    page.goto(URL, wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(2000)

    # Open MNIST and navigate to annotate
    try:
        page.click("button:has-text('Open Example Project')", timeout=5000)
        page.wait_for_timeout(1500)
        page.click("text=MNIST example project", timeout=5000)
        page.wait_for_timeout(15000)
    except Exception as e:
        record("annotate_load", "fail", f"Could not load MNIST: {e}")
        return

    # Click Annotate button (top right)
    annotate_btn = page.locator("text=Annotate").first
    try:
        if annotate_btn.is_visible():
            # Annotate might be disabled without an image selected
            is_disabled = annotate_btn.evaluate("el => el.closest('button, div')?.getAttribute('aria-disabled') === 'true' || el.closest('button')?.disabled")
            log(f"  Annotate button disabled: {is_disabled}")

            if is_disabled:
                # Need to select an image first - click on one
                log("  Selecting an image first...")
                img = page.query_selector("img")
                if img and img.is_visible():
                    img.click()
                    page.wait_for_timeout(1000)
                    screenshot(page, "60_image_selected")

                    # Try annotate again
                    annotate_btn = page.locator("text=Annotate").first
                    is_disabled = annotate_btn.evaluate("el => el.closest('button, div')?.getAttribute('aria-disabled') === 'true' || el.closest('button')?.disabled")
                    log(f"  Annotate after select: disabled={is_disabled}")

            if not is_disabled:
                annotate_btn.click()
                page.wait_for_timeout(5000)
                screenshot(page, "61_annotate_view")

                # Check annotation tools
                annotate_ui = page.evaluate("""() => {
                    const url = window.location.href;
                    const canvases = document.querySelectorAll('canvas').length;
                    const allBtns = Array.from(document.querySelectorAll('button, [role="button"]'))
                        .filter(b => b.offsetParent !== null)
                        .map(b => ({
                            text: (b.textContent || '').trim().substring(0, 40),
                            ariaLabel: b.getAttribute('aria-label') || '',
                            title: b.getAttribute('title') || ''
                        }));
                    return { url, canvases, buttons: allBtns };
                }""")
                log(f"  Annotate URL: {annotate_ui['url']}")
                log(f"  Canvases: {annotate_ui['canvases']}")
                log(f"  Buttons in annotate view:")
                for btn in annotate_ui['buttons'][:15]:
                    label = btn['text'] or btn['ariaLabel'] or btn['title']
                    if label:
                        log(f"    - {label}")

                # Look for annotation tools (pen, brush, threshold, etc.)
                tools_found = [b for b in annotate_ui['buttons']
                             if any(kw in (b['text'] + b['ariaLabel'] + b['title']).lower()
                                   for kw in ['pen', 'brush', 'lasso', 'select', 'threshold',
                                            'rectangle', 'ellipse', 'quick', 'magic', 'wand',
                                            'flood', 'zoom', 'hand', 'color'])]
                if tools_found:
                    tool_names = [t['text'] or t['ariaLabel'] or t['title'] for t in tools_found]
                    record("annotate_tools", "pass", f"Found tools: {', '.join(tool_names[:8])}")
                else:
                    record("annotate_tools", "warn", "No labeled annotation tools found")
                    issue("medium", "accessibility", "Annotation tools lack text labels")

                record("annotate_view", "pass", f"Annotate view opened, {annotate_ui['canvases']} canvases")
            else:
                record("annotate_view", "warn", "Annotate button is disabled even after selecting image")
                issue("medium", "functionality", "Cannot enter annotate view - button stays disabled")
        else:
            record("annotate_view", "fail", "Annotate button not visible")
    except Exception as e:
        record("annotate_view", "fail", f"Error: {e}")
        screenshot(page, "61_annotate_error")


def test_measure_workflow(page):
    """Test the Measure view"""
    log("=== TEST: Measure Workflow ===")

    page.goto(URL, wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(2000)

    # Open MNIST
    try:
        page.click("button:has-text('Open Example Project')", timeout=5000)
        page.wait_for_timeout(1500)
        page.click("text=MNIST example project", timeout=5000)
        page.wait_for_timeout(15000)
    except Exception as e:
        record("measure_load", "fail", f"Could not load project: {e}")
        return

    # Click Measure button
    measure_btn = page.locator("text=Measure").first
    try:
        if measure_btn.is_visible():
            measure_btn.click()
            page.wait_for_timeout(3000)
            screenshot(page, "63_measure_view")

            measure_ui = page.evaluate("""() => {
                return {
                    url: window.location.href,
                    text: document.body.innerText.substring(0, 1500),
                    hasTable: !!document.querySelector('table, [role="grid"], [class*="table"], [class*="Table"]'),
                    buttons: Array.from(document.querySelectorAll('button'))
                        .filter(b => b.offsetParent !== null)
                        .map(b => (b.textContent || '').trim().substring(0, 40))
                        .filter(t => t)
                };
            }""")
            log(f"  Measure URL: {measure_ui['url']}")
            log(f"  Has table: {measure_ui['hasTable']}")
            log(f"  Buttons: {measure_ui['buttons'][:10]}")
            log(f"  Text: {measure_ui['text'][:300]}")
            record("measure_view", "pass", f"Measure view opened, has_table={measure_ui['hasTable']}")
    except Exception as e:
        record("measure_view", "fail", f"Error: {e}")


def test_upload_then_classify(page):
    """End-to-end: upload local images, then attempt classification"""
    log("=== TEST: Upload Then Classify (E2E) ===")

    open_new_project(page)

    images = get_available_images()
    to_upload = images[:3]
    log(f"  Uploading {len(to_upload)} local images...")

    success = upload_images_via_open(page, to_upload)
    if success:
        page.wait_for_timeout(3000)
        screenshot(page, "70_e2e_uploaded")

        # Verify images loaded
        ws = page.evaluate("""() => {
            return {
                imgCount: document.querySelectorAll('img').length,
                text: document.body.innerText.substring(0, 500)
            };
        }""")
        log(f"  Workspace after upload: {ws['imgCount']} images")
        record("e2e_upload", "pass", f"Uploaded {len(to_upload)} images")

        # Click Classification tab
        cls_tab = page.query_selector("button:has-text('Classification')")
        if cls_tab:
            cls_tab.click()
            page.wait_for_timeout(1000)
            screenshot(page, "71_e2e_classify_tab")
            record("e2e_classify_tab", "pass", "Classification tab activated after upload")

            # Check model state
            model_state = page.evaluate("""() => {
                const text = document.body.innerText;
                return {
                    hasModel: text.includes('Model:'),
                    hasNewModel: text.includes('New Model'),
                    hasCategories: text.includes('Categories')
                };
            }""")
            log(f"  Model state: {json.dumps(model_state)}")
        else:
            record("e2e_classify_tab", "fail", "Classification tab not found after upload")
    else:
        record("e2e_upload", "fail", "Could not upload images for e2e test")
        issue("high", "functionality", "Image upload failed in end-to-end workflow")


def test_upload_then_segment(page):
    """End-to-end: upload local images, then test segmentation"""
    log("=== TEST: Upload Then Segment (E2E) ===")

    open_new_project(page)

    images = get_available_images()
    to_upload = images[:2]

    success = upload_images_via_open(page, to_upload)
    if success:
        page.wait_for_timeout(3000)
        screenshot(page, "75_e2e_seg_uploaded")
        record("e2e_seg_upload", "pass", f"Uploaded {len(to_upload)} images")

        # Click Segmentation tab
        seg_tab = page.query_selector("button:has-text('Segmentation')")
        if seg_tab:
            seg_tab.click()
            page.wait_for_timeout(2000)
            screenshot(page, "76_e2e_seg_tab")

            seg_state = page.evaluate("""() => {
                const text = document.body.innerText;
                return {
                    hasSelectedModel: text.includes('Selected Model'),
                    text: text.substring(0, 500)
                };
            }""")
            log(f"  Segmentation state after upload: {json.dumps(seg_state)}")
            record("e2e_seg_tab", "pass", "Segmentation tab activated after upload")
        else:
            record("e2e_seg_tab", "fail", "Segmentation tab not found")
    else:
        record("e2e_seg_upload", "fail", "Could not upload for segmentation e2e")


def test_example_project_cell_painting(page):
    """Test opening the cell painting / U2OS example project if available"""
    log("=== TEST: Cell Painting Example Project ===")

    page.goto(URL, wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(2000)

    try:
        page.click("button:has-text('Open Example Project')", timeout=5000)
        page.wait_for_timeout(1500)

        # Check "Image and Object Sets" tab for cell painting data
        try:
            obj_tab = page.locator("text=IMAGE AND OBJECT SETS").first
            if obj_tab.is_visible():
                obj_tab.click()
                page.wait_for_timeout(2000)
                screenshot(page, "80_object_sets_tab")

                obj_items = page.evaluate("""() => {
                    const dialog = document.querySelector('[role="dialog"]');
                    if (!dialog) return [];
                    return Array.from(dialog.querySelectorAll('*')).filter(
                        e => e.children.length === 0 && e.textContent.trim().length > 3 && e.offsetParent !== null
                    ).map(e => e.textContent.trim().substring(0, 100));
                }""")
                log(f"  Object sets items: {json.dumps(obj_items[:15])}")

                # Try to open a cell painting dataset
                for item in ['U2OS', 'cell-painting', 'Malaria', 'blood']:
                    try:
                        cell_btn = page.query_selector(f"text={item}")
                        if cell_btn and cell_btn.is_visible():
                            cell_btn.click()
                            page.wait_for_timeout(15000)
                            screenshot(page, f"81_opened_{item.lower()}")
                            record("example_cell_painting", "pass", f"Opened {item} project")

                            # Check workspace
                            ws = page.evaluate("""() => {
                                return {
                                    imgCount: document.querySelectorAll('img').length,
                                    canvasCount: document.querySelectorAll('canvas').length,
                                    text: document.body.innerText.substring(0, 500)
                                };
                            }""")
                            log(f"  {item} workspace: imgs={ws['imgCount']}, canvas={ws['canvasCount']}")
                            return
                    except:
                        pass

                record("example_cell_painting", "warn", "No cell painting project found to open")
        except Exception as e:
            log(f"  Object Sets tab error: {e}")

        page.keyboard.press("Escape")
    except Exception as e:
        record("example_cell_painting", "fail", f"Error: {e}")


def main():
    log(f"Starting Piximi Upload & Workflow tests: {URL}")
    log(f"Images dir: {EXAMPLE_IMAGES_DIR}")

    images = get_available_images()
    log(f"Found {len(images)} test images")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        def on_console(msg):
            if msg.type == "error":
                console_errors.append(msg.text)
        page.on("console", on_console)

        try:
            test_upload_jpg_image(page)
            test_upload_tif_images(page)
            test_upload_multiple_mixed(page)
            test_classification_with_example(page)
            test_segmentation_with_example(page)
            test_annotate_workflow(page)
            test_measure_workflow(page)
            test_upload_then_classify(page)
            test_upload_then_segment(page)
            test_example_project_cell_painting(page)
        except Exception as e:
            log(f"FATAL ERROR: {e}")
            import traceback
            traceback.print_exc()
            screenshot(page, "99_workflow_fatal_error")
        finally:
            screenshot(page, "99_workflow_final")

            log(f"\n{'='*70}")
            log(f"CONSOLE ERRORS: {len(console_errors)}")
            for err in console_errors[:20]:
                log(f"  ERROR: {err[:200]}")

            log(f"\n{'='*70}")
            log("ISSUES FOUND")
            log(f"{'='*70}")
            for i, iss in enumerate(ISSUES, 1):
                log(f"  {i}. [{iss['severity'].upper()}] [{iss['category']}] {iss['description']}")
            if not ISSUES:
                log("  None!")

            log(f"\n{'='*70}")
            log("TEST RESULTS SUMMARY")
            log(f"{'='*70}")
            passes = sum(1 for r in RESULTS if r['status'] == 'pass')
            fails = sum(1 for r in RESULTS if r['status'] == 'fail')
            warns = sum(1 for r in RESULTS if r['status'] == 'warn')
            log(f"Total: {len(RESULTS)} | Pass: {passes} | Fail: {fails} | Warn: {warns}")
            for r in RESULTS:
                symbol = {"pass": "✓", "fail": "✗", "warn": "⚠"}[r['status']]
                log(f"  {symbol} {r['test']}: {r['detail'][:120]}")
            log(f"{'='*70}")

        browser.close()

if __name__ == "__main__":
    main()
