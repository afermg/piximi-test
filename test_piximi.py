#!/usr/bin/env python3
"""Automated browser testing for https://piximi-beta.vercel.app"""

import json
import os
import sys
import time
from playwright.sync_api import sync_playwright

SCREENSHOTS_DIR = "/Users/amunozgo/tmp/piximi_screenshots"
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

URL = "https://piximi-beta.vercel.app"
RESULTS = []

def log(msg):
    print(f"[TEST] {msg}", flush=True)

def record(test_name, status, detail=""):
    RESULTS.append({"test": test_name, "status": status, "detail": detail})
    symbol = "PASS" if status == "pass" else "FAIL" if status == "fail" else "WARN"
    log(f"[{symbol}] {test_name}: {detail}")

def screenshot(page, name):
    path = os.path.join(SCREENSHOTS_DIR, f"{name}.png")
    page.screenshot(path=path, full_page=False)
    log(f"Screenshot saved: {path}")
    return path

def test_initial_load(page):
    """Test 1: Page loads successfully"""
    log("--- Test: Initial Page Load ---")
    try:
        response = page.goto(URL, wait_until="networkidle", timeout=30000)
        if response and response.status == 200:
            record("initial_load", "pass", f"Status {response.status}")
        else:
            status = response.status if response else "no response"
            record("initial_load", "fail", f"Status {status}")
    except Exception as e:
        record("initial_load", "fail", str(e))

    screenshot(page, "01_initial_load")

    # Check page title
    title = page.title()
    log(f"Page title: '{title}'")
    if title:
        record("page_title", "pass", f"Title: '{title}'")
    else:
        record("page_title", "warn", "No page title set")

