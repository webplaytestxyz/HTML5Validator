#!/usr/bin/env python3
"""
html5.py

Website HTML5 + SEO Auditor (Tkinter) with auto-download of vnu.jar (Nu HTML Checker).
Includes actionable insights for developers based on HTML5, accessibility, and SEO.
"""
import os
import sys
import threading
import time
import json
import tempfile
import subprocess
import shutil

from bs4 import BeautifulSoup
import tkinter as tk
from tkinter import messagebox, scrolledtext, filedialog
from PIL import Image, ImageTk

import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# ----------------------------
# Configuration / Paths
# ----------------------------
ROOT = os.path.dirname(os.path.abspath(__file__))
VALIDATOR_DIR = os.path.join(ROOT, "validator")
VNU_PATH = os.path.join(VALIDATOR_DIR, "vnu.jar")
if sys.platform.startswith("win"):
    JAVA_EMBED = os.path.join(VALIDATOR_DIR, "jre", "bin", "java.exe")
else:
    JAVA_EMBED = os.path.join(VALIDATOR_DIR, "jre", "bin", "java")
VNU_DOWNLOAD_URL = "https://github.com/validator/validator/releases/latest/download/vnu.jar"
VNU_DOWNLOAD_TIMEOUT = 60
VNU_RUN_TIMEOUT = 30

# ----------------------------
# Utilities
# ----------------------------
def ensure_validator_dir():
    if not os.path.isdir(VALIDATOR_DIR):
        os.makedirs(VALIDATOR_DIR, exist_ok=True)

def find_java_executable():
    if os.path.isfile(JAVA_EMBED) and os.access(JAVA_EMBED, os.X_OK):
        return JAVA_EMBED
    for java_cmd in ("java",):
        try:
            subprocess.run([java_cmd, "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=3)
            return java_cmd
        except Exception:
            continue
    return None

# ----------------------------
# Auto-download vnu.jar
# ----------------------------
def download_vnu_jar(progress_callback=None):
    ensure_validator_dir()
    try:
        with requests.get(VNU_DOWNLOAD_URL, stream=True, timeout=VNU_DOWNLOAD_TIMEOUT) as r:
            r.raise_for_status()
            total = int(r.headers.get("content-length") or 0) or None
            tmp_path = os.path.join(VALIDATOR_DIR, "vnu.jar.part")
            with open(tmp_path, "wb") as f:
                downloaded = 0
                for chunk in r.iter_content(chunk_size=8192):
                    if not chunk:
                        continue
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback:
                        try:
                            progress_callback(downloaded, total)
                        except Exception:
                            pass
            shutil.move(tmp_path, VNU_PATH)
        return True, None
    except Exception as e:
        try:
            part = os.path.join(VALIDATOR_DIR, "vnu.jar.part")
            if os.path.exists(part):
                os.remove(part)
        except Exception:
            pass
        return False, str(e)

# ----------------------------
# Run vnu validator on HTML text
# ----------------------------
def validate_with_vnu(html_text):
    if not os.path.isfile(VNU_PATH):
        return {"available": False, "valid": None, "messages": [], "error": "vnu.jar not found."}
    java_exec = find_java_executable()
    if not java_exec:
        return {"available": False, "valid": None, "messages": [], "error": "Java runtime not found."}
    tmp = None
    try:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".html", mode="wb")
        tmp.write(html_text.encode("utf-8"))
        tmp.close()
        cmd = [java_exec, "-jar", VNU_PATH, "--format", "json", tmp.name]
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=VNU_RUN_TIMEOUT
        )
        stdout = proc.stdout.strip() if proc.stdout else ""
        stderr = proc.stderr.strip() if proc.stderr else ""
        raw = stderr or stdout
        if proc.returncode == 0:
            return {"available": True, "valid": True, "messages": [], "error": None}
        else:
            try:
                parsed = json.loads(raw)
                messages = parsed.get("messages", [])
            except Exception:
                messages = [{"type": "error", "message": raw}]
            return {"available": True, "valid": False, "messages": messages, "error": None}
    except subprocess.TimeoutExpired:
        return {"available": True, "valid": None, "messages": [], "error": "Validation timed out."}
    except Exception as e:
        return {"available": True, "valid": None, "messages": [], "error": str(e)}
    finally:
        if tmp is not None:
            try:
                os.unlink(tmp.name)
            except Exception:
                pass

