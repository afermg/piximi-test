#!/usr/bin/env python3
"""Deep interaction testing for https://piximi-beta.vercel.app"""

import json
import os
import time
from playwright.sync_api import sync_playwright

SCREENSHOTS_DIR = "/Users/amunozgo/tmp/piximi_screenshots"
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

URL = "https://piximi-beta.vercel.app"
ISSUES = []
console_errors = []
console_warnings = []

def log(msg):
    print(f"[TEST] {msg}", flush=True)

def issue(severity, category, description):
    ISSUES.append({"severity": severity, "category": category, "description": description})
    log(f"[{severity.upper()}] [{category}] {description}")

def screenshot(page, name):
    path = os.path.join(SCREENSHOTS_DIR, f"{name}.png")
    page.screenshot(path=path, full_page=False)
    log(f"Screenshot: {path}")
    return path

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
        page = context.new_page()

        def on_console(msg):
            if msg.type == "error":
                console_errors.append(msg.text)
            elif msg.type == "warning":
                console_warnings.append(msg.text)
        page.on("console", on_console)

        # ===================== PHASE 1: Open Example Project =====================
        log("=== PHASE 1: Open MNIST Example Project ===")
        page.goto(URL, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(2000)

        # Click "Open Example Project"
        page.click("button:has-text('Open Example Project')")
        page.wait_for_timeout(1000)
        screenshot(page, "10_example_dialog")

        # Click on MNIST project
        try:
            page.click("text=MNIST example project", timeout=5000)
            page.wait_for_timeout(5000)
            screenshot(page, "11_mnist_loading")
            page.wait_for_timeout(10000)  # Give it time to load images
            screenshot(page, "12_mnist_loaded")
            log("MNIST project loaded")
        except Exception as e:
            issue("high", "functionality", f"Could not open MNIST example project: {e}")
            screenshot(page, "11_mnist_error")

        # ===================== PHASE 2: Inspect Main Workspace =====================
        log("=== PHASE 2: Inspect Main Workspace ===")

        # Get all visible text and elements
        page_info = page.evaluate("""() => {
            const allText = document.body.innerText.substring(0, 3000);
            const buttons = Array.from(document.querySelectorAll('button, [role="button"]'))
                .filter(b => b.offsetParent !== null)
                .map(b => ({
                    text: (b.textContent || b.getAttribute('aria-label') || '').trim().substring(0, 60),
                    disabled: b.disabled
                }));
            const inputs = Array.from(document.querySelectorAll('input, select, textarea'))
                .map(i => ({
                    type: i.type,
                    placeholder: i.placeholder || '',
                    value: i.value || '',
                    visible: i.offsetParent !== null
                }));
            const images = document.querySelectorAll('img').length;
            const canvases = document.querySelectorAll('canvas').length;
            return { allText, buttons, inputs, images, canvases };
        }""")

        log(f"  Page text (truncated): {page_info['allText'][:500]}")
        log(f"  Visible buttons: {len(page_info['buttons'])}")
        for btn in page_info['buttons'][:15]:
            log(f"    Button: '{btn['text']}' disabled={btn['disabled']}")
        log(f"  Inputs: {len(page_info['inputs'])}")
        log(f"  Images: {page_info['images']}, Canvases: {page_info['canvases']}")

        # ===================== PHASE 3: Check Sidebar / Categories =====================
        log("=== PHASE 3: Categories & Sidebar ===")

        # Look for category-related elements
        categories = page.evaluate("""() => {
            const els = document.querySelectorAll('[class*="category"], [class*="Category"], [class*="class"], [class*="Class"]');
            return Array.from(els).filter(e => e.offsetParent !== null).map(e => e.textContent.trim().substring(0, 80));
        }""")
        log(f"  Category elements: {len(categories)}")
        for cat in categories[:10]:
            log(f"    Category: '{cat}'")

        # Try to find and click on sidebar or drawer toggle
        drawer_toggles = page.query_selector_all("[aria-label*='drawer'], [aria-label*='Drawer'], [class*='drawer'], [data-testid*='drawer']")
        log(f"  Drawer toggles found: {len(drawer_toggles)}")

        # ===================== PHASE 4: Test "Start New Project" Flow =====================
        log("=== PHASE 4: Start New Project Flow ===")

        # Navigate back to home
        page.goto(URL, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(2000)

        # Click "Start New Project"
        try:
            page.click("button:has-text('Start New Project')", timeout=5000)
            page.wait_for_timeout(3000)
            screenshot(page, "13_new_project")
            log("New project created/opened")

            # Check the workspace state
            workspace_info = page.evaluate("""() => {
                return {
                    url: window.location.href,
                    title: document.title,
                    hasToolbar: !!document.querySelector('[class*="toolbar"], [class*="Toolbar"], [role="toolbar"]'),
                    hasCanvas: !!document.querySelector('canvas'),
                    buttonCount: document.querySelectorAll('button').length,
                    visibleText: document.body.innerText.substring(0, 1000)
                };
            }""")
            log(f"  URL after new project: {workspace_info['url']}")
            log(f"  Has toolbar: {workspace_info['hasToolbar']}")
            log(f"  Has canvas: {workspace_info['hasCanvas']}")
            log(f"  Button count: {workspace_info['buttonCount']}")
        except Exception as e:
            issue("high", "functionality", f"Could not start new project: {e}")

        # ===================== PHASE 5: Test Upload Project Flow =====================
        log("=== PHASE 5: Upload Project Flow ===")
        page.goto(URL, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(2000)

        try:
            page.click("button:has-text('Upload Project')", timeout=5000)
            page.wait_for_timeout(2000)
            screenshot(page, "14_upload_dialog")

            # Check what dialog/UI appeared
            upload_ui = page.evaluate("""() => {
                const dialogs = document.querySelectorAll('[role="dialog"], [class*="modal"], [class*="Modal"]');
                const fileInputs = document.querySelectorAll('input[type="file"]');
                return {
                    dialogCount: dialogs.length,
                    fileInputCount: fileInputs.length,
                    dialogText: dialogs.length > 0 ? dialogs[0].textContent.substring(0, 300) : ''
                };
            }""")
            log(f"  Upload dialogs: {upload_ui['dialogCount']}")
            log(f"  File inputs: {upload_ui['fileInputCount']}")
            log(f"  Dialog text: {upload_ui['dialogText'][:200]}")
        except Exception as e:
            issue("medium", "functionality", f"Upload project flow issue: {e}")

        # ===================== PHASE 6: Test within the workspace =====================
        log("=== PHASE 6: Deep Workspace Testing ===")

        # Go back and open MNIST
        page.goto(URL, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(2000)
        page.click("button:has-text('Open Example Project')")
        page.wait_for_timeout(1000)

        try:
            page.click("text=MNIST example project", timeout=5000)
            page.wait_for_timeout(15000)  # Wait for project to fully load
            screenshot(page, "15_workspace_full")

            # Look at all UI elements in the workspace
            workspace = page.evaluate("""() => {
                const allBtns = Array.from(document.querySelectorAll('button, [role="button"], [class*="IconButton"]'))
                    .filter(b => b.offsetParent !== null)
                    .map(b => ({
                        text: (b.textContent || '').trim().substring(0, 40),
                        ariaLabel: b.getAttribute('aria-label') || '',
                        title: b.getAttribute('title') || '',
                        className: (b.className || '').toString().substring(0, 60)
                    }));
                const tabs = Array.from(document.querySelectorAll('[role="tab"]'))
                    .map(t => t.textContent.trim());
                const lists = Array.from(document.querySelectorAll('[role="listbox"], [role="list"], ul, ol'))
                    .filter(l => l.offsetParent !== null).length;
                const tooltips = Array.from(document.querySelectorAll('[class*="tooltip"], [class*="Tooltip"]'))
                    .length;
                return { allBtns, tabs, lists, tooltips };
            }""")

            log(f"  Workspace buttons: {len(workspace['allBtns'])}")
            for btn in workspace['allBtns'][:25]:
                log(f"    Btn: text='{btn['text']}' aria='{btn['ariaLabel']}' title='{btn['title']}'")
            log(f"  Tabs: {workspace['tabs']}")
            log(f"  Lists: {workspace['lists']}")

            # Try to find and click on menus in the workspace
            # Look for File/Edit/Help type menus
            menu_items = page.evaluate("""() => {
                return Array.from(document.querySelectorAll('[class*="MenuItem"], [role="menuitem"], [class*="ListItem"]'))
                    .filter(m => m.offsetParent !== null)
                    .map(m => m.textContent.trim().substring(0, 50));
            }""")
            log(f"  Menu items: {menu_items[:20]}")

            # Test: Try clicking some toolbar buttons
            toolbar_btns = page.query_selector_all("[aria-label]")
            for btn in toolbar_btns[:5]:
                label = btn.get_attribute("aria-label")
                if label and btn.is_visible():
                    log(f"  Trying to click aria-label='{label}'")
                    try:
                        btn.click()
                        page.wait_for_timeout(1000)
                        screenshot(page, f"16_after_click_{label[:20].replace(' ','_')}")
                    except Exception as e:
                        log(f"    Error clicking: {e}")
                    break

        except Exception as e:
            issue("high", "functionality", f"Could not explore workspace: {e}")
            screenshot(page, "15_workspace_error")

        # ===================== PHASE 7: Test keyboard navigation =====================
        log("=== PHASE 7: Keyboard Navigation ===")
        try:
            page.goto(URL, wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(2000)

            # Tab through elements
            focused_elements = []
            for i in range(10):
                page.keyboard.press("Tab")
                page.wait_for_timeout(300)
                focused = page.evaluate("""() => {
                    const el = document.activeElement;
                    return {
                        tag: el.tagName,
                        text: (el.textContent || el.getAttribute('aria-label') || '').trim().substring(0, 50),
                        hasVisibleFocus: window.getComputedStyle(el).outlineStyle !== 'none' ||
                                        window.getComputedStyle(el).boxShadow !== 'none'
                    };
                }""")
                focused_elements.append(focused)

            log(f"  Tab navigation sequence:")
            for i, el in enumerate(focused_elements):
                log(f"    Tab {i+1}: <{el['tag']}> '{el['text']}' focusVisible={el['hasVisibleFocus']}")

            # Check if focus is visually indicated
            no_visible_focus = sum(1 for el in focused_elements if not el['hasVisibleFocus'] and el['tag'] != 'BODY')
            if no_visible_focus > 3:
                issue("medium", "accessibility", f"{no_visible_focus}/10 tabbed elements lack visible focus indicator")

        except Exception as e:
            issue("low", "accessibility", f"Keyboard navigation test failed: {e}")

        # ===================== PHASE 8: Check for broken images =====================
        log("=== PHASE 8: Broken Images ===")
        page.goto(URL, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(2000)
        page.click("button:has-text('Open Example Project')")
        page.wait_for_timeout(1000)

        broken_images = page.evaluate("""() => {
            return Array.from(document.querySelectorAll('img')).filter(img => {
                return !img.complete || img.naturalWidth === 0;
            }).map(img => img.src.substring(0, 100));
        }""")
        if broken_images:
            issue("high", "visual", f"Broken images found: {json.dumps(broken_images)}")
        else:
            log("  No broken images found in example dialog")

        # ===================== PHASE 9: Test "Image and Object Sets" tab =====================
        log("=== PHASE 9: Image and Object Sets Tab ===")
        try:
            page.click("text=IMAGE AND OBJECT SETS", timeout=3000)
            page.wait_for_timeout(2000)
            screenshot(page, "17_object_sets_tab")

            obj_items = page.evaluate("""() => {
                const dialog = document.querySelector('[role="dialog"]');
                if (!dialog) return [];
                return Array.from(dialog.querySelectorAll('h5, h6, [class*="title"], [class*="Title"]'))
                    .map(e => e.textContent.trim().substring(0, 80));
            }""")
            log(f"  Object sets items: {obj_items}")
        except Exception as e:
            issue("medium", "functionality", f"Could not switch to Object Sets tab: {e}")

        # Close dialog
        try:
            close_btn = page.query_selector("[aria-label='close'], [aria-label='Close'], button:has-text('×')")
            if close_btn:
                close_btn.click()
                page.wait_for_timeout(500)
        except:
            page.keyboard.press("Escape")
            page.wait_for_timeout(500)

        # ===================== PHASE 10: Mobile usability deep test =====================
        log("=== PHASE 10: Mobile Usability ===")
        page.set_viewport_size({"width": 375, "height": 812})
        page.goto(URL, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(2000)
        screenshot(page, "18_mobile_home")

        # Check button sizes for touch targets
        touch_issues = page.evaluate("""() => {
            const btns = Array.from(document.querySelectorAll('button, a, [role="button"]'));
            const small = btns.filter(b => {
                const rect = b.getBoundingClientRect();
                return b.offsetParent !== null && (rect.width < 44 || rect.height < 44);
            });
            return small.map(b => ({
                text: (b.textContent || b.getAttribute('aria-label') || '').trim().substring(0, 40),
                width: Math.round(b.getBoundingClientRect().width),
                height: Math.round(b.getBoundingClientRect().height)
            }));
        }""")
        if touch_issues:
            issue("medium", "mobile", f"{len(touch_issues)} buttons below 44px minimum touch target")
            for t in touch_issues[:5]:
                log(f"    Small touch target: '{t['text']}' ({t['width']}x{t['height']}px)")

        # Open example project on mobile
        try:
            page.click("button:has-text('Open Example Project')", timeout=3000)
            page.wait_for_timeout(1000)
            screenshot(page, "19_mobile_dialog")

            # Check if dialog is properly sized for mobile
            dialog_overflow = page.evaluate("""() => {
                const dialog = document.querySelector('[role="dialog"], [class*="Modal"]');
                if (!dialog) return null;
                const rect = dialog.getBoundingClientRect();
                return {
                    width: Math.round(rect.width),
                    height: Math.round(rect.height),
                    exceedsViewport: rect.width > window.innerWidth || rect.height > window.innerHeight,
                    rightEdge: Math.round(rect.right),
                    viewportWidth: window.innerWidth
                };
            }""")
            if dialog_overflow:
                log(f"  Dialog size on mobile: {dialog_overflow['width']}x{dialog_overflow['height']}")
                if dialog_overflow['exceedsViewport']:
                    issue("high", "mobile", f"Dialog exceeds viewport on mobile ({dialog_overflow['width']}x{dialog_overflow['height']})")
        except Exception as e:
            log(f"  Mobile dialog test failed: {e}")

        # Reset viewport
        page.set_viewport_size({"width": 1280, "height": 720})

        # ===================== PHASE 11: Check meta tags and SEO basics =====================
        log("=== PHASE 11: Meta Tags & SEO ===")
        page.goto(URL, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(2000)

        meta_info = page.evaluate("""() => {
            const getMeta = (name) => {
                const el = document.querySelector(`meta[name="${name}"], meta[property="${name}"]`);
                return el ? el.content : null;
            };
            return {
                description: getMeta('description'),
                ogTitle: getMeta('og:title'),
                ogDescription: getMeta('og:description'),
                ogImage: getMeta('og:image'),
                viewport: getMeta('viewport'),
                charset: document.characterSet,
                lang: document.documentElement.lang,
                favicon: !!document.querySelector('link[rel="icon"], link[rel="shortcut icon"]')
            };
        }""")
        log(f"  Meta info: {json.dumps(meta_info, indent=2)}")

        if not meta_info.get('description'):
            issue("low", "seo", "Missing meta description")
        if not meta_info.get('ogTitle'):
            issue("low", "seo", "Missing Open Graph title (og:title)")
        if not meta_info.get('ogDescription'):
            issue("low", "seo", "Missing Open Graph description (og:description)")
        if not meta_info.get('ogImage'):
            issue("low", "seo", "Missing Open Graph image (og:image)")
        if not meta_info.get('lang'):
            issue("medium", "accessibility", "Missing lang attribute on <html> element")

        # ===================== FINAL SUMMARY =====================
        log(f"\n{'='*70}")
        log("CONSOLE ERRORS COLLECTED DURING ALL TESTS")
        log(f"{'='*70}")
        for err in console_errors[:30]:
            log(f"  ERROR: {err[:200]}")
        log(f"  Total errors: {len(console_errors)}")

        log(f"\nCONSOLE WARNINGS: {len(console_warnings)}")
        for w in console_warnings[:10]:
            log(f"  WARN: {w[:200]}")

        log(f"\n{'='*70}")
        log("ALL ISSUES FOUND")
        log(f"{'='*70}")
        for i, iss in enumerate(ISSUES, 1):
            log(f"  {i}. [{iss['severity'].upper()}] [{iss['category']}] {iss['description']}")
        log(f"{'='*70}")
        log(f"Total issues: {len(ISSUES)}")

        browser.close()

if __name__ == "__main__":
    main()
