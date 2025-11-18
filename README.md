
![screenshot](https://github.com/user-attachments/assets/12085c77-e00e-4637-8e48-3d9f12291e8c)
# HTML5Validator

A small desktop GUI tool to audit websites for HTML5, accessibility and basic SEO signals. The app uses Selenium to fetch pages (with a real browser render), BeautifulSoup for parsing, and the Nu HTML Checker (vnu.jar) for full HTML5 validation when Java is available.

## Features
- Render page with Selenium (headless Chrome/Chromium) and capture a screenshot preview.
- Basic structural checks: DOCTYPE, <html lang>, title, H1 count, canonical link.
- Robots meta parsing (index/follow/snippet/image-preview).
- Image alt text summary and list.
- OpenGraph and Twitter Card detection.
- Full HTML5 validation via vnu.jar (auto-download to validator/vnu.jar). If vnu.jar or Java is missing, the app still performs the structural checks and reports validator availability.
- Save audit as a TXT report from the GUI.

## Requirements
- Python 3.8+
- Dependencies (install via pip): requests, beautifulsoup4, pillow, selenium, html5lib
  - Example: pip install -r requirements.txt
- Chrome or Chromium browser accessible on the machine.
- A matching ChromeDriver accessible via PATH or let Selenium Manager auto-provide a driver (Selenium 4.6+).
- Java runtime (optional, required only for vnu.jar HTML validation). If Java is not found the app falls back to non-vnu checks.
- Network access to download vnu.jar on first run (saved in validator/vnu.jar).

## Installation
1. Clone or download this repository.
2. (Optional) Create and activate a virtual environment:
   - python -m venv .venv
   - .venv\Scripts\activate
3. Install Python packages:
   - pip install requests beautifulsoup4 pillow selenium html5lib
   - Or: pip install -r requirements.txt (create requirements.txt if desired)
4. Ensure Chrome/Chromium is installed and a compatible driver is available, or use a Selenium version with Selenium Manager.

## Usage
1. Run the GUI:
   - python html5.py
2. In the app:
   - Enter a URL (http/https). If you omit the scheme, "http://" is prepended.
   - Click "Scan Website" to run the audit. A screenshot appears, results populate the report panel.
   - Click "Save Report as TXT" to export the report.

Notes:
- On first run the app attempts to download vnu.jar to the validator/ folder. If vnu.jar or Java is unavailable, the UI will show validator as unavailable and still perform the basic checks.
- The app stores a temporary page screenshot as page_preview.png in the project root.

## Troubleshooting
- "Browser not found" / Selenium errors: ensure Chrome/Chromium is installed and either ChromeDriver is on PATH or use a Selenium release that supports Selenium Manager.
- "Java runtime not found" — install Java (JRE/JDK) or place java executable in validator/jre/bin/java(.exe) if bundling a JRE.
- vnu.jar download fails: check network access and retry. You can manually put vnu.jar into the validator/ directory.

## Security & Usage
- The tool runs locally and uses your machine/network to fetch sites. Do not scan sites you do not have permission to test. Avoid aggressive or repeated scanning of large websites.

## License
MIT License — see LICENSE