# ----------------------------
# Selenium fetch
# ----------------------------
def selenium_fetch(url):
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1400,1000")
    driver = webdriver.Chrome(options=options)
    start_time = time.time()
    driver.get(url)
    time.sleep(2)
    try:
        perf = driver.execute_script(
            "return (window.performance.timing.loadEventEnd - window.performance.timing.navigationStart);"
        )
        page_load_ms = int(perf) if perf and int(perf) > 0 else None
    except Exception:
        page_load_ms = None
    page_source = driver.page_source
    screenshot_path = os.path.join(ROOT, "page_preview.png")
    driver.save_screenshot(screenshot_path)
    driver.quit()
    duration_ms = int((time.time() - start_time) * 1000)
    return page_source, screenshot_path, page_load_ms, duration_ms

# ----------------------------
# Parsing & audit logic
# ----------------------------
def parse_robots_meta(content):
    content = (content or "").lower()
    return {
        "Indexing": "Allowed" if "noindex" not in content else "Disallowed",
        "Following Links": "Allowed" if "nofollow" not in content else "Disallowed",
        "Snippets": "Allowed" if "nosnippet" not in content else "Disallowed",
        "Image Previews": ("Large" if "max-image-preview:large" in content else
                           "Standard" if "max-image-preview:standard" in content else
                           "None" if "max-image-preview:none" in content else "Not specified")
    }

def audit_website_selenium(url):
    result = {}
    try:
        html, screenshot_path, page_load_ms, fetch_duration = selenium_fetch(url)
    except Exception as e:
        return {"error": f"❌ Failed to fetch URL with Selenium: {e}"}
    result["fetch_duration_ms"] = fetch_duration
    result["screenshot"] = screenshot_path
    result["page_load_ms"] = page_load_ms
    result["raw_html"] = html

    soup = BeautifulSoup(html, "html5lib")
    doctype = next((str(item) for item in soup.contents if isinstance(item, type(soup.Doctype))), "Missing")
    result["DOCTYPE"] = doctype
    result["lang"] = soup.html.get("lang") if soup.html and soup.html.get("lang") else None
    result["title"] = soup.title.string.strip() if soup.title and soup.title.string else None
    h1s = [h.text.strip() for h in soup.find_all("h1")]
    result["h1s"] = h1s
    canonical = soup.find("link", rel="canonical")
    result["canonical"] = canonical["href"] if canonical and canonical.get("href") else None
    images = soup.find_all("img")
    result["images_total"] = len(images)
    result["images_with_alt"] = sum(1 for img in images if img.get("alt"))
    result["images_list"] = [{"src": img.get("src"), "alt": img.get("alt")} for img in images]
    robots = soup.find("meta", attrs={"name": "robots"})
    result["robots_content"] = robots["content"] if robots and robots.get("content") else ""
    result["robots_parsed"] = parse_robots_meta(result["robots_content"])
    ogs = [meta.get("property") for meta in soup.find_all("meta", property=lambda v: v and v.startswith("og:"))]
    result["og_tags"] = ogs
    twitters = [meta.get("name") for meta in soup.find_all("meta", attrs={"name": lambda v: v and v.startswith("twitter:")})]
    result["twitter_tags"] = twitters
    result["html5_validation"] = validate_with_vnu(html)
    return result

