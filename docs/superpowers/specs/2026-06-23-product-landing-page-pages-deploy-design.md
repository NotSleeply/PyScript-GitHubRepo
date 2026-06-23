# Design Document: Product Landing Page & GitHub Pages Deployment

**Date:** 2026-06-23  
**Status:** Approved  
**Author:** Claude Code  

---

## 1. Overview

The goal is to create a product landing/introduction page for the `PyScript-GitHubRepo` utility under the `public/` directory and configure a automated GitHub Actions workflow to deploy it to GitHub Pages. The deployment must be isolated and not affect other projects' GitHub Pages.

---

## 2. Requirements & Constraints

* **Product Introduction**: Showcase features, installation, usage, and quickstart info for `PyScript-GitHubRepo`.
* **Path Location**: The HTML and assets must be placed inside the `public/` directory in the root of the project.
* **GitHub Pages deployment**: Automation via GitHub Actions.
* **Isolation**: Must not affect other repositories' GitHub Pages (resolved by using repository-specific Pages served at `https://<username>.github.io/<repo-name>/`).
* **Visual Appeal**: High-quality dark-themed developer landing page.

---

## 3. Architecture & Design

### A. Static Assets (`public/index.html`)

We will create a single-page HTML application:

1. **Header**: Title, version badge, links to GitHub.
2. **Hero Section**: Catchy title ("Batch Download & Sync GitHub Repositories at Scale"), description, and a simulated terminal output demonstrating the CLI usage.
3. **Features Matrix**:
   * Multi-threaded performance
   * Dual-mode download (Git Clone / ZIP Download)
   * Local metadata filtering (Language, Stars, Updated dates)
   * Automated reporting (Markdown, CSV, JSON)
   * Automation-friendly (JSON mode + exit codes)
4. **Getting Started**:
   * Quick installation code snippets (`uv pip install`).
   * Usage examples (human mode and machine/JSON mode).
   * Configuration yaml file example.

### B. Styling & Styling Tech Stack

* **Tailwind CSS (via CDN)**: For responsive, utility-first CSS styling without build dependencies.
* **Inter Font**: Loaded via Google Fonts.
* **SVG Icons**: Pure inline SVG icons for clean graphics.

### C. GitHub Actions Workflow (`.github/workflows/deploy-pages.yml`)

* **Trigger**: Triggered on pushes to the `main` branch, specifically when there are modifications under the `public/` directory or the workflow file. Also supports manual trigger via `workflow_dispatch`.
* **Environment**: GitHub Pages deployment target.
* **Job Steps**:
  1. Checkout repository (`actions/checkout@v4`).
  2. Setup Pages environment (`actions/configure-pages@v4`).
  3. Upload static content as Pages artifact (`actions/upload-pages-artifact@v3`, target path: `./public`).
  4. Deploy Pages artifact (`actions/deploy-pages@v4`).
* **Permissions**:

  ```yaml
  permissions:
    contents: read
    pages: write
    id-token: write
  ```

  This is the recommended configuration by GitHub for secure, automated GitHub Pages deployments.

---

## 4. Verification Plan

* **Local Verification**: The HTML page is verified directly in a local browser.
* **Actions Validation**: The GitHub Actions runner will deploy the artifacts, which will be accessible at `https://<username>.github.io/PyScript-GitHubRepo/`.
* **Isolation Validation**: Other pages (e.g. `https://<username>.github.io/other-repos`) will remain completely untouched.
