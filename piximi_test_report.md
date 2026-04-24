# Piximi Beta (piximi-beta.vercel.app) - Browser Test Report

**Date:** 2026-04-24  
**Testing method:** Automated Playwright (headless Chromium) + visual screenshot analysis  
**Viewport tested:** 1280x720 (desktop), 768x1024 (tablet), 375x812 (mobile)

---

## Summary

| Severity | Count |
|----------|-------|
| High     | 3     |
| Medium   | 6     |
| Low      | 5     |

---

## HIGH Severity Issues

### 1. Mobile: Example Project dialog has severe text overlap
**Where:** Open Example Project dialog on 375x812 viewport  
**Details:** The dialog list items overlap catastrophically on mobile. Project titles, descriptions, and links from different items render on top of each other, making the content completely unreadable.  
**Screenshot:** `19_mobile_dialog.jpg`

### 2. Workspace: MNIST images do not render (WebGL dependency)
**Where:** Project workspace after loading MNIST example  
**Details:** After opening the MNIST example project, the image grid area is completely empty (0 `<img>` elements, 0 `<canvas>` elements). The console reports "WebGL is not supported on this device". While this is expected in headless mode, the app provides no fallback rendering and no user-facing error message when WebGL is unavailable. Users on older devices/browsers will see an empty workspace with no explanation.  
**Screenshot:** `12_mnist_loaded.jpg`

### 3. Accessibility: 12 icon-only buttons have no accessible label
**Where:** Workspace toolbar and sidebar  
**Details:** 12 visible buttons containing only SVG icons have no `textContent`, no `aria-label`, and no `title` attribute. Screen reader users cannot know what these buttons do. This includes both enabled and disabled icon buttons throughout the toolbar and sidebar.

---

## MEDIUM Severity Issues

### 4. Accessibility: Missing ARIA landmarks
**Where:** Entire application  
**Details:** The app has zero ARIA landmark roles. Missing: `banner`, `navigation`, `main`, `contentinfo`. There are no `<header>`, `<nav>`, `<main>`, or `<footer>` semantic elements either. Screen reader users cannot navigate the page structure.

### 5. Accessibility: Most interactive elements lack visible focus indicator
**Where:** Landing page  
**Details:** 6 out of 10 tabbed elements (buttons, links) show no visible focus ring or outline when focused via keyboard. Only the hidden file `<input>` showed a focus style. The main CTA buttons ("Start New Project", "Open Example Project", "Documentation") all lack visible focus indicators.

### 6. Accessibility: Form input without label
**Where:** Landing page  
**Details:** There is 1 form `<input>` element with no associated `<label>`, no `aria-label`, and no `placeholder` text. This appears to be a hidden file input for project upload.

### 7. Accessibility: Keyboard tab order loops and traps
**Where:** Landing page  
**Details:** Tab navigation cycles through only 4 elements (Start New Project -> hidden input -> Open Example Project -> Documentation) then jumps to `<body>` and repeats the same cycle. The "Upload Project" button is skipped entirely in the tab order.

### 8. Mobile: Touch targets below 44px minimum
**Where:** Landing page on 375x812 viewport  
**Details:** All 3 main buttons ("Start New Project", "Open Example Project", "Documentation") are only 37px tall, below the 44px minimum recommended by WCAG and Apple HIG for touch targets.

### 9. Disabled buttons not clearly distinguishable
**Where:** Workspace toolbar  
**Details:** Several disabled buttons (Save Model, unnamed icon buttons, Annotations tab) have `opacity: 1` and only change cursor to `default`. Without a visual opacity/color change, users may not realize these buttons are disabled. Only the "Annotate" button uses proper `opacity: 0.38` for its disabled state.

---

## LOW Severity Issues

### 10. SEO: Missing Open Graph meta tags
**Where:** `<head>` section  
**Details:** The page has a basic `<meta name="description">` but is missing `og:title`, `og:description`, and `og:image`. This means shared links on social media (Slack, Twitter, etc.) will display poorly with no preview card.

### 11. Landing page: No semantic HTML structure
**Where:** Landing page  
**Details:** The landing page uses no `<header>`, `<main>`, or semantic sectioning elements. The entire UI is built with generic `<div>` elements. The logo and heading are not wrapped in `<h1>` or similar.

### 12. Mobile workspace: Sidebar collapses to icon-only strip with no labels
**Where:** Workspace on 375x812 viewport  
**Details:** The left sidebar collapses to a 36px-wide icon strip on mobile. The right sidebar shows small unlabeled icons. Combined with Issue #3 (no aria-labels), these icons are unidentifiable to both sighted users unfamiliar with the app and screen reader users.  
**Screenshot:** `21_mobile_workspace.jpg`

### 13. Settings dialog: Toggle controls lack accessible labels
**Where:** Settings dialog  
**Details:** Settings toggle controls (Theme Mode, Sound Effects, Hide Image/Show Text on Scroll) use icon-based toggles without text labels on the toggle buttons themselves. While the setting names are visible, the toggle states may not be programmatically associated.  
**Screenshot:** `23_settings.jpg`

### 14. Feedback form: "Create GitHub Issue" button initially disabled with no indication why
**Where:** Send Feedback dialog  
**Details:** The "Create GitHub Issue" button appears grayed out when the dialog opens. It's not immediately clear that filling in the Title field is required to enable it - there's no helper text or required indicator.  
**Screenshot:** `24_feedback.jpg`

---

## Positive Findings

- Page loads fast (TTFB ~44ms)
- No console errors during normal operation
- No failed network requests (HTTP 4xx/5xx)
- No horizontal overflow at any viewport size
- Responsive layout adapts (no scroll issues)
- Browser back/forward navigation works correctly
- Project name is editable
- Example project dialog works well on desktop
- "Image and Object Sets" tab functions correctly
- Settings dialog is clean and functional on desktop
- Meta description and `lang="en"` attribute are present
- Favicon is present

---

## Screenshots Index

| File | Description |
|------|-------------|
| `01_initial_load.jpg` | Landing page on desktop |
| `04_responsive_mobile_375x812.jpg` | Landing page on mobile |
| `06_after_click_open.jpg` | Example project dialog (desktop) |
| `12_mnist_loaded.jpg` | MNIST project - empty workspace |
| `13_new_project.jpg` | New empty project workspace |
| `17_object_sets_tab.jpg` | Object sets tab in example dialog |
| `19_mobile_dialog.jpg` | **Example dialog on mobile (overlapping text)** |
| `21_mobile_workspace.jpg` | Workspace on mobile |
| `23_settings.jpg` | Settings dialog |
| `24_feedback.jpg` | Feedback dialog |
| `30_after_back.jpg` | After browser back navigation |
