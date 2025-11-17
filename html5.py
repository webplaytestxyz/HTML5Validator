import threading
import time
from bs4 import BeautifulSoup
import tkinter as tk
from tkinter import messagebox, scrolledtext, filedialog
from PIL import Image, ImageTk

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# ---------- Core Selenium Fetch ----------
def selenium_fetch(url):
    """Fetch page source + screenshot + page load time using Selenium headless Chrome."""
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1400,1000")

    driver = webdriver.Chrome(options=options)
    start_time = time.time()
    driver.get(url)

    # Wait for page to load (basic)
    time.sleep(2)

    # Estimated page load using Navigation Timing API
    try:
        perf = driver.execute_script(
            "return window.performance.timing.loadEventEnd - window.performance.timing.navigationStart;"
        )
        page_load_seconds = round(perf / 1000, 2) if perf > 0 else None
    except Exception:
        page_load_seconds = None

    page_source = driver.page_source
    screenshot_path = "page_preview.png"
    driver.save_screenshot(screenshot_path)
    driver.quit()
    return page_source, screenshot_path, page_load_seconds, int((time.time() - start_time) * 1000)


# ---------- Website Audit ----------
def audit_website_selenium(url):
    result = {}
    try:
        html, screenshot_path, page_load, fetch_duration = selenium_fetch(url)
    except Exception as e:
        return {"error": f"❌ Failed to fetch URL with Selenium: {e}"}

    result["fetch_duration"] = fetch_duration
    result["screenshot"] = screenshot_path
    result["page_load"] = page_load

    soup = BeautifulSoup(html, "html5lib")

    # DOCTYPE
    doctype_found = any(str(item).lower().startswith("<!doctype") for item in soup.contents)
    result["DOCTYPE"] = ("✅", "HTML5") if doctype_found else ("❌", "Missing")

    # HTML lang
    lang = soup.html.get("lang") if soup.html else None
    result["HTML lang"] = ("✅", lang) if lang else ("❌", "Missing")

    # Title tag
    title = soup.title.string.strip() if soup.title and soup.title.string else None
    if title:
        length = len(title)
        status = "✅" if 10 <= length <= 60 else "⚠️"
        display_title = title if len(title) <= 70 else title[:67] + "..."
        result["Title Tag"] = (status, f"'{display_title}' ({length} chars)")
    else:
        result["Title Tag"] = ("❌", "Missing")

    # H1
    h1s = soup.find_all("h1")
    if h1s:
        result["H1 Tags"] = ("✅", f"Found {len(h1s)}: '{h1s[0].text.strip()[:50]}'")
    else:
        result["H1 Tags"] = ("❌", "No H1 tag found")

    # Canonical
    canonical = soup.find("link", rel="canonical")
    result["Canonical Tag"] = ("✅", canonical['href']) if canonical and canonical.get('href') else ("❌", "Missing")

    # Robots meta
    robots = soup.find("meta", attrs={"name": "robots"})
    if robots and robots.get("content"):
        content = robots["content"].lower()
        idx = "Allowed" if "noindex" not in content else "Disallowed"
        follow = "Allowed" if "nofollow" not in content else "Disallowed"
        snippets = "No restriction" if "nosnippet" not in content else "Restricted"
        img_preview = "Large" if "max-image-preview:large" in content else "Not specified"
        raw = robots["content"]
        result["Robots Meta"] = ("✅", f"Indexing: {idx}\nFollowing Links: {follow}\nSnippets: {snippets}\nImage Previews: {img_preview}\nRaw: '{raw}'")
    else:
        result["Robots Meta"] = ("❌", "Missing")

    # Images alt text
    images = soup.find_all("img")
    with_alt = sum(1 for img in images if img.get("alt"))
    total = len(images)
    if total > 0:
        missing = total - with_alt
        status = "✅" if missing == 0 else "⚠️"
        result["Image Alts"] = (status, f"{with_alt}/{total} images have alt text")
    else:
        result["Image Alts"] = ("⚠️", "No images found")

    # OpenGraph
    og_tags = soup.find_all("meta", property=lambda v: v and v.startswith("og:"))
    result["OpenGraph Tags"] = ("✅" if og_tags else "❌", f"Found {len(og_tags)}")

    # Twitter Cards
    twitter_tags = soup.find_all("meta", attrs={"name": lambda v: v and v.startswith("twitter:")})
    result["Twitter Cards"] = ("✅" if twitter_tags else "❌", f"Found {len(twitter_tags)}")

    return result


