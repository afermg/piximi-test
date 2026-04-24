#!/usr/bin/env python3
"""Final targeted tests for piximi-beta"""

import json
import os
import time
from playwright.sync_api import sync_playwright

SCREENSHOTS_DIR = "/Users/amunozgo/tmp/piximi_screenshots"
URL = "https://piximi-beta.vercel.app"

def log(msg):
    print(f"[TEST] {msg}", flush=True)

def screenshot(page, name):
    path = os.path.join(SCREENSHOTS_DIR, f"{name}.png")
    page.screenshot(path=path, full_page=False)
    return path

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # ===================== TEST: Mobile dialog overlap =====================
        log("=== Mobile Dialog Overlap Test ===")
        context = browser.new_context(viewport={"width": 375, "height": 812})
        page = context.new_page()
        page.goto(URL, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(2000)
        page.click("button:has-text('Open Example Project')")
        page.wait_for_timeout(1500)

        # Check for text overlap in dialog on mobile
        overlap_info = page.evaluate("""() => {
            const items = document.querySelectorAll('[role="dialog"] li, [role="dialog"] [class*="item"], [role="dialog"] [class*="Item"]');
            const rects = [];
            items.forEach(item => {
                if (item.offsetParent !== null) {
                    const rect = item.getBoundingClientRect();
                    rects.push({
                        text: item.textContent.trim().substring(0, 40),
                        top: Math.round(rect.top),
                        bottom: Math.round(rect.bottom),
                        height: Math.round(rect.height)
                    });
                }
            });
            // Check overlaps
            const overlaps = [];
            for (let i = 0; i < rects.length; i++) {
                for (let j = i + 1; j < rects.length; j++) {
                    if (rects[i].bottom > rects[j].top && rects[i].top < rects[j].bottom) {
                        overlaps.push({
                            item1: rects[i].text,
                            item2: rects[j].text,
                            overlapPx: Math.min(rects[i].bottom, rects[j].bottom) - Math.max(rects[i].top, rects[j].top)
                        });
                    }
                }
            }
            return { items: rects, overlaps };
        }""")
        log(f"  Dialog items: {len(overlap_info['items'])}")
        for item in overlap_info['items']:
            log(f"    Item: '{item['text']}' top={item['top']} bottom={item['bottom']} height={item['height']}")
        log(f"  Overlaps detected: {len(overlap_info['overlaps'])}")
        for ov in overlap_info['overlaps']:
            log(f"    OVERLAP: '{ov['item1']}' and '{ov['item2']}' by {ov['overlapPx']}px")

        # Scroll the dialog to check all items
        screenshot(page, "20_mobile_dialog_scroll")
        context.close()

        # ===================== TEST: Workspace on mobile =====================
        log("=== Mobile Workspace Test ===")
        context = browser.new_context(viewport={"width": 375, "height": 812})
        page = context.new_page()
        page.goto(URL, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(2000)
        page.click("button:has-text('Start New Project')")
        page.wait_for_timeout(3000)
        screenshot(page, "21_mobile_workspace")

        mobile_workspace = page.evaluate("""() => {
            const hasHScroll = document.documentElement.scrollWidth > document.documentElement.clientWidth;
            const sidebar = document.querySelector('[class*="drawer"], [class*="Drawer"], [class*="sidebar"]');
            const sidebarVisible = sidebar ? sidebar.offsetParent !== null : false;
            const sidebarWidth = sidebar ? sidebar.getBoundingClientRect().width : 0;
            const bodyWidth = document.body.clientWidth;
            // Check if sidebar takes up too much space
            return {
                hasHScroll,
                sidebarVisible,
                sidebarWidth: Math.round(sidebarWidth),
                bodyWidth,
                sidebarPercent: sidebar ? Math.round((sidebarWidth / bodyWidth) * 100) : 0
            };
        }""")
        log(f"  Mobile workspace: {json.dumps(mobile_workspace)}")
        context.close()

        # ===================== TEST: Buttons without labels =====================
        log("=== Unlabeled Buttons Test ===")
        context = browser.new_context(viewport={"width": 1280, "height": 720})
        page = context.new_page()
        page.goto(URL, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(2000)
        page.click("button:has-text('Start New Project')")
        page.wait_for_timeout(3000)

        unlabeled = page.evaluate("""() => {
            const btns = Array.from(document.querySelectorAll('button, [role="button"]'));
            return btns.filter(b => {
                const text = (b.textContent || '').trim();
                const aria = b.getAttribute('aria-label') || '';
                const title = b.getAttribute('title') || '';
                return b.offsetParent !== null && !text && !aria && !title;
            }).map(b => ({
                className: (b.className || '').toString().substring(0, 80),
                innerHTML: b.innerHTML.substring(0, 100),
                hasSvg: !!b.querySelector('svg'),
                disabled: b.disabled
            }));
        }""")
        log(f"  Unlabeled visible buttons: {len(unlabeled)}")
        for btn in unlabeled:
            log(f"    Unlabeled btn: class='{btn['className'][:50]}' hasSvg={btn['hasSvg']} disabled={btn['disabled']}")

        # ===================== TEST: Disabled buttons that look enabled =====================
        log("=== Disabled Button Clarity Test ===")
        disabled_btns = page.evaluate("""() => {
            const btns = Array.from(document.querySelectorAll('button[disabled], [aria-disabled="true"]'));
            return btns.filter(b => b.offsetParent !== null).map(b => {
                const style = window.getComputedStyle(b);
                return {
                    text: (b.textContent || b.getAttribute('aria-label') || '').trim().substring(0, 40),
                    opacity: style.opacity,
                    cursor: style.cursor,
                    color: style.color
                };
            });
        }""")
        log(f"  Disabled buttons: {len(disabled_btns)}")
        for btn in disabled_btns:
            log(f"    Disabled: '{btn['text']}' opacity={btn['opacity']} cursor={btn['cursor']}")

        # ===================== TEST: Save with no data =====================
        log("=== Save With No Data Test ===")
        try:
            save_btn = page.query_selector("button:has-text('Save')")
            if save_btn and save_btn.is_visible():
                save_btn.click()
                page.wait_for_timeout(2000)
                screenshot(page, "22_save_empty_project")

                # Check what happened - dialog, download, error?
                save_result = page.evaluate("""() => {
                    const dialogs = document.querySelectorAll('[role="dialog"]');
                    const alerts = document.querySelectorAll('[role="alert"]');
                    const snackbars = document.querySelectorAll('[class*="snackbar"], [class*="Snackbar"], [class*="toast"], [class*="Toast"]');
                    return {
                        dialogs: dialogs.length,
                        alerts: alerts.length,
                        snackbars: snackbars.length,
                        dialogText: dialogs.length > 0 ? dialogs[0].textContent.substring(0, 200) : ''
                    };
                }""")
                log(f"  Save result: {json.dumps(save_result)}")
        except Exception as e:
            log(f"  Save test error: {e}")

        # ===================== TEST: Settings dialog =====================
        log("=== Settings Dialog Test ===")
        try:
            settings_btn = page.query_selector("[aria-label='Settings']")
            if settings_btn and settings_btn.is_visible():
                settings_btn.click()
                page.wait_for_timeout(1500)
                screenshot(page, "23_settings")

                settings_content = page.evaluate("""() => {
                    const dialog = document.querySelector('[role="dialog"]');
                    return dialog ? dialog.textContent.substring(0, 500) : 'No dialog found';
                }""")
                log(f"  Settings content: {settings_content[:300]}")

                # Close settings
                page.keyboard.press("Escape")
                page.wait_for_timeout(500)
        except Exception as e:
            log(f"  Settings test error: {e}")

        # ===================== TEST: Send Feedback dialog =====================
        log("=== Feedback Dialog Test ===")
        try:
            feedback_btn = page.query_selector("[aria-label='Send Feedback']")
            if feedback_btn and feedback_btn.is_visible():
                feedback_btn.click()
                page.wait_for_timeout(1500)
                screenshot(page, "24_feedback")
                page.keyboard.press("Escape")
                page.wait_for_timeout(500)
        except Exception as e:
            log(f"  Feedback test error: {e}")

        # ===================== TEST: Help mode toggle =====================
        log("=== Help Mode Test ===")
        try:
            help_btn = page.query_selector("[aria-label='Toggle Help Mode']")
            if help_btn and help_btn.is_visible():
                help_btn.click()
                page.wait_for_timeout(1500)
                screenshot(page, "25_help_mode")

                # Check if tooltips or help overlays appeared
                help_ui = page.evaluate("""() => {
                    const tooltips = document.querySelectorAll('[class*="tooltip"], [class*="Tooltip"], [class*="help"], [class*="Help"]');
                    return {
                        tooltipCount: tooltips.length,
                        texts: Array.from(tooltips).filter(t => t.offsetParent !== null).map(t => t.textContent.trim().substring(0, 60))
                    };
                }""")
                log(f"  Help UI elements: {json.dumps(help_ui)}")
        except Exception as e:
            log(f"  Help test error: {e}")

        # ===================== TEST: Category add/delete =====================
        log("=== Category Management Test ===")
        try:
            # Click the + button next to Categories
            add_cat_btn = page.evaluate("""() => {
                const catHeader = Array.from(document.querySelectorAll('*')).find(
                    el => el.textContent.trim() === 'Categories' && el.offsetParent !== null
                );
                if (!catHeader) return null;
                const parent = catHeader.parentElement;
                const addBtn = parent ? parent.querySelector('button, [role="button"]') : null;
                return addBtn ? true : false;
            }""")
            log(f"  Add category button found: {add_cat_btn}")

            # Try clicking the "+" near Categories
            plus_btns = page.query_selector_all("button:has-text('+')")
            for btn in plus_btns:
                if btn.is_visible():
                    log("  Clicking + button for categories")
                    btn.click()
                    page.wait_for_timeout(1500)
                    screenshot(page, "26_add_category")
                    break

        except Exception as e:
            log(f"  Category test error: {e}")

        # ===================== TEST: Project name editing =====================
        log("=== Project Name Edit Test ===")
        try:
            # The project name "New Project" should be editable
            name_input = page.query_selector("input[value='New Project'], [class*='projectName'], [class*='ProjectName']")
            if name_input:
                name_input.click()
                page.wait_for_timeout(500)
                name_input.fill("Test Project Name")
                page.wait_for_timeout(500)
                screenshot(page, "27_project_name")
                log("  Project name edited successfully")
            else:
                # Try clicking on the "New Project" text
                np_text = page.query_selector("text='New Project'")
                if np_text and np_text.is_visible():
                    np_text.click()
                    page.wait_for_timeout(500)
                    screenshot(page, "27_project_name_click")
                    log("  Clicked on project name text")
        except Exception as e:
            log(f"  Project name test error: {e}")

        # ===================== TEST: Annotate view =====================
        log("=== Annotate View Test ===")
        try:
            annotate_btn = page.query_selector("button:has-text('Annotate')")
            if annotate_btn and annotate_btn.is_visible():
                annotate_btn.click()
                page.wait_for_timeout(3000)
                screenshot(page, "28_annotate_view")

                annotate_state = page.evaluate("""() => {
                    return {
                        url: window.location.href,
                        hasCanvas: !!document.querySelector('canvas'),
                        buttonCount: document.querySelectorAll('button').length,
                        toolbarBtns: Array.from(document.querySelectorAll('[class*="tool"], [class*="Tool"]'))
                            .filter(e => e.offsetParent !== null)
                            .map(e => (e.textContent || e.getAttribute('aria-label') || '').trim().substring(0, 30))
                    };
                }""")
                log(f"  Annotate state: {json.dumps(annotate_state)}")
        except Exception as e:
            log(f"  Annotate test error: {e}")

        # ===================== TEST: Measure view =====================
        log("=== Measure View Test ===")
        try:
            # Go back to main view first
            page.goto(URL, wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(2000)
            page.click("button:has-text('Start New Project')")
            page.wait_for_timeout(3000)

            measure_btn = page.query_selector("button:has-text('Measure')")
            if measure_btn and measure_btn.is_visible():
                measure_btn.click()
                page.wait_for_timeout(3000)
                screenshot(page, "29_measure_view")
                log("  Measure view opened")

                measure_state = page.evaluate("""() => {
                    return {
                        url: window.location.href,
                        visibleText: document.body.innerText.substring(0, 500)
                    };
                }""")
                log(f"  Measure URL: {measure_state['url']}")
                log(f"  Measure text: {measure_state['visibleText'][:200]}")
        except Exception as e:
            log(f"  Measure test error: {e}")

        # ===================== TEST: Browser back/forward =====================
        log("=== Browser Navigation Test ===")
        try:
            page.goto(URL, wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(2000)
            url1 = page.url

            page.click("button:has-text('Start New Project')")
            page.wait_for_timeout(3000)
            url2 = page.url

            page.go_back()
            page.wait_for_timeout(3000)
            url3 = page.url
            screenshot(page, "30_after_back")

            log(f"  Home: {url1}")
            log(f"  After new project: {url2}")
            log(f"  After back: {url3}")

            if url3 != url1:
                log(f"  WARNING: Back button did not return to home page (got {url3})")
        except Exception as e:
            log(f"  Navigation test error: {e}")

        context.close()
        browser.close()

if __name__ == "__main__":
    main()
