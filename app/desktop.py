"""
Lead Extractor Pro - Desktop Application
Native desktop app built with tkinter + ttk.
Works on all macOS versions.
"""
from __future__ import annotations

import asyncio
import threading
import os
import sys
from pathlib import Path
from datetime import datetime

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import (
    APP_NAME,
    APP_VERSION,
    LICENSE_KEY,
    LICENSE_SECRET,
    EXPORT_DIR,
)
from app.license.validator import validate_license
from app.search.ddg_search import ddg_search
from app.search.deep_scraper import deep_scrape_pages
from app.extractors.email_extractor import extract_emails
from app.extractors.name_extractor import (
    extract_business_name,
    extract_contact_names,
    extract_names_from_email,
)
from app.extractors.phone_extractor import extract_phones
from app.database.db import (
    save_search,
    save_leads,
    get_recent_searches,
    get_leads_by_search,
    get_all_leads,
    get_lead_stats,
    delete_search,
)
from app.export.exporter import export_to_csv, export_to_excel
from app.export.pdf_exporter import export_to_pdf


# ─── Colors ──────────────────────────────────────────────────────────────────
BG = "#1e1e2e"
BG2 = "#2a2a3e"
BG3 = "#333350"
ACCENT = "#6c63ff"
ACCENT2 = "#e94560"
SUCCESS = "#00b894"
TEXT = "#e0e0e0"
TEXT_DIM = "#8888a0"
WHITE = "#ffffff"


