# Piximi Beta Test Report

**URL:** https://piximi-beta.vercel.app  
**Date:** 2026-04-24  
**Test Method:** Automated browser testing with Playwright (headless Chromium)  
**Test Scripts:** `test_piximi.py`, `test_piximi_final.py`, `test_piximi_deep.py`, `test_piximi_upload_workflows.py`, `test_piximi_models.py`  
**Test Data:** 18 microscopy images (1 JPG from JUMP dataset, 17 TIF from U2OS cell-painting assay)

---

## Executive Summary

Piximi loads successfully and core workflows (project creation, image upload, navigation) function well. Example projects (MNIST, U2OS cell-painting, Malaria) load and display correctly. Classification model training works end-to-end (Fit Classifier with Simple CNN on MNIST, training plots displayed). However, **all segmentation model loading fails silently**, and several issues were found across accessibility, functionality, and user experience:

- **14 PASS, 0 FAIL, 2 WARN** in workflow tests (upload, classify, segment, measure)
- **17 PASS, 1 FAIL, 4 WARN** in base UI tests
- **9 PASS, 0 FAIL, 4 WARN** in model loading tests
- **6 issues** from deep interaction testing
- **3 console errors** related to mixed-type file uploads

---

## Issues Found

### CRITICAL Severity

#### 0. All segmentation models fail to load silently
- **Category:** Functionality
- **Description:** Selecting any pre-trained segmentation model (Cellpose, StardistVHE, StardistFluo, COCO-SSD, GlandSegmentation) from the Load Segmentation Model dialog and clicking "OPEN SEGMENTATION MODEL" closes the dialog but never loads the model. The sidebar continues to show "Selected Model: No Selected Model" and "Model Kind: N/A" indefinitely. No error message, no progress indicator, and no console errors are produced.
- **Impact:** Segmentation workflow is completely non-functional. Users cannot segment images. This is a core feature of the application.
- **Steps to Reproduce:** Open MNIST project > Click SEGMENTATION tab > Click LOAD MODEL > Select any model from dropdown > Click OPEN SEGMENTATION MODEL > Observe sidebar still shows "No Selected Model"
- **Models tested:** Cellpose, StardistFluo, COCO-SSD (all failed after 60s wait each)
- **Note:** The dialog warns these models "perform inference in the cloud" and require internet access. The failure may be due to a backend service being down, a CORS issue, or a broken API endpoint. No network errors or console errors were observed.

### HIGH Severity

#### 1. Mixed-type file upload throws unhandled error
- **Category:** Functionality / Error Handling
- **Description:** Uploading files of mixed types (e.g., JPG + TIF together) triggers an unhandled promise rejection: `"Input files must be of the same type"`.
- **Impact:** The error message is shown as raw text ("Uncaught promise rejection") in the UI with no user-friendly feedback. Images silently fail to load.
- **Steps to Reproduce:** Open > Image > New Image, select a JPG and TIF file together.
- **Recommendation:** Catch this error gracefully and show a clear message like "Please upload images of the same file type."

#### 2. Annotate button remains disabled after selecting an image
- **Category:** Functionality
- **Description:** In the MNIST example project, clicking on an image thumbnail does not enable the "Annotate" button (top-right). The button remains disabled even after image selection.
- **Impact:** Users cannot enter annotation/segmentation mode through the expected workflow.
- **Steps to Reproduce:** Open MNIST example project > click on any image thumbnail > observe Annotate button stays grayed out.
- **Note:** This may require double-click or a different selection mechanism, but single-click should be sufficient.

#### 3. 12 icon-only buttons without accessible labels
- **Category:** Accessibility
- **Description:** 12 visible buttons in the workspace consist only of SVG icons with no `aria-label`, `title`, or text content. Screen readers cannot identify these buttons.
- **Impact:** The application is inaccessible to users relying on assistive technology.
- **Affected buttons:** Icon buttons in the toolbar area, category action buttons (e.g., expand/collapse), and the 3 ML action icons (Fit/Predict/Evaluate) below the Model selector.
- **Recommendation:** Add descriptive `aria-label` attributes to all icon-only buttons.

#### 3b. Classification remote model loading - validation rejects valid TF Hub URLs
- **Category:** Functionality
- **Description:** In the Load Classification Model > Fetch Remote tab, entering a TensorFlow Hub URL and checking "From TF Hub?" shows the error "URL must point to TFHub" even for valid TF Hub URLs. The "LOAD MODEL" button remains disabled.
- **Impact:** Users cannot load pre-trained classification models from TensorFlow Hub.
- **Steps to Reproduce:** Open MNIST > Classification > Load Model > Fetch Remote > Check "From TF Hub?" > Enter a TF Hub model URL > Observe "URL must point to TFHub" error
- **Note:** The URL validation regex may be too strict or the expected format may not match actual TF Hub URLs.