# ----------------------------
# GUI
# ----------------------------
class App:
    def __init__(self, root):
        self.root = root
        root.title("HTML5Validator - Website Auditor")
        root.geometry("1050x800")
        root.resizable(False, False)

        tk.Label(root, text="Enter website URL:", font=("Segoe UI", 10)).pack(pady=(8, 4))
        self.url_entry = tk.Entry(root, width=96, font=("Segoe UI", 10))
        self.url_entry.pack(pady=(0, 6))

        btn_frame = tk.Frame(root)
        btn_frame.pack(pady=(0, 8))
        self.scan_button = tk.Button(btn_frame, text="Scan Website", command=self.run_audit, width=20)
        self.scan_button.grid(row=0, column=0, padx=8)
        self.save_button = tk.Button(btn_frame, text="Save Report as TXT", command=self.save_report, width=20)
        self.save_button.grid(row=0, column=1, padx=8)

        self.status_label = tk.Label(root, text="Status: Ready", anchor="w")
        self.status_label.pack(fill="x", padx=10)

        main_frame = tk.Frame(root)
        main_frame.pack(pady=6, fill="both", expand=True)

        report_frame = tk.Frame(main_frame)
        report_frame.pack(side="left", fill="both", expand=True, padx=(10, 5))
        tk.Label(report_frame, text="📋 Audit Results", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.output_box = scrolledtext.ScrolledText(report_frame, width=80, height=38, font=("Consolas", 10))
        self.output_box.pack(fill="both", expand=True)
        self.output_box.tag_configure("green", foreground="green")
        self.output_box.tag_configure("orange", foreground="orange")
        self.output_box.tag_configure("red", foreground="red")
        self.output_box.tag_configure("bold", font=("Consolas", 10, "bold"))

        preview_frame = tk.Frame(main_frame, width=400)
        preview_frame.pack(side="right", fill="both", expand=True, padx=(5, 10))
        tk.Label(preview_frame, text="🌐 Website Screenshot", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.preview_label = tk.Label(preview_frame, text="Preview will appear here.", width=50, height=20)
        self.preview_label.pack(fill="both", expand=True)

        ensure_validator_dir()
        if not os.path.isfile(VNU_PATH):
            self._start_vnu_download()

    def _start_vnu_download(self):
        def progress_cb(downloaded, total):
            if total:
                pct = int(downloaded * 100 / total)
                self.status_label.config(text=f"Status: Downloading vnu.jar ({pct}%)")
            else:
                self.status_label.config(text=f"Status: Downloading vnu.jar ({downloaded} bytes)")

        def do_download():
            ok, err = download_vnu_jar(progress_callback=progress_cb)
            if ok:
                self.status_label.config(text="Status: vnu.jar downloaded — full HTML5 validation available")
            else:
                self.status_label.config(text="Status: vnu.jar download failed")
                print("vnu.jar download failed:", err)

        threading.Thread(target=do_download, daemon=True).start()

    def run_audit_thread(self, url):
        self.status_label.config(text="Status: Running audit...")
        results = audit_website_selenium(url)

        def update_ui():
            self.output_box.config(state=tk.NORMAL)
            self.output_box.delete("1.0", tk.END)

            if "error" in results:
                self.output_box.insert(tk.END, results["error"])
                self.preview_label.config(image='', text="No preview.")
                self.output_box.config(state=tk.DISABLED)
                self.status_label.config(text="Status: Ready")
                return

            # Screenshot
            try:
                img = Image.open(results["screenshot"])
                img = img.resize((420, 320))
                tk_img = ImageTk.PhotoImage(img)
                self.preview_label.config(image=tk_img, text="")
                self.preview_label.image = tk_img
            except Exception:
                self.preview_label.config(text="No preview.")

            def insert_line(name, status, value, tag=None):
                self.output_box.insert(tk.END, f"- {name}: ", "bold")
                if tag:
                    self.output_box.insert(tk.END, f"{status} {value}\n", tag)
                else:
                    self.output_box.insert(tk.END, f"{status} {value}\n")

            self.output_box.insert(tk.END, f"🔍 Website Audit: {url}\n")
            self.output_box.insert(tk.END, f"⏱ Audit Duration: Fetched in {results['fetch_duration_ms']}ms\n")
            if results.get('page_load_ms'):
                self.output_box.insert(tk.END, f"⚡ Estimated Page Load: {results['page_load_ms']/1000:.2f}s\n\n")
            else:
                self.output_box.insert(tk.END, f"⚡ Estimated Page Load: N/A\n\n")

            # Structure
            self.output_box.insert(tk.END, "📄 Structure\n")
            insert_line("DOCTYPE", "✅" if results["DOCTYPE"] != "Missing" else "❌", results["DOCTYPE"],
                        "green" if results["DOCTYPE"] != "Missing" else "red")
            insert_line("HTML <lang>", "✅" if results["lang"] else "❌", results["lang"] or "Missing",
                        "green" if results["lang"] else "red")

            # SEO Essentials
            self.output_box.insert(tk.END, "\n🔍 SEO Essentials\n")
            title = results.get("title")
            if title:
                tlen = len(title)
                tint = "green" if 10 <= tlen <= 70 else "orange"
                insert_line("Title Tag", "✅" if 10 <= tlen <= 70 else "⚠️", f"'{title}' ({tlen} chars)", tint)
            else:
                insert_line("Title Tag", "❌", "Missing", "red")

            h1s = results.get("h1s", [])
            if len(h1s) == 0:
                insert_line("H1 Tags", "❌", "No H1 tag found", "red")
            elif len(h1s) == 1:
                insert_line("H1 Tags", "✅", f"Found 1 H1: '{h1s[0][:50]}'", "green")
            else:
                insert_line("H1 Tags", "⚠️", f"Found {len(h1s)} H1 tags (consider 1)", "orange")

            insert_line("Canonical Tag", "✅" if results.get("canonical") else "❌",
                        results.get("canonical") or "Missing",
                        "green" if results.get("canonical") else "red")

            # Robots
            self.output_box.insert(tk.END, "- Robots Meta:\n")
            robots_parsed = results.get("robots_parsed", {})
            for k, v in robots_parsed.items():
                tag = "green" if (v in ("Allowed", "Large", "Standard", "Not specified")) else "red"
                self.output_box.insert(tk.END, f"    ✅ {k}: {v}\n", tag)

            # Images
            images_list = results.get("images_list", [])
            if not images_list:
                insert_line("Image Alts", "⚠️", "No images found", "orange")
            else:
                missing_count = sum(1 for i in images_list if not i["alt"])
                insert_line("Image Alts", "⚠️" if missing_count else "✅",
                            f"{missing_count}/{len(images_list)} missing alt text", "orange" if missing_count else "green")
                for img in images_list:
                    src = img.get("src") or "(no src)"
                    alt = img.get("alt") or "(missing alt)"
                    self.output_box.insert(tk.END, f"    - {src}: {alt}\n")

            # OpenGraph / Twitter
            og_tags = results.get("og_tags", [])
            tw_tags = results.get("twitter_tags", [])
            insert_line("OpenGraph Tags", "✅" if og_tags else "❌", f"Found {len(og_tags)}: {', '.join(og_tags)}", "green" if og_tags else "red")
            insert_line("Twitter Cards", "✅" if tw_tags else "❌", f"Found {len(tw_tags)}: {', '.join(tw_tags)}", "green" if tw_tags else "red")

            # HTML5 Validation
            v = results.get("html5_validation", {})
            self.output_box.insert(tk.END, "\n🔎 HTML5 Validation & Actionables\n")
            if not v.get("available"):
                self.output_box.insert(tk.END, f"- Validator unavailable: {v.get('error') or 'vnu.jar or Java missing'}\n")
                self.output_box.insert(tk.END, "- Performing basic structural checks instead.\n")
            else:
                if v.get("valid") is True:
                    self.output_box.insert(tk.END, "- ✅ Page is valid HTML5 (no errors)\n", "green")
                elif v.get("valid") is False:
                    self.output_box.insert(tk.END, f"- ❌ Page has {len(v.get('messages', []))} HTML5 issues\n", "red")
                    self.output_box.insert(tk.END, "- Actionable tips:\n", "bold")
                    for m in v.get("messages", []):
                        typ = m.get("type", "info").upper()
                        msg = m.get("message") or m.get("extract") or str(m)
                        line = m.get("lastLine") or m.get("firstLine") or ""
                        self.output_box.insert(tk.END, f"    - {typ} line {line}: {msg}\n")
                else:
                    self.output_box.insert(tk.END, f"- Validation run but result unknown: {v.get('error')}\n")

            self.output_box.config(state=tk.DISABLED)
            self.status_label.config(text="Status: Ready")

        self.root.after(0, update_ui)

    def run_audit(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showinfo("Info", "Please enter a URL to scan.")
            return
        if not url.startswith("http"):
            url = "http://" + url
        self.scan_button.config(state=tk.DISABLED)
        self.status_label.config(text="Status: Queued — starting audit...")
        def wrapper():
            try:
                self.run_audit_thread(url)
            finally:
                time.sleep(1)
                self.scan_button.config(state=tk.NORMAL)
        threading.Thread(target=wrapper, daemon=True).start()

    def save_report(self):
        report = self.output_box.get("1.0", tk.END).strip()
        if not report:
            messagebox.showinfo("Info", "No report to save.")
            return
        file_path = filedialog.asksaveasfilename(defaultextension=".txt",
                                                 filetypes=[("Text Files", "*.txt")],
                                                 title="Save audit report")
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(report)
                messagebox.showinfo("Success", "Report saved successfully.")
            except Exception as e:
                messagebox.showerror("Error", f"Could not save report:\n{e}")

def main():
    root = tk.Tk()
    app = App(root)
    root.mainloop()

if __name__ == "__main__":
    main()