class LeadExtractorApp:
    """Main desktop application."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title(f"{APP_NAME} v{APP_VERSION}")
        self.root.geometry("1250x780")
        self.root.minsize(1050, 680)
        self.root.configure(bg=BG)

        # Try to set macOS dark title bar
        try:
            self.root.tk.call("::tk::unsupported::MacWindowStyle", "style",
                              self.root._w, "moveableModal", "")
        except Exception:
            pass

        # State
        self.current_leads: list[dict] = []
        self.is_searching = False
        self.license_valid = False
        self.current_tab = "search"

        # Variables
        self.num_results_var = tk.StringVar(value="20")
        self.deep_search_var = tk.BooleanVar(value=True)
        self.email_only_var = tk.BooleanVar(value=False)
        self.autosave_var = tk.BooleanVar(value=True)
        self.progress_var = tk.DoubleVar(value=0)

        # Style
        self._setup_styles()

        # Build UI
        self._build_ui()

        # Check license
        self.root.after(200, self._check_license)

    def run(self):
        self.root.mainloop()

    # ─── Styles ──────────────────────────────────────────────────────────
    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")

        # Treeview
        style.configure("Dark.Treeview",
            background=BG,
            foreground=TEXT,
            fieldbackground=BG,
            borderwidth=0,
            rowheight=30,
            font=("Helvetica", 12),
        )
        style.configure("Dark.Treeview.Heading",
            background=BG3,
            foreground=WHITE,
            borderwidth=0,
            font=("Helvetica", 12, "bold"),
            relief="flat",
        )
        style.map("Dark.Treeview",
            background=[("selected", ACCENT)],
            foreground=[("selected", WHITE)],
        )
        style.map("Dark.Treeview.Heading",
            background=[("active", ACCENT)],
        )

        # Progressbar
        style.configure("Accent.Horizontal.TProgressbar",
            troughcolor=BG3,
            background=ACCENT,
            thickness=8,
            borderwidth=0,
        )

        # Scrollbar
        style.configure("Dark.Vertical.TScrollbar",
            troughcolor=BG,
            background=BG3,
            borderwidth=0,
            arrowsize=0,
        )

    # ─── License ─────────────────────────────────────────────────────────
    def _check_license(self):
        result = validate_license(LICENSE_KEY, LICENSE_SECRET)
        if result.valid:
            self.license_valid = True
            self.license_label.configure(
                text=f"✅ {result.licensee} | {result.plan.upper()} | Exp: {result.expires_at[:10]}",
                fg=SUCCESS,
            )
            self.search_btn.configure(state="normal")
        else:
            self.license_valid = False
            self.license_label.configure(text=f"❌ {result.error}", fg=ACCENT2)
            key = self._ask_license()
            if key:
                r2 = validate_license(key, LICENSE_SECRET)
                if r2.valid:
                    self.license_valid = True
                    self.license_label.configure(
                        text=f"✅ {r2.licensee} | {r2.plan.upper()}", fg=SUCCESS)
                    self.search_btn.configure(state="normal")
                else:
                    messagebox.showerror("Invalid License", r2.error)

    def _ask_license(self) -> str:
        dialog = tk.Toplevel(self.root)
        dialog.title("License Activation")
        dialog.geometry("450x150")
        dialog.configure(bg=BG)
        dialog.transient(self.root)
        dialog.grab_set()

        tk.Label(dialog, text="Enter your license key:", bg=BG, fg=TEXT,
                 font=("Helvetica", 13)).pack(pady=(20, 5))
        entry = tk.Entry(dialog, width=50, font=("Helvetica", 11), show="•",
                         bg=BG2, fg=TEXT, insertbackground=TEXT, relief="flat",
                         highlightbackground=BG3, highlightthickness=1)
        entry.pack(padx=20, pady=5)

        result = {"key": ""}

        def submit():
            result["key"] = entry.get().strip()
            dialog.destroy()

        tk.Button(dialog, text="Activate", command=submit, bg=ACCENT, fg=WHITE,
                  font=("Helvetica", 12, "bold"), relief="flat", padx=20, pady=5,
                  activebackground=ACCENT2, cursor="hand2").pack(pady=10)

        entry.bind("<Return>", lambda e: submit())
        dialog.wait_window()
        return result["key"]

    # ─── Build UI ────────────────────────────────────────────────────────
    def _build_ui(self):
        # ── Sidebar ──
        self.sidebar = tk.Frame(self.root, bg=BG2, width=230)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # Logo
        tk.Label(self.sidebar, text="🎯", font=("Helvetica", 28),
                 bg=BG2, fg=WHITE).pack(pady=(20, 0))
        tk.Label(self.sidebar, text=APP_NAME, font=("Helvetica", 15, "bold"),
                 bg=BG2, fg=WHITE).pack(pady=(2, 0))
        tk.Label(self.sidebar, text=f"v{APP_VERSION}", font=("Helvetica", 10),
                 bg=BG2, fg=TEXT_DIM).pack(pady=(0, 15))

        # Nav buttons
        self.nav_btns = {}
        for label, key in [
            ("🔍  Search & Extract", "search"),
            ("📋  Saved Leads", "leads"),
            ("📜  History", "history"),
        ]:
            btn = tk.Button(
                self.sidebar, text=label, font=("Helvetica", 13),
                bg=BG2, fg=TEXT, relief="flat", anchor="w", padx=18, pady=8,
                activebackground=ACCENT, activeforeground=WHITE, cursor="hand2",
                command=lambda k=key: self._switch_tab(k),
            )
            btn.pack(fill="x", padx=8, pady=2)
            self.nav_btns[key] = btn

        # Separator
        tk.Frame(self.sidebar, bg=BG3, height=1).pack(fill="x", padx=18, pady=15)

        # Search engine badge
        tk.Label(self.sidebar, text="⚙️ Search Engine", font=("Helvetica", 11, "bold"),
                 bg=BG2, fg=TEXT).pack(anchor="w", padx=18)
        tk.Label(self.sidebar, text="✅ DuckDuckGo (Free)", font=("Helvetica", 10),
                 bg=BG2, fg=SUCCESS).pack(anchor="w", padx=18, pady=(2, 10))

        # Stats
        tk.Label(self.sidebar, text="📊 Stats", font=("Helvetica", 11, "bold"),
                 bg=BG2, fg=TEXT).pack(anchor="w", padx=18, pady=(5, 2))
        self.stats_label = tk.Label(
            self.sidebar, text="Loading...", font=("Helvetica", 10),
            bg=BG2, fg=TEXT_DIM, justify="left", anchor="w",
        )
        self.stats_label.pack(anchor="w", padx=18, pady=(0, 10))

        # License at bottom
        spacer = tk.Frame(self.sidebar, bg=BG2)
        spacer.pack(fill="both", expand=True)
        self.license_label = tk.Label(
            self.sidebar, text="Checking license...", font=("Helvetica", 9),
            bg=BG2, fg=TEXT_DIM, wraplength=200, justify="left",
        )
        self.license_label.pack(anchor="sw", padx=15, pady=(0, 15))

        # ── Main Content ──
        self.main_frame = tk.Frame(self.root, bg=BG)
        self.main_frame.pack(side="right", fill="both", expand=True)

        # Tab frames
        self.tabs = {}
        self._build_search_tab()
        self._build_leads_tab()
        self._build_history_tab()

        self._switch_tab("search")
        self._update_stats()

    # ─── Search Tab ──────────────────────────────────────────────────────
    def _build_search_tab(self):
        frame = tk.Frame(self.main_frame, bg=BG)
        self.tabs["search"] = frame

        # Title
        title_frame = tk.Frame(frame, bg=BG)
        title_frame.pack(fill="x", padx=25, pady=(20, 0))
        tk.Label(title_frame, text="🔍 Lead Extractor — Deep Search",
                 font=("Helvetica", 20, "bold"), bg=BG, fg=WHITE).pack(anchor="w")
        tk.Label(title_frame, text="Search the web, scrape websites + PDFs, extract emails & contacts",
                 font=("Helvetica", 11), bg=BG, fg=TEXT_DIM).pack(anchor="w", pady=(2, 0))

        # Search bar
        search_frame = tk.Frame(frame, bg=BG3, highlightbackground=BG3, highlightthickness=1)
        search_frame.pack(fill="x", padx=25, pady=(15, 0))

        self.search_entry = tk.Entry(
            search_frame, font=("Helvetica", 14), bg=BG2, fg=TEXT,
            insertbackground=TEXT, relief="flat", highlightthickness=0,
        )
        self.search_entry.pack(side="left", fill="x", expand=True, padx=(12, 5), pady=10, ipady=6)
        self.search_entry.insert(0, "")
        self.search_entry.bind("<Return>", lambda e: self._start_search())

        # Placeholder
        self.search_entry.insert(0, "Enter keyword... e.g. plumbing companies in Houston Texas")
        self.search_entry.configure(fg=TEXT_DIM)
        self.search_entry.bind("<FocusIn>", self._on_search_focus_in)
        self.search_entry.bind("<FocusOut>", self._on_search_focus_out)

        num_menu = tk.OptionMenu(search_frame, self.num_results_var, "10", "20", "30", "50")
        num_menu.configure(bg=BG3, fg=TEXT, font=("Helvetica", 12),
                           activebackground=ACCENT, activeforeground=WHITE,
                           highlightthickness=0, relief="flat")
        num_menu["menu"].configure(bg=BG2, fg=TEXT, font=("Helvetica", 11))
        num_menu.pack(side="left", padx=5, pady=10)

        self.search_btn = tk.Button(
            search_frame, text="🚀 Extract Leads",
            font=("Helvetica", 13, "bold"), bg=ACCENT2, fg=WHITE,
            relief="flat", padx=18, pady=6, activebackground="#c0392b",
            cursor="hand2", state="disabled",
            command=self._start_search,
        )
        self.search_btn.pack(side="right", padx=(5, 12), pady=10)

        # Options
        opts_frame = tk.Frame(frame, bg=BG)
        opts_frame.pack(fill="x", padx=25, pady=(8, 0))

        for var, text in [
            (self.deep_search_var, "Deep Search (contact pages + PDFs)"),
            (self.email_only_var, "Only with emails"),
            (self.autosave_var, "Auto-save to database"),
        ]:
            cb = tk.Checkbutton(
                opts_frame, text=text, variable=var,
                font=("Helvetica", 11), bg=BG, fg=TEXT,
                selectcolor=BG2, activebackground=BG, activeforeground=TEXT,
                highlightthickness=0,
            )
            cb.pack(side="left", padx=(0, 15))

        # Progress
        prog_frame = tk.Frame(frame, bg=BG)
        prog_frame.pack(fill="x", padx=25, pady=(8, 0))

        self.status_label = tk.Label(
            prog_frame, text="Ready to search", font=("Helvetica", 11),
            bg=BG, fg=TEXT_DIM, anchor="w",
        )
        self.status_label.pack(fill="x")

        self.progress_bar = ttk.Progressbar(
            prog_frame, variable=self.progress_var, maximum=100,
            style="Accent.Horizontal.TProgressbar",
        )
        self.progress_bar.pack(fill="x", pady=(3, 0))

        # Results table
        table_frame = tk.Frame(frame, bg=BG2, highlightbackground=BG3, highlightthickness=1)
        table_frame.pack(fill="both", expand=True, padx=25, pady=(10, 0))

        # Metrics
        self.metrics_frame = tk.Frame(table_frame, bg=BG2)
        self.metrics_frame.pack(fill="x", padx=10, pady=(8, 5))

        self.metric_labels = {}
        for key, label in [("total", "Total: 0"), ("emails", "Emails: 0"),
                           ("phones", "Phones: 0"), ("names", "Names: 0")]:
            lbl = tk.Label(self.metrics_frame, text=label, font=("Helvetica", 12, "bold"),
                           bg=BG2, fg=TEXT_DIM)
            lbl.pack(side="left", padx=15)
            self.metric_labels[key] = lbl

        # Treeview
        tree_container = tk.Frame(table_frame, bg=BG)
        tree_container.pack(fill="both", expand=True, padx=5, pady=(0, 5))

        columns = ("business", "contact", "email", "phone", "website")
        self.tree = ttk.Treeview(
            tree_container, columns=columns, show="headings",
            style="Dark.Treeview",
        )

        self.tree.heading("business", text="Business Name")
        self.tree.heading("contact", text="Contact")
        self.tree.heading("email", text="Email")
        self.tree.heading("phone", text="Phone")
        self.tree.heading("website", text="Website")

        self.tree.column("business", width=200, minwidth=100)
        self.tree.column("contact", width=130, minwidth=80)
        self.tree.column("email", width=220, minwidth=120)
        self.tree.column("phone", width=140, minwidth=80)
        self.tree.column("website", width=200, minwidth=100)

        scrollbar = ttk.Scrollbar(tree_container, orient="vertical", command=self.tree.yview,
                                  style="Dark.Vertical.TScrollbar")
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Export buttons
        export_frame = tk.Frame(frame, bg=BG)
        export_frame.pack(fill="x", padx=25, pady=(8, 12))

        for text, cmd in [
            ("📄 Export CSV", lambda: self._export("csv")),
            ("📊 Export Excel", lambda: self._export("excel")),
            ("📕 Export PDF", lambda: self._export("pdf")),
            ("💾 Save As...", self._save_as),
        ]:
            btn = tk.Button(
                export_frame, text=text, font=("Helvetica", 12),
                bg=BG3, fg=TEXT, relief="flat", padx=14, pady=5,
                activebackground=ACCENT, activeforeground=WHITE,
                cursor="hand2", command=cmd,
            )
            btn.pack(side="left", padx=4)

    # ─── Saved Leads Tab ─────────────────────────────────────────────────
    def _build_leads_tab(self):
        frame = tk.Frame(self.main_frame, bg=BG)
        self.tabs["leads"] = frame

        tk.Label(frame, text="📋 Saved Leads", font=("Helvetica", 20, "bold"),
                 bg=BG, fg=WHITE).pack(anchor="w", padx=25, pady=(20, 5))

        # Filter
        filter_frame = tk.Frame(frame, bg=BG3)
        filter_frame.pack(fill="x", padx=25, pady=(5, 10))

        self.leads_filter = tk.Entry(
            filter_frame, font=("Helvetica", 13), bg=BG2, fg=TEXT,
            insertbackground=TEXT, relief="flat",
        )
        self.leads_filter.pack(side="left", fill="x", expand=True, padx=(12, 5), pady=8, ipady=4)
        self.leads_filter.insert(0, "🔎 Filter leads...")
        self.leads_filter.configure(fg=TEXT_DIM)
        self.leads_filter.bind("<FocusIn>", lambda e: (
            self.leads_filter.delete(0, "end"),
            self.leads_filter.configure(fg=TEXT)) if self.leads_filter.get().startswith("🔎") else None)
        self.leads_filter.bind("<Return>", lambda e: self._load_saved_leads())

        tk.Button(filter_frame, text="Load", font=("Helvetica", 12),
                  bg=ACCENT, fg=WHITE, relief="flat", padx=15, pady=4,
                  command=self._load_saved_leads, cursor="hand2").pack(side="right", padx=(0, 12), pady=8)

        # Table
        tree_frame = tk.Frame(frame, bg=BG)
        tree_frame.pack(fill="both", expand=True, padx=25, pady=(0, 5))

        columns = ("business", "contact", "email", "phone", "website", "query")
        self.leads_tree = ttk.Treeview(
            tree_frame, columns=columns, show="headings", style="Dark.Treeview")

        for col, heading, width in [
            ("business", "Business", 170), ("contact", "Contact", 120),
            ("email", "Email", 190), ("phone", "Phone", 130),
            ("website", "Website", 160), ("query", "Search Query", 150),
        ]:
            self.leads_tree.heading(col, text=heading)
            self.leads_tree.column(col, width=width, minwidth=80)

        sb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.leads_tree.yview)
        self.leads_tree.configure(yscrollcommand=sb.set)
        self.leads_tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        # Export
        exp_frame = tk.Frame(frame, bg=BG)
        exp_frame.pack(fill="x", padx=25, pady=(5, 12))
        for text, fmt in [("📄 Export CSV", "csv"), ("📊 Export Excel", "excel"), ("📕 Export PDF", "pdf")]:
            tk.Button(exp_frame, text=text, font=("Helvetica", 12),
                      bg=BG3, fg=TEXT, relief="flat", padx=14, pady=5,
                      activebackground=ACCENT, cursor="hand2",
                      command=lambda f=fmt: self._export_saved(f)).pack(side="left", padx=4)

    # ─── History Tab ─────────────────────────────────────────────────────
    def _build_history_tab(self):
        frame = tk.Frame(self.main_frame, bg=BG)
        self.tabs["history"] = frame

        tk.Label(frame, text="📜 Search History", font=("Helvetica", 20, "bold"),
                 bg=BG, fg=WHITE).pack(anchor="w", padx=25, pady=(20, 10))

        # Scrollable list
        canvas = tk.Canvas(frame, bg=BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        self.history_container = tk.Frame(canvas, bg=BG)

        self.history_container.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.history_container, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True, padx=25)
        scrollbar.pack(side="right", fill="y")
        self.history_canvas = canvas

    # ─── Tab Switching ───────────────────────────────────────────────────
    def _switch_tab(self, tab_name: str):
        for f in self.tabs.values():
            f.pack_forget()
        self.tabs[tab_name].pack(fill="both", expand=True)

        for key, btn in self.nav_btns.items():
            btn.configure(bg=ACCENT if key == tab_name else BG2)

        self.current_tab = tab_name
        if tab_name == "leads":
            self._load_saved_leads()
        elif tab_name == "history":
            self._load_history()

    # ─── Search Entry Placeholder ────────────────────────────────────────
    def _on_search_focus_in(self, event):
        if self.search_entry.get().startswith("Enter keyword"):
            self.search_entry.delete(0, "end")
            self.search_entry.configure(fg=TEXT)

    def _on_search_focus_out(self, event):
        if not self.search_entry.get().strip():
            self.search_entry.insert(0, "Enter keyword... e.g. plumbing companies in Houston Texas")
            self.search_entry.configure(fg=TEXT_DIM)

    # ─── Search Logic ────────────────────────────────────────────────────
    def _start_search(self):
        keyword = self.search_entry.get().strip()
        if not keyword or keyword.startswith("Enter keyword"):
            messagebox.showwarning("Input Required", "Please enter a keyword to search.")
            return
        if self.is_searching:
            return

        self.is_searching = True
        self.search_btn.configure(state="disabled", text="⏳ Searching...")
        self.progress_var.set(0)

        for item in self.tree.get_children():
            self.tree.delete(item)
        self.current_leads = []

        thread = threading.Thread(
            target=self._search_worker,
            args=(keyword, int(self.num_results_var.get())),
            daemon=True,
        )
        thread.start()

    def _search_worker(self, keyword: str, num_results: int):
        try:
            self.root.after(0, lambda: self.status_label.configure(text=f"🔎 Searching for '{keyword}'...", fg=TEXT))
            self.root.after(0, lambda: self.progress_var.set(10))

            search_response = ddg_search(keyword, num_results)

            if search_response.error:
                self.root.after(0, lambda: messagebox.showerror("Search Error", search_response.error))
                self._search_done()
                return

            if not search_response.results:
                self.root.after(0, lambda: self.status_label.configure(text="⚠️ No results found", fg=ACCENT2))
                self._search_done()
                return

            self.root.after(0, lambda: self.status_label.configure(
                text=f"✅ Found {len(search_response.results)} results. Deep scraping..."))
            self.root.after(0, lambda: self.progress_var.set(20))

            # Deep scrape
            urls = [r.url for r in search_response.results]
            loop = asyncio.new_event_loop()

            if self.deep_search_var.get():
                self.root.after(0, lambda: self.status_label.configure(
                    text="🌐 Deep scraping (websites + contact pages + PDFs)..."))
                pages = loop.run_until_complete(deep_scrape_pages(urls))
            else:
                from app.search.scraper import scrape_pages
                pages = loop.run_until_complete(scrape_pages(urls))
            loop.close()

            self.root.after(0, lambda: self.progress_var.set(60))
            self.root.after(0, lambda: self.status_label.configure(
                text="🔍 Extracting emails, names, and phone numbers..."))

            # Extract leads
            leads = []
            total = len(pages)
            for i, (result, page) in enumerate(zip(search_response.results, pages)):
                prog = 60 + (40 * (i + 1) / total)
                self.root.after(0, lambda p=prog: self.progress_var.set(min(p, 99)))

                biz = extract_business_name(result.title, result.url, result.snippet)

                if not page.success:
                    leads.append({
                        "business_name": biz, "contact_name": "", "email": "",
                        "phone": "", "website": result.display_link,
                        "source_url": result.url, "snippet": result.snippet,
                    })
                    continue

                emails = extract_emails(page.text_content, page.html_content)
                phones = extract_phones(page.text_content, page.html_content)
                names = extract_contact_names(page.text_content)

                if emails and not names:
                    for email in emails:
                        d = extract_names_from_email(email)
                        if d:
                            names.append(d)

                if emails:
                    for j, email in enumerate(emails):
                        cn = names[j] if j < len(names) else (names[0] if names else "")
                        ph = phones[j] if j < len(phones) else (phones[0] if phones else "")
                        leads.append({
                            "business_name": biz, "contact_name": cn, "email": email,
                            "phone": ph, "website": result.display_link,
                            "source_url": result.url, "snippet": result.snippet[:200],
                        })
                else:
                    leads.append({
                        "business_name": biz,
                        "contact_name": names[0] if names else "",
                        "email": "",
                        "phone": phones[0] if phones else "",
                        "website": result.display_link,
                        "source_url": result.url,
                        "snippet": result.snippet[:200],
                    })

            if self.email_only_var.get():
                leads = [l for l in leads if l.get("email")]

            if self.autosave_var.get() and leads:
                sid = save_search(keyword, len(search_response.results))
                save_leads(sid, leads)

            self.current_leads = leads
            self.root.after(0, lambda: self._display_results(leads))

        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
        finally:
            self._search_done()

    def _search_done(self):
        self.root.after(0, lambda: self.search_btn.configure(state="normal", text="🚀 Extract Leads"))
        self.root.after(0, lambda: self.progress_var.set(100))
        self.is_searching = False
        self.root.after(0, self._update_stats)

    def _display_results(self, leads: list[dict]):
        for item in self.tree.get_children():
            self.tree.delete(item)

        total = len(leads)
        em = sum(1 for l in leads if l.get("email"))
        ph = sum(1 for l in leads if l.get("phone"))
        nm = sum(1 for l in leads if l.get("contact_name"))

        self.metric_labels["total"].configure(text=f"Total: {total}", fg=WHITE)
        self.metric_labels["emails"].configure(text=f"Emails: {em}", fg=SUCCESS)
        self.metric_labels["phones"].configure(text=f"Phones: {ph}", fg=TEXT)
        self.metric_labels["names"].configure(text=f"Names: {nm}", fg=TEXT)

        for lead in leads:
            self.tree.insert("", "end", values=(
                lead.get("business_name", "")[:45],
                lead.get("contact_name", "")[:30],
                lead.get("email", ""),
                lead.get("phone", ""),
                lead.get("website", "")[:40],
            ))

        self.status_label.configure(
            text=f"✅ Done! {total} leads extracted ({em} emails, {ph} phones)",
            fg=SUCCESS,
        )

    # ─── Export ──────────────────────────────────────────────────────────
    def _export(self, fmt: str):
        if not self.current_leads:
            messagebox.showinfo("No Data", "No leads to export. Run a search first.")
            return
        keyword = self.search_entry.get().strip()
        if keyword.startswith("Enter keyword"):
            keyword = "leads"
        try:
            if fmt == "csv":
                path = export_to_csv(self.current_leads)
            elif fmt == "excel":
                path = export_to_excel(self.current_leads)
            elif fmt == "pdf":
                path = export_to_pdf(self.current_leads, query=keyword)
            else:
                return
            messagebox.showinfo("✅ Export Success", f"Exported to:\n{path}")
            os.system(f'open "{path.parent}"')
        except Exception as e:
            messagebox.showerror("Export Error", str(e))

    def _save_as(self):
        if not self.current_leads:
            messagebox.showinfo("No Data", "No leads to export.")
            return
        EXPORT_DIR.mkdir(parents=True, exist_ok=True)
        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv"), ("Excel", "*.xlsx"), ("PDF", "*.pdf")],
            initialdir=str(EXPORT_DIR),
        )
        if not filepath:
            return
        try:
            keyword = self.search_entry.get().strip()
            if keyword.startswith("Enter keyword"):
                keyword = "leads"
            p = Path(filepath)
            if p.suffix == ".csv":
                export_to_csv(self.current_leads, p.name)
            elif p.suffix == ".xlsx":
                export_to_excel(self.current_leads, p.name)
            elif p.suffix == ".pdf":
                export_to_pdf(self.current_leads, query=keyword, filename=p.name)
            messagebox.showinfo("✅ Saved", f"Saved to:\n{filepath}")
        except Exception as e:
            messagebox.showerror("Save Error", str(e))

    def _export_saved(self, fmt: str):
        leads = get_all_leads()
        if not leads:
            messagebox.showinfo("No Data", "No saved leads.")
            return
        try:
            if fmt == "csv":
                path = export_to_csv(leads, "all_leads.csv")
            elif fmt == "excel":
                path = export_to_excel(leads, "all_leads.xlsx")
            elif fmt == "pdf":
                path = export_to_pdf(leads, query="All Saved Leads", filename="all_leads.pdf")
            else:
                return
            messagebox.showinfo("✅ Exported", f"Exported to:\n{path}")
            os.system(f'open "{path.parent}"')
        except Exception as e:
            messagebox.showerror("Export Error", str(e))

    # ─── Saved Leads ─────────────────────────────────────────────────────
    def _load_saved_leads(self):
        for item in self.leads_tree.get_children():
            self.leads_tree.delete(item)

        leads = get_all_leads()
        ft = self.leads_filter.get().strip().lower()
        if ft.startswith("🔎"):
            ft = ""

        for lead in leads:
            if ft:
                combined = " ".join(str(v) for v in lead.values()).lower()
                if ft not in combined:
                    continue
            self.leads_tree.insert("", "end", values=(
                lead.get("business_name", "")[:40],
                lead.get("contact_name", "")[:25],
                lead.get("email", ""),
                lead.get("phone", ""),
                lead.get("website", "")[:35],
                lead.get("search_query", "")[:30],
            ))

    # ─── History ─────────────────────────────────────────────────────────
    def _load_history(self):
        for w in self.history_container.winfo_children():
            w.destroy()

        searches = get_recent_searches(30)
        if not searches:
            tk.Label(self.history_container, text="No search history yet.",
                     font=("Helvetica", 13), bg=BG, fg=TEXT_DIM).pack(pady=20)
            return

        for i, s in enumerate(searches):
            card = tk.Frame(self.history_container, bg=BG2, highlightbackground=BG3,
                            highlightthickness=1)
            card.pack(fill="x", padx=5, pady=3)

            tk.Label(card, text="🔎", font=("Helvetica", 16), bg=BG2, fg=TEXT).pack(side="left", padx=(12, 5), pady=8)
            tk.Label(card,
                     text=f"{s['query']}  —  {s['num_leads']} leads  |  {s['created_at']}",
                     font=("Helvetica", 12), bg=BG2, fg=TEXT, anchor="w").pack(side="left", fill="x", expand=True, padx=5, pady=8)

            tk.Button(card, text="🗑️", font=("Helvetica", 12), bg=BG2, fg=ACCENT2,
                      relief="flat", cursor="hand2",
                      command=lambda sid=s["id"]: self._delete_search(sid)).pack(side="right", padx=10, pady=8)

        self.history_canvas.update_idletasks()
        self.history_canvas.configure(scrollregion=self.history_canvas.bbox("all"))

    def _delete_search(self, sid: int):
        if messagebox.askyesno("Confirm", "Delete this search and its leads?"):
            delete_search(sid)
            self._load_history()
            self._update_stats()

    # ─── Stats ───────────────────────────────────────────────────────────
    def _update_stats(self):
        try:
            s = get_lead_stats()
            self.stats_label.configure(
                text=f"Searches: {s['total_searches']}\n"
                     f"Leads: {s['total_leads']}\n"
                     f"Emails: {s['unique_emails']}\n"
                     f"Domains: {s['unique_domains']}")
        except Exception:
            self.stats_label.configure(text="No data yet")


def main():
    app = LeadExtractorApp()
    app.run()


if __name__ == "__main__":
    main()