#### 3c. Segmentation Load Model lacks custom model upload
- **Category:** Functionality
- **Description:** The segmentation Load Model dialog only offers a "LOAD PRETRAINED" tab with a dropdown of 5 pre-trained models. Unlike the classification dialog (which has "Upload Local" and "Fetch Remote" tabs), there is no way to upload a custom segmentation model or fetch one from a URL.
- **Impact:** Users are limited to the 5 pre-built segmentation models (which currently don't load - see issue #0).

### MEDIUM Severity

#### 4. ML action buttons (Fit/Predict/Evaluate) lack labels
- **Category:** Accessibility
- **Description:** The 3 icon buttons below the "Model:" selector (which appear to be Fit, Predict, and Evaluate actions) have no `aria-label`, `title`, or text. Users cannot determine their purpose without trial and error.
- **Impact:** Both accessibility and general usability are affected. Even sighted users may not understand what these buttons do.
- **Recommendation:** Add tooltips and aria-labels (e.g., "Fit Model", "Predict", "Evaluate").

#### 5. Missing ARIA landmarks
- **Category:** Accessibility
- **Description:** No ARIA landmark roles found for `banner`, `navigation`, `main`, or `contentinfo`. The `<html>` element does have `lang="en"` set correctly.
- **Impact:** Screen reader navigation is impaired; users cannot jump between page sections.
- **Recommendation:** Add semantic HTML elements or ARIA roles: `<header>` or `role="banner"`, `<nav>` or `role="navigation"`, `<main>` or `role="main"`.

#### 6. No visible focus indicators on interactive elements
- **Category:** Accessibility
- **Description:** 6 out of 10 tabbed elements lack visible focus indicators. Buttons like "Start New Project" and "Open Example Project" show no outline or highlight when focused via keyboard.
- **Impact:** Keyboard-only users cannot track which element is currently focused.
- **Recommendation:** Ensure `:focus-visible` styles are applied to all interactive elements.

#### 7. Touch targets below 44px minimum on mobile
- **Category:** Mobile / Usability
- **Description:** On mobile viewport (375x812), the main buttons ("Start New Project", "Open Example Project", "Documentation") are only 37px tall, below the 44px minimum recommended by WCAG and Apple HIG.
- **Impact:** Buttons are harder to tap accurately on touch devices.
- **Recommendation:** Increase button height to at least 44px on mobile viewports.

#### 8. Form input without label
- **Category:** Accessibility
- **Description:** 1 form input element (likely the project name input or search) has no associated `<label>`, `aria-label`, or `placeholder` text.
- **Impact:** Screen readers cannot identify the purpose of this input.

#### 9. Disabled buttons indistinguishable from enabled
- **Category:** Usability
- **Description:** Several disabled buttons (e.g., "Save Model", "New Model") have `opacity: 1` and no visual distinction from enabled buttons. Only `cursor: default` changes. "Annotate" is the exception with `opacity: 0.38`.
- **Impact:** Users cannot easily distinguish which actions are available.
- **Recommendation:** Apply consistent reduced opacity or dimmed styling to all disabled buttons.

#### 10. "Upload Project" button not found
- **Category:** Functionality
- **Description:** The `test_piximi_deep.py` script could not locate an "Upload Project" button on the home page. The home page only shows "Start New Project" and "Open Example Project".
- **Impact:** Users cannot upload a previously saved project directly from the landing page (must go to workspace first and use Open > Project).
- **Note:** This may be by design, but the deep test expected this workflow.

### LOW Severity (ALAN):  These seem irrelevant

#### 11. Missing Open Graph meta tags
- **Category:** SEO / Social Sharing
- **Description:** Missing `og:title`, `og:description`, and `og:image` meta tags. Only `<meta name="description">` is present.
- **Impact:** Links shared on social media (Twitter, Slack, etc.) will not show a rich preview.
- **Recommendation:** Add Open Graph meta tags for better link sharing.

#### 12. Segmentation model loads require cloud inference
- **Category:** UX / Privacy
- **Description:** The segmentation "Load Model" dialog warns: "This model performs inference in the cloud; images will leave your machine." This is correctly disclosed but may surprise users expecting client-side processing.
- **Impact:** Users concerned about data privacy may be deterred. The warning is good practice.
- **Recommendation:** Consider offering client-side segmentation models as an alternative.

#### 13. No semantic HTML structure
- **Category:** Accessibility / SEO
- **Description:** The app does not use `<header>`, `<main>`, `<nav>`, or `<footer>` elements. All layout is done through `<div>` elements with MUI classes.
- **Recommendation:** Wrap major sections in semantic elements for better accessibility and SEO.

#### 14. Settings dialog toggle accessibility
- **Category:** Accessibility
- **Description:** Settings dialog contains toggle switches for "UITheme Mode", "Selection Border Width", "Sound Effects", and "Prompt save when starting new project" but their accessible states may not be properly announced.

---

## Model Loading & Training Results

### Classification Models

| Test | Result | Details |
|------|--------|---------|
| Upload Local tab | PASS | File chooser works, accepts `.json` + `.bin` files, multiple=true |
| Graph/Layers Model toggle | PASS | Both radio options selectable, descriptions mention .json + .bin |
| Fetch Remote tab | PASS | URL input, "From TF Hub?" checkbox, Model Format selector all present |
| Fetch Remote - load model | WARN | URL validation rejects TF Hub URLs ("URL must point to TFHub") |
| Fit Classifier (Simple CNN) | PASS | Training runs on MNIST, progress bar shows "Epoch N of 10", training curves displayed |
| Training Plots tab | PASS | Shows "Training History - Accuracy per Epoch" and "Loss per Epoch" with validation/training curves (86 SVGs) |
| Model Summary tab | DISABLED | Shows "No Trained Model" tooltip, tab is disabled during training |
| Hyperparameters | PASS | Architecture: Simple CNN, Input Shape: 28x28x1, Epochs: 10, Training %: 85%, Export Hyperparameters link |

### Segmentation Models

| Test | Result | Details |
|------|--------|---------|
| Load Pretrained tab | PASS | "Pre-trained Models" Autocomplete dropdown with 5 options |
| Available models | PASS | Cellpose, StardistVHE, StardistFluo, COCO-SSD, GlandSegmentation |
| Model info display | PASS | Shows Name, Description, Use, Output, Sources (GitHub), Citations |
| Load Cellpose | FAIL | Dialog closes, model never loads. Sidebar: "No Selected Model" after 60s |
| Load StardistFluo | FAIL | Same silent failure |
| Load COCO-SSD | FAIL | Same silent failure |
| Custom model upload | N/A | No Upload Local or Fetch Remote tab available for segmentation |

## Passing Tests

| Test | Result | Details |
|------|--------|---------|
| Initial page load | PASS | HTTP 200, title "Piximi" |
| Console errors (clean load) | PASS | 0 errors on initial load |
| Responsive design | PASS | No horizontal overflow at 375px, 768px, 1920px |
| JPG image upload | PASS | piximi_JUMP_K14_0.jpg uploaded, appears in grid, Unknown count = 1 |
| TIF image upload | PASS | 3 DNA channel TIFs uploaded, rendered as grayscale thumbnails |
| MNIST example project | PASS | 1000 images loaded with 10 categories (0-9) |
| U2OS cell-painting example | PASS | Project loads with composite fluorescence image |
| Classification tab | PASS | CLASSIFICATION/SEGMENTATION toggle works |
| Load Model dialog | PASS | Upload Local + Fetch Remote tabs functional |
| Segmentation tab | PASS | Shows model selection UI, Load Model works |
| Measure view | PASS | Navigates to /measurements, shows "Tables" view |
| Project name editing | PASS | Project name input is editable |
| Browser back/forward | PASS | Navigation history works correctly |
| Settings dialog | PASS | Opens with theme, border, sound, save-prompt options |
| Help mode toggle | PASS | Toggles help tooltip visibility |
| Network errors | PASS | No failed HTTP requests |
| File upload mechanism | PASS | 1 file input (hidden) + 1 drop zone detected |

---

## Console Errors Observed

3 identical errors during mixed-type upload tests:
```
Unhandled promise rejection: Error: Input files must be of the same type.
Found function entries() { [native code] }
at interpretFiles (index-BHcXtXQU.js:2212)
```
No console errors during normal single-type uploads or example project loading.

---

## Performance Metrics

| Metric | Value |
|--------|-------|
| TTFB | 17ms |
| Transfer size | 300 bytes (initial HTML) |
| Console errors on load | 0 |
| No horizontal scrollbar | All viewports (375px-1920px) |

---

## Test Environment

- **Browser:** Chromium (headless), Playwright 1.58.0
- **Viewport:** 1280x720 (desktop), 375x812 (mobile)
- **Python:** 3.9
- **OS:** macOS Darwin 24.6.0
- **Test images:** 1 JPG (830KB), 17 TIF (300-860KB each) - microscopy/cell biology images

---

## Screenshots

All screenshots saved to `/Users/amunozgo/tmp/piximi_screenshots/`. Key screenshots:
- `41_after_jpg_upload.png` - JPG cell image successfully uploaded
- `43_after_tif_upload.png` - 3 TIF DNA channel images uploaded
- `12_mnist_loaded.png` - MNIST example with categorized digits
- `51_classification_tab_active.png` - Classification UI with model selector
- `56_segmentation_tab.png` - Segmentation mode showing model status
- `53_load_model_dialog.png` - Load Classification model dialog (Upload Local tab)
- `53b_fetch_remote.png` - Load Classification model dialog (Fetch Remote tab)
- `81_opened_u2os.png` - U2OS cell-painting project loaded
- `63_measure_view.png` - Measure view at /measurements
- `M30_fit_dialog.png` - Fit Classifier dialog with hyperparameters
- `M31_fitting.png` - Training in progress, Training Plots with accuracy curves
- `M33_training_plots.png` - Training History showing Accuracy & Loss per Epoch (6/10 epochs)
- `M03_cls_remote_url_filled.png` - Fetch Remote with "URL must point to TFHub" error
- `M41_cellpose_info.png` - Cellpose model info (Name, Description, Use, Output, Sources, Citations)
- `M50_cellpose_failed.png` - Cellpose model failed to load (still "No Selected Model")