# ---------- GUI Thread ----------
def run_audit_thread(url):
    results = audit_website_selenium(url)

    def update_ui():
        output_box.config(state=tk.NORMAL)
        output_box.delete("1.0", tk.END)

        if "error" in results:
            output_box.insert(tk.END, results["error"])
            preview_label.config(image='', text="No preview.")
            output_box.config(state=tk.DISABLED)
            return

        # Screenshot preview
        img = Image.open(results["screenshot"])
        img = img.resize((400, 300))
        tk_img = ImageTk.PhotoImage(img)
        preview_label.config(image=tk_img)
        preview_label.image = tk_img

        # Header
        output_box.insert(tk.END, f"🔍 Website Audit: {url}\n")
        output_box.insert(tk.END, f"⏱ Audit Duration: Fetched in {results['fetch_duration']}ms\n")
        if results.get("page_load"):
            output_box.insert(tk.END, f"⚡ Estimated Page Load: {results['page_load']}s\n\n")
        else:
            output_box.insert(tk.END, f"⚡ Estimated Page Load: N/A\n\n")

        def insert_line(name, value_tuple):
            status, value = value_tuple
            color = {"✅":"green", "⚠️":"orange", "❌":"red"}.get(status, "black")
            output_box.insert(tk.END, f"- {name}: ", "bold")
            output_box.insert(tk.END, f"{status} {value}\n", color)

        output_box.insert(tk.END, "📄 Structure\n")
        insert_line("DOCTYPE", results["DOCTYPE"])
        insert_line("HTML <lang>", results["HTML lang"])
        output_box.insert(tk.END, "\n🔍 SEO Essentials\n")
        insert_line("Title Tag", results["Title Tag"])
        insert_line("H1 Tags", results["H1 Tags"])
        insert_line("Canonical Tag", results["Canonical Tag"])
        insert_line("Robots Meta", results["Robots Meta"])
        output_box.insert(tk.END, "\n🖼️ Images\n")
        insert_line("Image Alts", results["Image Alts"])
        output_box.insert(tk.END, "\n🔗 Social Sharing Tags\n")
        insert_line("OpenGraph Tags", results["OpenGraph Tags"])
        insert_line("Twitter Cards", results["Twitter Cards"])

        output_box.config(state=tk.DISABLED)

    app.after(0, update_ui)


# ---------- GUI Commands ----------
def run_audit():
    url = url_entry.get().strip()
    if not url.startswith("http"):
        url = "http://" + url
    output_box.config(state=tk.NORMAL)
    output_box.delete("1.0", tk.END)
    output_box.insert(tk.END, "🔄 Fetching website with Selenium...\n")
    output_box.config(state=tk.DISABLED)
    preview_label.config(image='', text="Loading...")
    threading.Thread(target=run_audit_thread, args=(url,), daemon=True).start()


def save_report():
    report = output_box.get("1.0", tk.END).strip()
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


# ---------- GUI Setup ----------
app = tk.Tk()
app.title("Website HTML5 + SEO Auditor (with Screenshot Preview)")
app.geometry("980x720")
app.resizable(False, False)

# URL entry
tk.Label(app, text="Enter website URL:", font=("Segoe UI", 10)).pack(pady=5)
url_entry = tk.Entry(app, width=80, font=("Segoe UI", 10))
url_entry.pack(pady=5)

# Buttons
btn_frame = tk.Frame(app)
btn_frame.pack(pady=5)
scan_button = tk.Button(btn_frame, text="Scan Website", command=run_audit, width=20)
scan_button.grid(row=0, column=0, padx=10)
save_button = tk.Button(btn_frame, text="Save Report as TXT", command=save_report, width=20)
save_button.grid(row=0, column=1, padx=10)

# Main frame
main_frame = tk.Frame(app)
main_frame.pack(pady=10, fill="both", expand=True)

# Audit Text Panel
report_frame = tk.Frame(main_frame)
report_frame.pack(side="left", fill="both", expand=True, padx=(10, 5))
tk.Label(report_frame, text="📋 Audit Results", font=("Segoe UI", 10, "bold")).pack(anchor="w")
output_box = scrolledtext.ScrolledText(report_frame, width=60, height=30, font=("Consolas", 10))
output_box.pack(fill="both", expand=True)
# Add tags for colors
output_box.tag_configure("green", foreground="green")
output_box.tag_configure("orange", foreground="orange")
output_box.tag_configure("red", foreground="red")
output_box.tag_configure("bold", font=("Consolas", 10, "bold"))

# Screenshot Preview Panel
preview_frame = tk.Frame(main_frame, width=400)
preview_frame.pack(side="right", fill="both", expand=True, padx=(5, 10))
tk.Label(preview_frame, text="🌐 Website Screenshot", font=("Segoe UI", 10, "bold")).pack(anchor="w")
preview_label = tk.Label(preview_frame, text="Preview will appear here.", width=50, height=20)
preview_label.pack(fill="both", expand=True)

app.mainloop()
