#!/usr/bin/env python3
"""Test loading classification and segmentation models (remote and local) on piximi-beta.vercel.app"""

import json
import os
import time
from playwright.sync_api import sync_playwright

SCREENSHOTS_DIR = "/Users/amunozgo/tmp/piximi_screenshots"
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

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

def load_mnist_project(page):
    """Load the MNIST example project"""
    page.goto(URL, wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(2000)
    page.click("button:has-text('Open Example Project')", timeout=5000)
    page.wait_for_timeout(1500)
    page.click("text=MNIST example project", timeout=5000)
    page.wait_for_timeout(15000)


def get_model_state(page):
    """Get the current model state from the sidebar"""
    return page.evaluate("""() => {
        const text = document.body.innerText;
        const modelMatch = text.match(/Model:\\s*([^\\n]+)/);
        const selectedMatch = text.match(/Selected Model:\\s*([^\\n]+)/);
        const kindMatch = text.match(/Model Kind:\\s*([^\\n]+)/);
        return {
            modelName: modelMatch ? modelMatch[1].trim() : null,
            selectedModel: selectedMatch ? selectedMatch[1].trim() : null,
            modelKind: kindMatch ? kindMatch[1].trim() : null,
            hasClassification: text.includes('CLASSIFICATION'),
            hasSegmentation: text.includes('SEGMENTATION'),
            fullText: text.substring(0, 2000)
        };
    }""")


# ==================== CLASSIFICATION MODELS ====================

def test_classification_load_model_dialog(page):
    """Test the classification Load Model dialog UI in detail"""
    log("=== TEST: Classification Load Model Dialog ===")

    load_mnist_project(page)

    # Ensure Classification tab is active
    cls_tab = page.query_selector("button:has-text('Classification')")
    if cls_tab:
        cls_tab.click()
        page.wait_for_timeout(1000)

    # Click Load Model
    page.click("button:has-text('Load Model')", timeout=5000)
    page.wait_for_timeout(2000)
    screenshot(page, "M01_cls_load_dialog_upload_local")

    # Inspect Upload Local tab
    upload_local = page.evaluate("""() => {
        const dialog = document.querySelector('[role="dialog"]');
        if (!dialog) return { found: false };
        const inputs = dialog.querySelectorAll('input');
        const radios = dialog.querySelectorAll('input[type="radio"]');
        const buttons = Array.from(dialog.querySelectorAll('button')).map(
            b => ({ text: b.textContent.trim(), disabled: b.disabled })
        );
        const fileInputs = dialog.querySelectorAll('input[type="file"]');
        return {
            found: true,
            title: dialog.querySelector('h2, h3, [class*="Title"]')?.textContent?.trim() || '',
            inputCount: inputs.length,
            radioCount: radios.length,
            buttons: buttons,
            fileInputCount: fileInputs.length,
            text: dialog.textContent.substring(0, 600)
        };
    }""")
    log(f"  Upload Local tab: {json.dumps(upload_local, indent=2)}")
    record("cls_upload_local_tab", "pass" if upload_local['found'] else "fail",
           f"Buttons: {upload_local.get('buttons', [])}")

    # Try clicking "Select model files" to see if file chooser appears
    try:
        select_files_link = page.locator("text=Select model files").first
        if select_files_link.is_visible():
            with page.expect_file_chooser(timeout=5000) as fc_info:
                select_files_link.click()
            file_chooser = fc_info.value
            log(f"  File chooser opened: multiple={file_chooser.is_multiple}")
            record("cls_local_file_chooser", "pass", f"File chooser opens, multiple={file_chooser.is_multiple}")
            # Don't actually upload - just verify it works
            page.keyboard.press("Escape")
            page.wait_for_timeout(500)
        else:
            record("cls_local_file_chooser", "warn", "Select model files link not visible")
    except Exception as e:
        record("cls_local_file_chooser", "fail", f"File chooser failed: {e}")

    # Re-open dialog if needed
    dialog = page.query_selector("[role='dialog']")
    if not dialog:
        page.click("button:has-text('Load Model')", timeout=5000)
        page.wait_for_timeout(1500)

    # Switch to Fetch Remote tab
    log("  Switching to Fetch Remote tab...")
    try:
        fetch_tab = page.locator("text=Fetch Remote").first
        if not fetch_tab.is_visible():
            fetch_tab = page.locator("text=FETCH REMOTE").first
        fetch_tab.click()
        page.wait_for_timeout(1000)
        screenshot(page, "M02_cls_fetch_remote_tab")

        # Inspect Fetch Remote tab
        fetch_remote = page.evaluate("""() => {
            const dialog = document.querySelector('[role="dialog"]');
            if (!dialog) return { found: false };
            const inputs = Array.from(dialog.querySelectorAll('input')).map(i => ({
                type: i.type,
                placeholder: i.placeholder,
                value: i.value,
                visible: i.offsetParent !== null
            }));
            const checkboxes = Array.from(dialog.querySelectorAll('input[type="checkbox"]')).map(c => ({
                checked: c.checked,
                label: c.parentElement?.textContent?.trim() || ''
            }));
            const buttons = Array.from(dialog.querySelectorAll('button')).map(
                b => ({ text: b.textContent.trim(), disabled: b.disabled })
            );
            return {
                found: true,
                inputs: inputs,
                checkboxes: checkboxes,
                buttons: buttons,
                text: dialog.textContent.substring(0, 600)
            };
        }""")
        log(f"  Fetch Remote tab: {json.dumps(fetch_remote, indent=2)}")
        record("cls_fetch_remote_tab", "pass", f"Inputs: {len(fetch_remote.get('inputs',[]))}, Checkboxes: {len(fetch_remote.get('checkboxes',[]))}")

    except Exception as e:
        record("cls_fetch_remote_tab", "fail", f"Error: {e}")

    page.keyboard.press("Escape")
    page.wait_for_timeout(500)


def test_classification_fetch_remote_model(page):
    """Test actually fetching a remote classification model"""
    log("=== TEST: Classification Fetch Remote Model ===")

    load_mnist_project(page)

    # Classification tab
    cls_tab = page.query_selector("button:has-text('Classification')")
    if cls_tab:
        cls_tab.click()
        page.wait_for_timeout(1000)

    # Get initial model state
    initial_state = get_model_state(page)
    log(f"  Initial model: {initial_state.get('modelName', 'N/A')}")

    # Open Load Model > Fetch Remote
    page.click("button:has-text('Load Model')", timeout=5000)
    page.wait_for_timeout(1500)

    fetch_tab = page.locator("text=FETCH REMOTE").first
    if not fetch_tab.is_visible():
        fetch_tab = page.locator("text=Fetch Remote").first
    fetch_tab.click()
    page.wait_for_timeout(1000)

    # Check the "From TF Hub?" checkbox and see if a URL is pre-filled or if we need one
    dialog_info = page.evaluate("""() => {
        const dialog = document.querySelector('[role="dialog"]');
        if (!dialog) return {};
        const urlInput = dialog.querySelector('input[type="text"], input[type="url"], input:not([type="radio"]):not([type="checkbox"]):not([type="file"])');
        const checkbox = dialog.querySelector('input[type="checkbox"]');
        const loadBtn = Array.from(dialog.querySelectorAll('button')).find(
            b => b.textContent.trim().includes('LOAD MODEL') || b.textContent.trim().includes('OPEN CLASSIFICATION')
        );
        return {
            urlInputValue: urlInput ? urlInput.value : null,
            urlInputPlaceholder: urlInput ? urlInput.placeholder : null,
            checkboxChecked: checkbox ? checkbox.checked : null,
            checkboxLabel: checkbox ? checkbox.parentElement?.textContent?.trim() : null,
            loadBtnText: loadBtn ? loadBtn.textContent.trim() : null,
            loadBtnDisabled: loadBtn ? loadBtn.disabled : null
        };
    }""")
    log(f"  Dialog info: {json.dumps(dialog_info)}")

    # Try checking "From TF Hub?" checkbox
    try:
        checkbox = page.locator("input[type='checkbox']").first
        if checkbox.is_visible():
            checkbox.check()
            page.wait_for_timeout(500)
            log("  Checked 'From TF Hub?' checkbox")
    except Exception as e:
        log(f"  Checkbox interaction failed: {e}")

    # Enter a TF Hub model URL for MNIST classification
    # Use mobilenet as a well-known classification model
    try:
        url_input = page.locator("[role='dialog'] input[type='text'], [role='dialog'] input:not([type='radio']):not([type='checkbox']):not([type='file'])").first
        if url_input.is_visible():
            url_input.fill("https://tfhub.dev/google/tfjs-model/imagenet/mobilenet_v2_100_224/classification/3/default/1")
            page.wait_for_timeout(500)
            screenshot(page, "M03_cls_remote_url_filled")
            log("  URL filled in for remote classification model")

            # Check if LOAD MODEL / OPEN CLASSIFICATION MODEL button is enabled
            load_btn_state = page.evaluate("""() => {
                const dialog = document.querySelector('[role="dialog"]');
                const btn = Array.from(dialog.querySelectorAll('button')).find(
                    b => b.textContent.includes('LOAD MODEL') || b.textContent.includes('OPEN CLASSIFICATION')
                );
                return {
                    text: btn ? btn.textContent.trim() : null,
                    disabled: btn ? btn.disabled : null
                };
            }""")
            log(f"  Load button: {json.dumps(load_btn_state)}")

            if load_btn_state.get('disabled') == False:
                # Click Load Model
                load_btn = page.locator("[role='dialog'] button:has-text('LOAD MODEL'), [role='dialog'] button:has-text('OPEN CLASSIFICATION')").first
                load_btn.click()
                log("  Clicked Load Model button, waiting for model to load...")

                # Wait for model to load (may take a while)
                page.wait_for_timeout(15000)
                screenshot(page, "M04_cls_remote_loading")

                # Check for progress, errors, or success
                load_result = page.evaluate("""() => {
                    const text = document.body.innerText;
                    const dialog = document.querySelector('[role="dialog"]');
                    const progress = document.querySelector('[role="progressbar"]');
                    const snackbar = document.querySelector('[class*="Snackbar"], [class*="snackbar"]');
                    return {
                        hasDialog: !!dialog,
                        hasProgress: !!progress,
                        hasSnackbar: !!snackbar,
                        snackbarText: snackbar ? snackbar.textContent.trim().substring(0, 200) : '',
                        hasError: text.includes('Error') || text.includes('error') || text.includes('failed'),
                        modelText: text.substring(0, 1500)
                    };
                }""")
                log(f"  Load result: dialog={load_result['hasDialog']}, progress={load_result['hasProgress']}, error={load_result['hasError']}")

                page.wait_for_timeout(15000)
                screenshot(page, "M05_cls_remote_loaded")

                # Check model state after loading
                after_state = get_model_state(page)
                log(f"  Model after load: {after_state.get('modelName', 'N/A')}")

                if after_state.get('modelName') != initial_state.get('modelName'):
                    record("cls_fetch_remote", "pass", f"Model changed from '{initial_state.get('modelName')}' to '{after_state.get('modelName')}'")
                else:
                    # Check for error messages
                    if load_result['hasError']:
                        record("cls_fetch_remote", "fail", "Error loading remote classification model")
                        issue("high", "functionality", "Remote classification model failed to load")
                    else:
                        record("cls_fetch_remote", "warn", "Model state unchanged after remote load attempt")
            else:
                record("cls_fetch_remote", "warn", f"Load button is disabled: {load_btn_state}")
                issue("medium", "functionality", "Load Model button disabled after entering URL")
        else:
            record("cls_fetch_remote", "fail", "URL input not found in Fetch Remote tab")
    except Exception as e:
        record("cls_fetch_remote", "fail", f"Error: {e}")
        screenshot(page, "M05_cls_remote_error")

    page.keyboard.press("Escape")
    page.wait_for_timeout(500)


def test_classification_local_upload(page):
    """Test the local model upload flow for classification"""
    log("=== TEST: Classification Local Model Upload ===")

    load_mnist_project(page)

    cls_tab = page.query_selector("button:has-text('Classification')")
    if cls_tab:
        cls_tab.click()
        page.wait_for_timeout(1000)

    page.click("button:has-text('Load Model')", timeout=5000)
    page.wait_for_timeout(1500)

    # Should be on Upload Local tab by default
    screenshot(page, "M06_cls_local_upload_tab")

    # Test Graph Model vs Layers Model radio
    try:
        graph_radio = page.locator("text=Graph Model").first
        layers_radio = page.locator("text=Layers Model").first

        if graph_radio.is_visible():
            graph_radio.click()
            page.wait_for_timeout(500)
            screenshot(page, "M07_cls_graph_model_selected")

            graph_state = page.evaluate("""() => {
                const dialog = document.querySelector('[role="dialog"]');
                const text = dialog ? dialog.textContent : '';
                return {
                    text: text.substring(0, 500),
                    mentionsJson: text.includes('.json'),
                    mentionsBin: text.includes('.bin'),
                    mentionsPb: text.includes('.pb') || text.includes('SavedModel')
                };
            }""")
            log(f"  Graph Model format info: json={graph_state['mentionsJson']}, bin={graph_state['mentionsBin']}")
            record("cls_local_graph_format", "pass", "Graph Model option selectable")

        if layers_radio.is_visible():
            layers_radio.click()
            page.wait_for_timeout(500)

            layers_state = page.evaluate("""() => {
                const dialog = document.querySelector('[role="dialog"]');
                const text = dialog ? dialog.textContent : '';
                return {
                    text: text.substring(0, 500),
                    mentionsJson: text.includes('.json'),
                    mentionsBin: text.includes('.bin')
                };
            }""")
            log(f"  Layers Model format info: json={layers_state['mentionsJson']}, bin={layers_state['mentionsBin']}")
            record("cls_local_layers_format", "pass", "Layers Model option selectable")

    except Exception as e:
        record("cls_local_format_selection", "fail", f"Error: {e}")

    # Test "Select model files" - verify file chooser
    try:
        select_btn = page.locator("[role='dialog'] :text('Select model files')").first
        if select_btn.is_visible():
            with page.expect_file_chooser(timeout=5000) as fc_info:
                select_btn.click()
            fc = fc_info.value
            log(f"  File chooser: multiple={fc.is_multiple}")
            record("cls_local_file_select", "pass", f"File chooser works, multiple={fc.is_multiple}")
        else:
            record("cls_local_file_select", "warn", "Select model files link not visible")
    except Exception as e:
        record("cls_local_file_select", "fail", f"Error: {e}")

    # Check "OPEN CLASSIFICATION MODEL" button state (should be disabled without files)
    open_btn_state = page.evaluate("""() => {
        const dialog = document.querySelector('[role="dialog"]');
        if (!dialog) return {};
        const btn = Array.from(dialog.querySelectorAll('button')).find(
            b => b.textContent.includes('OPEN CLASSIFICATION')
        );
        return {
            text: btn ? btn.textContent.trim() : null,
            disabled: btn ? btn.disabled : null
        };
    }""")
    log(f"  Open Classification Model button: {json.dumps(open_btn_state)}")
    if open_btn_state.get('disabled') == True:
        record("cls_local_btn_disabled", "pass", "Open button correctly disabled without files selected")
    else:
        record("cls_local_btn_disabled", "warn", "Open button enabled without files - may cause error")

    page.keyboard.press("Escape")
    page.wait_for_timeout(500)


# ==================== SEGMENTATION MODELS ====================

def test_segmentation_load_model_dialog(page):
    """Test the segmentation Load Model dialog in detail"""
    log("=== TEST: Segmentation Load Model Dialog ===")

    load_mnist_project(page)

    # Switch to Segmentation tab
    seg_tab = page.query_selector("button:has-text('Segmentation')")
    if seg_tab:
        seg_tab.click()
        page.wait_for_timeout(1000)

    initial_state = get_model_state(page)
    log(f"  Initial seg model: {initial_state.get('selectedModel', 'N/A')}, kind: {initial_state.get('modelKind', 'N/A')}")

    # Click Load Model
    page.click("button:has-text('Load Model')", timeout=5000)
    page.wait_for_timeout(2000)
    screenshot(page, "M10_seg_load_dialog")

    # Inspect the dialog - segmentation has "LOAD PRETRAINED" tab and "Pre-trained Models" dropdown
    seg_dialog = page.evaluate("""() => {
        const dialog = document.querySelector('[role="dialog"]');
        if (!dialog) return { found: false };
        const tabs = Array.from(dialog.querySelectorAll('[role="tab"], button')).map(
            t => t.textContent.trim()
        ).filter(t => t);
        const selects = dialog.querySelectorAll('select, [role="listbox"], [role="combobox"], [class*="Select"]');
        const dropdowns = dialog.querySelectorAll('[class*="select"], [class*="Select"], [class*="dropdown"], [class*="Dropdown"]');
        const text = dialog.textContent;
        return {
            found: true,
            tabs: tabs,
            selectCount: selects.length,
            dropdownCount: dropdowns.length,
            text: text.substring(0, 800),
            hasPretrainedTab: text.includes('LOAD PRETRAINED') || text.includes('Load Pretrained'),
            hasPretrainedDropdown: text.includes('Pre-trained Models'),
            hasSelectModel: text.includes('Select a Model'),
            hasCloudWarning: text.includes('cloud') || text.includes('Cloud'),
            buttons: Array.from(dialog.querySelectorAll('button')).map(b => ({
                text: b.textContent.trim(),
                disabled: b.disabled
            }))
        };
    }""")
    log(f"  Seg dialog: {json.dumps(seg_dialog, indent=2)}")
    record("seg_load_dialog", "pass" if seg_dialog['found'] else "fail",
           f"pretrained={seg_dialog.get('hasPretrainedTab')}, dropdown={seg_dialog.get('hasPretrainedDropdown')}")


def test_segmentation_pretrained_models(page):
    """Test loading a pre-trained segmentation model"""
    log("=== TEST: Segmentation Pre-trained Model Loading ===")

    load_mnist_project(page)

    # Switch to Segmentation tab
    seg_tab = page.query_selector("button:has-text('Segmentation')")
    if seg_tab:
        seg_tab.click()
        page.wait_for_timeout(1000)

    # Open Load Model dialog
    page.click("button:has-text('Load Model')", timeout=5000)
    page.wait_for_timeout(2000)

    # Click on the "Pre-trained Models" dropdown to see available models
    try:
        # The dropdown might be a MUI Select component
        dropdown = page.locator("[role='dialog'] [class*='Select'], [role='dialog'] select, [role='dialog'] [role='combobox']").first
        if not dropdown.is_visible():
            # Try clicking text "Pre-trained Models" which might be the select trigger
            dropdown = page.locator("text=Pre-trained Models").first

        dropdown.click()
        page.wait_for_timeout(1500)
        screenshot(page, "M11_seg_pretrained_dropdown")

        # Check what options appeared
        options = page.evaluate("""() => {
            // MUI Select renders options in a portal/popover
            const listboxes = document.querySelectorAll('[role="listbox"], [role="presentation"] ul');
            const options = document.querySelectorAll('[role="option"], [class*="MenuItem"]');
            const visibleOptions = Array.from(options).filter(o => o.offsetParent !== null).map(o => ({
                text: o.textContent.trim().substring(0, 80),
                value: o.getAttribute('data-value') || ''
            }));
            return {
                listboxCount: listboxes.length,
                optionCount: visibleOptions.length,
                options: visibleOptions
            };
        }""")
        log(f"  Pre-trained model options: {json.dumps(options, indent=2)}")

        if options['options']:
            record("seg_pretrained_dropdown", "pass", f"Found {options['optionCount']} pretrained models: {[o['text'] for o in options['options'][:5]]}")

            # Select the first available model
            first_model = options['options'][0]
            log(f"  Selecting model: {first_model['text']}")

            # Click the option
            page.locator(f"[role='option']:has-text('{first_model['text'][:30]}')").first.click()
            page.wait_for_timeout(2000)
            screenshot(page, "M12_seg_model_selected")

            # Check if "OPEN SEGMENTATION MODEL" button is now enabled
            open_btn = page.evaluate("""() => {
                const dialog = document.querySelector('[role="dialog"]');
                if (!dialog) return {};
                const btn = Array.from(dialog.querySelectorAll('button')).find(
                    b => b.textContent.includes('OPEN SEGMENTATION')
                );
                return {
                    text: btn ? btn.textContent.trim() : null,
                    disabled: btn ? btn.disabled : null
                };
            }""")
            log(f"  Open Segmentation Model button: {json.dumps(open_btn)}")

            if open_btn.get('disabled') == False:
                # Click to load the model
                log("  Loading segmentation model...")
                page.locator("[role='dialog'] button:has-text('OPEN SEGMENTATION')").first.click()
                page.wait_for_timeout(20000)  # Models can take time to download
                screenshot(page, "M13_seg_model_loading")

                # Check for progress or completion
                load_result = page.evaluate("""() => {
                    const text = document.body.innerText;
                    const progress = document.querySelector('[role="progressbar"]');
                    const dialog = document.querySelector('[role="dialog"]');
                    return {
                        hasDialog: !!dialog,
                        hasProgress: !!progress,
                        hasError: text.toLowerCase().includes('error'),
                        bodyText: text.substring(0, 1500)
                    };
                }""")
                log(f"  Load result: dialog={load_result['hasDialog']}, progress={load_result['hasProgress']}, error={load_result['hasError']}")

                # Wait more if still loading
                if load_result['hasProgress']:
                    log("  Model still loading, waiting 30 more seconds...")
                    page.wait_for_timeout(30000)
                    screenshot(page, "M14_seg_model_progress")

                # Final state check
                page.wait_for_timeout(5000)
                final_state = get_model_state(page)
                log(f"  Final seg model: selected={final_state.get('selectedModel')}, kind={final_state.get('modelKind')}")
                screenshot(page, "M15_seg_model_final")

                if final_state.get('selectedModel') and final_state['selectedModel'] != 'No Selected Model':
                    record("seg_pretrained_load", "pass", f"Model loaded: {final_state['selectedModel']}, kind={final_state['modelKind']}")
                elif load_result['hasError']:
                    record("seg_pretrained_load", "fail", "Error loading segmentation model")
                    issue("high", "functionality", f"Segmentation model failed to load: {first_model['text']}")
                else:
                    record("seg_pretrained_load", "warn", "Model state unchanged after load attempt")
            else:
                record("seg_pretrained_load", "warn", "Open Segmentation Model button still disabled after selection")
        else:
            record("seg_pretrained_dropdown", "fail", "No pretrained models available in dropdown")
            issue("high", "functionality", "Segmentation pretrained models dropdown is empty")

    except Exception as e:
        record("seg_pretrained_dropdown", "fail", f"Error: {e}")
        screenshot(page, "M11_seg_dropdown_error")

    page.keyboard.press("Escape")
    page.wait_for_timeout(500)


def test_segmentation_tabs(page):
    """Check if segmentation dialog has Upload Local / other tabs besides Load Pretrained"""
    log("=== TEST: Segmentation Dialog Tabs ===")

    load_mnist_project(page)

    seg_tab = page.query_selector("button:has-text('Segmentation')")
    if seg_tab:
        seg_tab.click()
        page.wait_for_timeout(1000)

    page.click("button:has-text('Load Model')", timeout=5000)
    page.wait_for_timeout(2000)

    # Check all tabs in the dialog
    tabs = page.evaluate("""() => {
        const dialog = document.querySelector('[role="dialog"]');
        if (!dialog) return [];
        // Look for tab-like elements
        const tabElements = dialog.querySelectorAll('[role="tab"], [class*="Tab"]:not([class*="Table"])');
        const clickableHeaders = Array.from(dialog.querySelectorAll('button, [role="button"]'))
            .filter(b => b.offsetParent !== null);
        return {
            tabs: Array.from(tabElements).map(t => ({
                text: t.textContent.trim(),
                selected: t.getAttribute('aria-selected') === 'true' || t.classList.contains('Mui-selected'),
                role: t.getAttribute('role') || ''
            })),
            buttons: clickableHeaders.map(b => b.textContent.trim().substring(0, 40))
        };
    }""")
    log(f"  Segmentation dialog tabs: {json.dumps(tabs, indent=2)}")

    tab_names = [t['text'] for t in tabs.get('tabs', [])]
    has_load_pretrained = any('pretrained' in t.lower() or 'LOAD PRETRAINED' in t for t in tab_names)
    has_upload_local = any('upload' in t.lower() or 'local' in t.lower() for t in tab_names)
    has_fetch_remote = any('fetch' in t.lower() or 'remote' in t.lower() for t in tab_names)

    log(f"  Has Load Pretrained: {has_load_pretrained}")
    log(f"  Has Upload Local: {has_upload_local}")
    log(f"  Has Fetch Remote: {has_fetch_remote}")

    if not has_upload_local and not has_fetch_remote:
        issue("medium", "functionality",
              "Segmentation Load Model dialog only has 'Load Pretrained' tab - no option to upload a custom local model or fetch from URL")
        record("seg_dialog_tabs", "warn",
               f"Only Load Pretrained tab available. Tabs: {tab_names}")
    else:
        record("seg_dialog_tabs", "pass", f"Tabs: {tab_names}")

    # If there are other tabs, try clicking them
    for tab_name in tab_names:
        if 'pretrained' not in tab_name.lower():
            try:
                page.locator(f"[role='dialog'] :text('{tab_name}')").first.click()
                page.wait_for_timeout(1000)
                screenshot(page, f"M16_seg_tab_{tab_name[:15].replace(' ','_')}")
                log(f"  Clicked tab: {tab_name}")
            except:
                pass

    page.keyboard.press("Escape")
    page.wait_for_timeout(500)


def test_model_after_fit_predict(page):
    """After loading MNIST with Classification tab, try the Fit/Predict icon buttons"""
    log("=== TEST: Fit/Predict Icon Buttons ===")

    load_mnist_project(page)

    cls_tab = page.query_selector("button:has-text('Classification')")
    if cls_tab:
        cls_tab.click()
        page.wait_for_timeout(1000)

    # The 3 icons below "Model:" are likely: Fit (scatter), Predict (play arrow), Evaluate (bar chart)
    # They have no aria-label, so we need to find them by position
    icon_info = page.evaluate("""() => {
        // Find all SVG icon buttons near the "Model:" text
        const modelText = Array.from(document.querySelectorAll('*')).find(
            e => e.textContent.trim().startsWith('Model:') && e.children.length === 0
        );
        if (!modelText) return { found: false };

        const modelRect = modelText.getBoundingClientRect();
        // Look for icon buttons below the model text
        const btns = Array.from(document.querySelectorAll('button:has(svg), [role="button"]:has(svg)'));
        const nearbyBtns = btns.filter(b => {
            const r = b.getBoundingClientRect();
            return r.top > modelRect.bottom && r.top < modelRect.bottom + 80 &&
                   r.left < modelRect.right + 100;
        }).map(b => ({
            x: Math.round(b.getBoundingClientRect().x),
            y: Math.round(b.getBoundingClientRect().y),
            w: Math.round(b.getBoundingClientRect().width),
            h: Math.round(b.getBoundingClientRect().height),
            disabled: b.disabled || b.getAttribute('aria-disabled') === 'true',
            ariaLabel: b.getAttribute('aria-label') || '',
            title: b.getAttribute('title') || '',
            className: (b.className || '').toString().substring(0, 60)
        }));
        return { found: true, buttons: nearbyBtns };
    }""")
    log(f"  Model action buttons: {json.dumps(icon_info, indent=2)}")

    if icon_info.get('buttons'):
        enabled_btns = [b for b in icon_info['buttons'] if not b['disabled']]
        disabled_btns = [b for b in icon_info['buttons'] if b['disabled']]
        log(f"  Enabled: {len(enabled_btns)}, Disabled: {len(disabled_btns)}")

        # Try clicking the first enabled button (likely Fit or Predict)
        if enabled_btns:
            btn = enabled_btns[0]
            log(f"  Clicking first enabled icon button at ({btn['x']}, {btn['y']})")
            page.mouse.click(btn['x'] + btn['w']//2, btn['y'] + btn['h']//2)
            page.wait_for_timeout(5000)
            screenshot(page, "M20_after_icon_click")

            # Check what happened
            after_click = page.evaluate("""() => {
                const text = document.body.innerText;
                const progress = document.querySelector('[role="progressbar"]');
                const snackbar = document.querySelector('[class*="Snackbar"], [class*="snackbar"]');
                return {
                    hasProgress: !!progress,
                    hasSnackbar: !!snackbar,
                    snackbarText: snackbar ? snackbar.textContent.trim() : '',
                    hasError: text.includes('Error') || text.includes('error'),
                    bodyText: text.substring(0, 1000)
                };
            }""")
            log(f"  After click: progress={after_click['hasProgress']}, error={after_click['hasError']}")
            if after_click['hasProgress']:
                log("  Model training/predicting in progress, waiting...")
                page.wait_for_timeout(20000)
                screenshot(page, "M21_model_progress")
                record("model_action_click", "pass", "Model action triggered, showing progress")
            elif after_click['hasError']:
                record("model_action_click", "warn", "Model action triggered but error occurred")
            else:
                record("model_action_click", "pass", "Icon button clickable")
        else:
            record("model_action_click", "warn", "All model action buttons are disabled")
            issue("medium", "functionality", "All Fit/Predict/Evaluate buttons disabled on MNIST project")
    else:
        record("model_action_click", "fail", "Could not find model action buttons")


def main():
    log(f"Starting Piximi Model Loading tests: {URL}")

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
            test_classification_load_model_dialog(page)
            test_classification_local_upload(page)
            test_classification_fetch_remote_model(page)
            test_segmentation_load_model_dialog(page)
            test_segmentation_tabs(page)
            test_segmentation_pretrained_models(page)
            test_model_after_fit_predict(page)
        except Exception as e:
            log(f"FATAL ERROR: {e}")
            import traceback
            traceback.print_exc()
            screenshot(page, "M99_fatal_error")
        finally:
            screenshot(page, "M99_final")

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