def test_console_errors(page):
    """Test 2: Check for console errors"""
    log("--- Test: Console Errors ---")
    errors = []
    warnings = []

    def on_console(msg):
        if msg.type == "error":
            errors.append(msg.text)
        elif msg.type == "warning":
            warnings.append(msg.text)

    page.on("console", on_console)
    page.reload(wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(3000)
    page.remove_listener("console", on_console)

    if errors:
        record("console_errors", "fail", f"{len(errors)} errors: {json.dumps(errors[:10], indent=2)}")
    else:
        record("console_errors", "pass", "No console errors")

    if warnings:
        record("console_warnings", "warn", f"{len(warnings)} warnings found")

def test_main_ui_elements(page):
    """Test 3: Check main UI elements render"""
    log("--- Test: Main UI Elements ---")
    screenshot(page, "02_main_ui")

    # Check for common UI elements
    checks = {
        "app_bar": "header, [class*='AppBar'], [class*='appbar'], [class*='toolbar'], nav, [role='banner']",
        "main_content": "main, [role='main'], [class*='content'], [class*='Content']",
        "buttons": "button",
        "images_or_canvas": "img, canvas, svg",
    }

    for name, selector in checks.items():
        try:
            elements = page.query_selector_all(selector)
            if elements:
                record(f"ui_{name}", "pass", f"Found {len(elements)} element(s)")
            else:
                record(f"ui_{name}", "warn", f"No elements matching: {selector}")
        except Exception as e:
            record(f"ui_{name}", "fail", str(e))

def test_navigation(page):
    """Test 4: Test navigation / sidebar / menu"""
    log("--- Test: Navigation ---")

    # Look for navigation elements, menus, sidebar
    nav_selectors = [
        "[class*='drawer']", "[class*='Drawer']",
        "[class*='sidebar']", "[class*='Sidebar']",
        "[class*='menu']", "[class*='Menu']",
        "nav", "[role='navigation']",
        "[class*='tab']", "[role='tablist']",
    ]

    for sel in nav_selectors:
        try:
            els = page.query_selector_all(sel)
            if els:
                log(f"  Found navigation element: {sel} ({len(els)} items)")
        except:
            pass

    # Try clicking hamburger/menu icon if present
    menu_selectors = [
        "[aria-label*='menu']", "[aria-label*='Menu']",
        "[class*='MenuIcon']", "[class*='hamburger']",
        "button svg", "[data-testid*='menu']",
    ]

    for sel in menu_selectors:
        try:
            btn = page.query_selector(sel)
            if btn and btn.is_visible():
                log(f"  Clicking menu element: {sel}")
                btn.click()
                page.wait_for_timeout(1000)
                screenshot(page, "03_after_menu_click")
                record("menu_interaction", "pass", f"Clicked {sel}")
                break
        except Exception as e:
            log(f"  Could not click {sel}: {e}")
    else:
        record("menu_interaction", "warn", "No clickable menu found")

def test_responsive_layout(page):
    """Test 5: Test responsive design at different viewport sizes"""
    log("--- Test: Responsive Layout ---")

    viewports = [
        ("mobile", 375, 812),
        ("tablet", 768, 1024),
        ("desktop", 1920, 1080),
    ]

    for name, w, h in viewports:
        try:
            page.set_viewport_size({"width": w, "height": h})
            page.wait_for_timeout(1000)
            screenshot(page, f"04_responsive_{name}_{w}x{h}")

            # Check for overflow
            has_h_scroll = page.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth")
            if has_h_scroll:
                record(f"responsive_{name}", "warn", f"Horizontal scrollbar at {w}x{h}")
            else:
                record(f"responsive_{name}", "pass", f"No overflow at {w}x{h}")
        except Exception as e:
            record(f"responsive_{name}", "fail", str(e))

    # Reset to desktop
    page.set_viewport_size({"width": 1280, "height": 720})

def test_links_and_buttons(page):
    """Test 6: Check all links and interactive elements"""
    log("--- Test: Links and Buttons ---")

    # Get all links
    links = page.evaluate("""() => {
        return Array.from(document.querySelectorAll('a[href]')).map(a => ({
            href: a.href,
            text: a.textContent.trim().substring(0, 50),
            visible: a.offsetParent !== null
        }))
    }""")
    log(f"  Found {len(links)} links")
    for link in links[:20]:
        log(f"    Link: '{link['text']}' -> {link['href']} (visible: {link['visible']})")

    # Get all buttons
    buttons = page.evaluate("""() => {
        return Array.from(document.querySelectorAll('button, [role="button"]')).map(b => ({
            text: (b.textContent || b.getAttribute('aria-label') || '').trim().substring(0, 50),
            disabled: b.disabled || b.getAttribute('aria-disabled') === 'true',
            visible: b.offsetParent !== null
        }))
    }""")
    log(f"  Found {len(buttons)} buttons")
    for btn in buttons[:20]:
        log(f"    Button: '{btn['text']}' (disabled: {btn['disabled']}, visible: {btn['visible']})")

    if links or buttons:
        record("interactive_elements", "pass", f"{len(links)} links, {len(buttons)} buttons")
    else:
        record("interactive_elements", "fail", "No interactive elements found")

def test_accessibility(page):
    """Test 7: Basic accessibility checks"""
    log("--- Test: Accessibility ---")

    # Check for alt text on images
    images_without_alt = page.evaluate("""() => {
        return Array.from(document.querySelectorAll('img')).filter(
            img => !img.alt && !img.getAttribute('aria-label') && !img.getAttribute('role')
        ).map(img => img.src.substring(0, 80))
    }""")
    if images_without_alt:
        record("img_alt_text", "fail", f"{len(images_without_alt)} images without alt text")
    else:
        record("img_alt_text", "pass", "All images have alt text (or no images)")

    # Check for form labels
    inputs_without_labels = page.evaluate("""() => {
        return Array.from(document.querySelectorAll('input, select, textarea')).filter(el => {
            const id = el.id;
            const hasLabel = id && document.querySelector(`label[for="${id}"]`);
            const hasAria = el.getAttribute('aria-label') || el.getAttribute('aria-labelledby');
            const hasPlaceholder = el.placeholder;
            return !hasLabel && !hasAria && !hasPlaceholder;
        }).length
    }""")
    if inputs_without_labels > 0:
        record("form_labels", "fail", f"{inputs_without_labels} inputs without labels")
    else:
        record("form_labels", "pass", "All form inputs have labels")

    # Check for ARIA landmarks
    landmarks = page.evaluate("""() => {
        const roles = ['banner', 'navigation', 'main', 'contentinfo'];
        const found = {};
        roles.forEach(r => {
            found[r] = document.querySelectorAll(`[role="${r}"]`).length +
                       document.querySelectorAll(r === 'banner' ? 'header' : r === 'contentinfo' ? 'footer' : r === 'navigation' ? 'nav' : 'main').length;
        });
        return found;
    }""")
    log(f"  ARIA landmarks: {json.dumps(landmarks)}")
    missing = [k for k, v in landmarks.items() if v == 0]
    if missing:
        record("aria_landmarks", "warn", f"Missing landmarks: {', '.join(missing)}")
    else:
        record("aria_landmarks", "pass", "All major landmarks present")

    # Check color contrast - basic tab-index check
    focusable = page.evaluate("""() => {
        const els = document.querySelectorAll('[tabindex]');
        const negative = Array.from(els).filter(el => parseInt(el.getAttribute('tabindex')) < 0);
        return { total: els.length, negative: negative.length };
    }""")
    if focusable['negative'] > 5:
        record("tabindex", "warn", f"{focusable['negative']} elements with negative tabindex (may be inaccessible via keyboard)")
    else:
        record("tabindex", "pass", f"Tabindex looks reasonable ({focusable['total']} total, {focusable['negative']} negative)")

def test_performance(page):
    """Test 8: Basic performance metrics"""
    log("--- Test: Performance ---")

    metrics = page.evaluate("""() => {
        const perf = performance.getEntriesByType('navigation')[0];
        if (!perf) return null;
        return {
            dns: Math.round(perf.domainLookupEnd - perf.domainLookupStart),
            connect: Math.round(perf.connectEnd - perf.connectStart),
            ttfb: Math.round(perf.responseStart - perf.requestStart),
            domContentLoaded: Math.round(perf.domContentLoadedEventEnd - perf.navigationStart),
            load: Math.round(perf.loadEventEnd - perf.navigationStart),
            domInteractive: Math.round(perf.domInteractive - perf.navigationStart),
            transferSize: perf.transferSize || 0,
        }
    }""")

    if metrics:
        log(f"  Performance metrics: {json.dumps(metrics, indent=2)}")

        if metrics.get('load', 0) > 10000:
            record("load_time", "fail", f"Page load: {metrics['load']}ms (>10s)")
        elif metrics.get('load', 0) > 5000:
            record("load_time", "warn", f"Page load: {metrics['load']}ms (>5s)")
        else:
            record("load_time", "pass", f"Page load: {metrics['load']}ms")

        if metrics.get('domContentLoaded', 0) > 5000:
            record("dom_content_loaded", "warn", f"DOMContentLoaded: {metrics['domContentLoaded']}ms")
        else:
            record("dom_content_loaded", "pass", f"DOMContentLoaded: {metrics['domContentLoaded']}ms")
    else:
        record("performance", "warn", "Could not retrieve performance metrics")

def test_network_errors(page):
    """Test 9: Check for failed network requests"""
    log("--- Test: Network Errors ---")

    failed_requests = []

    def on_response(response):
        if response.status >= 400:
            failed_requests.append({
                "url": response.url[:100],
                "status": response.status
            })

    page.on("response", on_response)
    page.reload(wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(3000)
    page.remove_listener("response", on_response)

    if failed_requests:
        record("network_errors", "fail", f"{len(failed_requests)} failed requests: {json.dumps(failed_requests[:10], indent=2)}")
    else:
        record("network_errors", "pass", "No failed network requests")

def test_click_through_features(page):
    """Test 10: Try interacting with app features"""
    log("--- Test: Feature Click-through ---")

    page.goto(URL, wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(3000)
    screenshot(page, "05_before_interactions")

    # Try to find and interact with key features
    # Look for "Open" or "New" project buttons
    action_buttons = page.evaluate("""() => {
        const btns = Array.from(document.querySelectorAll('button, [role="button"], a'));
        return btns.map(b => ({
            tag: b.tagName,
            text: (b.textContent || '').trim().substring(0, 60),
            ariaLabel: b.getAttribute('aria-label') || '',
            visible: b.offsetParent !== null,
            class: (b.className || '').toString().substring(0, 80)
        })).filter(b => b.visible);
    }""")

    log(f"  Visible interactive elements: {len(action_buttons)}")
    for btn in action_buttons[:30]:
        log(f"    [{btn['tag']}] text='{btn['text']}' aria='{btn['ariaLabel']}' class='{btn['class'][:40]}'")

    # Try clicking on "Open" or "New Project" style buttons
    open_keywords = ['open', 'new', 'create', 'import', 'upload', 'start', 'add']
    clicked = False
    for kw in open_keywords:
        try:
            btn = page.query_selector(f"button:has-text('{kw}'), [role='button']:has-text('{kw}')")
            if btn and btn.is_visible():
                log(f"  Clicking button with text containing '{kw}'")
                btn.click()
                page.wait_for_timeout(2000)
                screenshot(page, f"06_after_click_{kw}")
                record(f"feature_{kw}", "pass", f"Clicked '{kw}' button successfully")
                clicked = True
                break
        except Exception as e:
            log(f"  Could not click '{kw}': {e}")

    if not clicked:
        record("feature_click", "warn", "Could not find action buttons to click")

    # Check for dialogs/modals that might have appeared
    dialogs = page.query_selector_all("[role='dialog'], [class*='modal'], [class*='Modal'], [class*='dialog'], [class*='Dialog']")
    if dialogs:
        log(f"  Found {len(dialogs)} dialog/modal elements")
        screenshot(page, "07_dialog")

def test_file_upload(page):
    """Test 11: Check if file upload functionality exists and is accessible"""
    log("--- Test: File Upload ---")

    file_inputs = page.query_selector_all("input[type='file']")
    log(f"  Found {len(file_inputs)} file input elements")

    drop_zones = page.query_selector_all("[class*='drop'], [class*='Drop'], [class*='upload'], [class*='Upload']")
    log(f"  Found {len(drop_zones)} drop zone elements")

    if file_inputs or drop_zones:
        record("file_upload", "pass", f"{len(file_inputs)} file inputs, {len(drop_zones)} drop zones")
    else:
        record("file_upload", "warn", "No visible file upload mechanism found")

def test_error_boundaries(page):
    """Test 12: Check for visible error messages"""
    log("--- Test: Error Boundaries ---")

    error_elements = page.evaluate("""() => {
        const selectors = [
            '[class*="error"]', '[class*="Error"]',
            '[class*="alert"]', '[class*="Alert"]',
            '[role="alert"]',
            '[class*="warning"]', '[class*="Warning"]',
            '[class*="crash"]', '[class*="Crash"]',
        ];
        const results = [];
        selectors.forEach(sel => {
            document.querySelectorAll(sel).forEach(el => {
                if (el.offsetParent !== null && el.textContent.trim()) {
                    results.push({
                        selector: sel,
                        text: el.textContent.trim().substring(0, 200)
                    });
                }
            });
        });
        return results;
    }""")

    if error_elements:
        record("visible_errors", "fail", f"{len(error_elements)} visible error elements: {json.dumps(error_elements[:5], indent=2)}")
    else:
        record("visible_errors", "pass", "No visible error messages")

def main():
    log(f"Starting Piximi browser tests: {URL}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        # Collect console errors throughout
        all_console_errors = []
        def global_console(msg):
            if msg.type == "error":
                all_console_errors.append(msg.text)
        page.on("console", global_console)

        try:
            test_initial_load(page)
            test_console_errors(page)
            test_main_ui_elements(page)
            test_links_and_buttons(page)
            test_navigation(page)
            test_responsive_layout(page)
            test_accessibility(page)
            test_performance(page)
            test_network_errors(page)
            test_click_through_features(page)
            test_file_upload(page)
            test_error_boundaries(page)
        except Exception as e:
            log(f"FATAL ERROR: {e}")
            screenshot(page, "99_fatal_error")
        finally:
            # Final full-page screenshot
            screenshot(page, "99_final_state")

            log(f"\n{'='*60}")
            log(f"All console errors collected: {len(all_console_errors)}")
            for err in all_console_errors[:20]:
                log(f"  CONSOLE ERROR: {err[:200]}")

            log(f"\n{'='*60}")
            log("TEST SUMMARY")
            log(f"{'='*60}")
            passes = sum(1 for r in RESULTS if r['status'] == 'pass')
            fails = sum(1 for r in RESULTS if r['status'] == 'fail')
            warns = sum(1 for r in RESULTS if r['status'] == 'warn')
            log(f"Total: {len(RESULTS)} | Pass: {passes} | Fail: {fails} | Warn: {warns}")
            log(f"{'='*60}")
            for r in RESULTS:
                symbol = {"pass": "✓", "fail": "✗", "warn": "⚠"}[r['status']]
                log(f"  {symbol} {r['test']}: {r['detail'][:120]}")
            log(f"{'='*60}")

        browser.close()

if __name__ == "__main__":
    main()
