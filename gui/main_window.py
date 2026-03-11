"""
gui/main_window.py — Main tkinter application window.

Bilingual CN + EN UI with:
  - Single-file and batch-folder mode
  - Auto-detect tab (smart entity detection toggles)
  - Custom terms tab
  - Settings tab
  - Processing log with progress bar
"""

from __future__ import annotations

import logging
import os
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Callable

from core.detector import SmartDetector
from core.processor import DocxProcessor, PdfProcessor, get_processor, make_output_path
from gui.styles import FONT_FAMILY, PALETTE, apply_styles
from utils.config import AppConfig, load_config, save_config

logger = logging.getLogger(__name__)

SUPPORTED_EXTS = {".docx", ".pdf"}


class MainWindow:
    """
    Top-level application window.

    All processing runs in a background thread to keep the UI responsive.
    The thread posts log messages and progress updates back to the main thread
    via the Tk event queue (``root.after``).
    """

    VERSION = "2.0.0"

    def __init__(self) -> None:
        self.cfg   = load_config()
        self.root  = tk.Tk()
        self.root.title(f"⚖ Legal Desensitizer v{self.VERSION}  法律文件脱敏工具")
        self.root.geometry(self.cfg.window_geometry)
        self.root.minsize(700, 580)

        apply_styles(self.root)
        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # State
        self._selected_paths: list[str] = []   # file(s) or expanded folder files
        self._processing     = False

    # ─────────────────────────────────────────────────────────────────────────
    # UI Construction
    # ─────────────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = self.root

        # ── Header ──────────────────────────────────────────────────────────
        header = ttk.Frame(root)
        header.pack(fill="x", padx=20, pady=(14, 0))

        ttk.Label(
            header,
            text="⚖ Legal Document Desensitizer  法律文件脱敏工具",
            style="Title.TLabel",
        ).pack(side="left")

        ttk.Label(
            header,
            text=f"v{self.VERSION}",
            style="Muted.TLabel",
        ).pack(side="right", anchor="s", pady=2)

        ttk.Label(
            root,
            text="100% offline · 完全本地运行 · DOCX + PDF",
            style="Subtitle.TLabel",
        ).pack(anchor="w", padx=20, pady=(2, 8))

        ttk.Separator(root).pack(fill="x", padx=20, pady=2)

        # ── File Selection ───────────────────────────────────────────────────
        file_frame = ttk.LabelFrame(root, text="📁 文件选择 / File Selection", padding=10)
        file_frame.pack(fill="x", padx=20, pady=(8, 0))

        btn_row = ttk.Frame(file_frame)
        btn_row.pack(fill="x")

        self._mode_var = tk.StringVar(value="single")
        ttk.Radiobutton(
            btn_row, text="单文件 Single File",
            variable=self._mode_var, value="single",
            command=self._on_mode_change,
        ).pack(side="left", padx=(0, 10))
        ttk.Radiobutton(
            btn_row, text="文件夹批量 Batch Folder",
            variable=self._mode_var, value="batch",
            command=self._on_mode_change,
        ).pack(side="left")

        path_row = ttk.Frame(file_frame)
        path_row.pack(fill="x", pady=(6, 0))

        self._path_var = tk.StringVar()
        ttk.Entry(path_row, textvariable=self._path_var, width=60).pack(
            side="left", fill="x", expand=True, padx=(0, 8)
        )
        self._browse_btn = ttk.Button(
            path_row, text="浏览 Browse",
            command=self._browse, style="Secondary.TButton",
        )
        self._browse_btn.pack(side="right")

        ttk.Label(
            file_frame,
            text="支持 .docx / .pdf  |  Supports Word and PDF files",
            style="Muted.TLabel",
        ).pack(anchor="w", pady=(4, 0))

        # ── Notebook tabs ────────────────────────────────────────────────────
        self._notebook = ttk.Notebook(root)
        self._notebook.pack(fill="both", expand=True, padx=20, pady=(10, 0))

        self._build_auto_tab()
        self._build_custom_tab()
        self._build_settings_tab()

        # ── Action Buttons ───────────────────────────────────────────────────
        btn_bar = ttk.Frame(root)
        btn_bar.pack(fill="x", padx=20, pady=(10, 0))

        self._preview_btn = ttk.Button(
            btn_bar, text="预览 Preview",
            command=self._preview, style="Secondary.TButton",
        )
        self._preview_btn.pack(side="left", padx=(0, 8))

        self._start_btn = ttk.Button(
            btn_bar, text="开始脱敏 Desensitize",
            command=self._start, style="Primary.TButton",
        )
        self._start_btn.pack(side="right")

        ttk.Button(
            btn_bar, text="清空 Clear",
            command=self._clear, style="Secondary.TButton",
        ).pack(side="right", padx=(0, 8))

        # ── Progress + Log ───────────────────────────────────────────────────
        log_frame = ttk.LabelFrame(root, text="处理日志 / Processing Log", padding=8)
        log_frame.pack(fill="both", expand=True, padx=20, pady=(8, 0))

        self._progress_var = tk.DoubleVar(value=0)
        self._progress_bar = ttk.Progressbar(
            log_frame,
            variable=self._progress_var,
            maximum=100,
            style="Accent.Horizontal.TProgressbar",
        )
        self._progress_bar.pack(fill="x", pady=(0, 6))

        self._log_text = tk.Text(
            log_frame,
            height=7,
            font=(FONT_FAMILY, 9),
            state="disabled",
            bg=PALETTE["white"],
            relief="flat",
            wrap="word",
        )
        self._log_text.pack(fill="both", expand=True)

        sb = ttk.Scrollbar(log_frame, command=self._log_text.yview)
        sb.pack(side="right", fill="y")
        self._log_text.configure(yscrollcommand=sb.set)

        # ── Status bar ───────────────────────────────────────────────────────
        self._status_var = tk.StringVar(value="就绪  Ready — 请选择文件  Please select a file")
        ttk.Label(
            root,
            textvariable=self._status_var,
            style="Muted.TLabel",
            relief="sunken",
            anchor="w",
        ).pack(fill="x", padx=0, pady=(4, 0), ipady=3, ipadx=6)

    def _build_auto_tab(self) -> None:
        """Auto-detect tab: checkboxes for each entity type."""
        tab = ttk.Frame(self._notebook, padding=12)
        self._notebook.add(tab, text="  自动检测 Auto Detect  ")

        ttk.Label(
            tab,
            text="选择要自动检测并脱敏的信息类型 / Select entity types to auto-detect:",
            style="Normal.TLabel",
        ).pack(anchor="w", pady=(0, 8))

        cfg = self.cfg

        def _row(parent: ttk.Frame, text: str, replacement: str, var: tk.BooleanVar) -> None:
            f = ttk.Frame(parent)
            f.pack(fill="x", pady=2)
            ttk.Checkbutton(f, text=text, variable=var).pack(side="left")
            ttk.Label(f, text=f"→ {replacement}", style="Muted.TLabel").pack(side="left", padx=(8, 0))

        self._var_parties   = tk.BooleanVar(value=cfg.detect_parties)
        self._var_amounts   = tk.BooleanVar(value=cfg.detect_amounts)
        self._var_phones    = tk.BooleanVar(value=cfg.detect_phones)
        self._var_emails    = tk.BooleanVar(value=cfg.detect_emails)
        self._var_ids       = tk.BooleanVar(value=cfg.detect_ids)
        self._var_addresses = tk.BooleanVar(value=cfg.detect_addresses)
        self._var_names     = tk.BooleanVar(value=cfg.detect_names)
        self._var_companies = tk.BooleanVar(value=cfg.detect_other_companies)

        _row(tab, "☑ 合同签署方 Contract Parties (提取别名 extract alias)", "alias", self._var_parties)
        _row(tab, "☑ 金额/数字 Amounts",                                    "[AMOUNT] / [金额]", self._var_amounts)
        _row(tab, "☑ 人名 Person Names (Notices clause)",                   "[NAME] / [姓名]",   self._var_names)
        _row(tab, "☑ 其他公司名 Other Company Names",                        "[COMPANY NAME] / [公司名称]", self._var_companies)
        _row(tab, "☑ 电话号码 Phone Numbers",                               "[PHONE] / [电话]",  self._var_phones)
        _row(tab, "☑ 电子邮件 Email Addresses",                             "[EMAIL]",           self._var_emails)
        _row(tab, "☑ 身份证 / 护照 ID & Passport Numbers",                  "[证件号码] / [ID NUMBER]", self._var_ids)
        _row(tab, "☑ 地址 Addresses",                                       "[ADDRESS] / [地址]", self._var_addresses)

    def _build_custom_tab(self) -> None:
        """Custom terms tab: manual term entry."""
        tab = ttk.Frame(self._notebook, padding=12)
        self._notebook.add(tab, text="  自定义词语 Custom Terms  ")

        ttk.Label(
            tab,
            text="每行输入一个需要脱敏的词语 / Enter one term per line:",
            style="Normal.TLabel",
        ).pack(anchor="w", pady=(0, 6))

        self._custom_text = tk.Text(
            tab,
            height=10,
            font=(FONT_FAMILY, 11),
            wrap="word",
            relief="solid",
            bd=1,
        )
        self._custom_text.pack(fill="both", expand=True)

        # Pre-fill from saved config
        for term in self.cfg.custom_terms:
            self._custom_text.insert("end", term + "\n")

        repl_row = ttk.Frame(tab)
        repl_row.pack(fill="x", pady=(8, 0))
        ttk.Label(repl_row, text="替换为 Replace with:", style="Normal.TLabel").pack(side="left")
        self._custom_repl_var = tk.StringVar(value=self.cfg.custom_replacement)
        ttk.Entry(repl_row, textvariable=self._custom_repl_var, width=16).pack(side="left", padx=(8, 0))

    def _build_settings_tab(self) -> None:
        """Settings tab."""
        tab = ttk.Frame(self._notebook, padding=12)
        self._notebook.add(tab, text="  设置 Settings  ")

        ttk.Label(tab, text="输出文件名后缀 Output suffix:", style="Normal.TLabel").pack(anchor="w")
        self._suffix_var = tk.StringVar(value="_脱敏")
        ttk.Entry(tab, textvariable=self._suffix_var, width=20).pack(anchor="w", pady=(4, 12))

        ttk.Label(tab, text="日志文件 Log file:", style="Normal.TLabel").pack(anchor="w")
        ttk.Label(
            tab,
            text=str(Path.home() / "legal_desensitizer_log.txt"),
            style="Muted.TLabel",
        ).pack(anchor="w", pady=(4, 12))

        ttk.Label(tab, text="配置文件 Config file:", style="Normal.TLabel").pack(anchor="w")
        ttk.Label(
            tab,
            text=str(Path.home() / ".legal_desensitizer" / "config.json"),
            style="Muted.TLabel",
        ).pack(anchor="w", pady=(4, 0))

    # ─────────────────────────────────────────────────────────────────────────
    # File selection
    # ─────────────────────────────────────────────────────────────────────────

    def _on_mode_change(self) -> None:
        self._path_var.set("")
        self._selected_paths = []
        self._log("模式切换 Mode changed.")

    def _browse(self) -> None:
        mode = self._mode_var.get()
        if mode == "single":
            path = filedialog.askopenfilename(
                title="选择文件 Select file",
                filetypes=[
                    ("Supported files", "*.docx *.pdf"),
                    ("Word Document", "*.docx"),
                    ("PDF", "*.pdf"),
                    ("All files", "*.*"),
                ],
            )
            if path:
                self._path_var.set(path)
                self._selected_paths = [path]
                self._log(f"已选择 Selected: {os.path.basename(path)}")
        else:
            folder = filedialog.askdirectory(title="选择文件夹 Select folder")
            if folder:
                self._path_var.set(folder)
                files = [
                    str(p)
                    for p in Path(folder).rglob("*")
                    if p.suffix.lower() in SUPPORTED_EXTS
                ]
                self._selected_paths = files
                self._log(
                    f"文件夹 Folder: {folder}\n"
                    f"找到 Found {len(files)} 个支持的文件 supported files."
                )

    # ─────────────────────────────────────────────────────────────────────────
    # Processing
    # ─────────────────────────────────────────────────────────────────────────

    def _build_detector(self) -> SmartDetector:
        return SmartDetector(
            detect_parties=self._var_parties.get(),
            detect_amounts=self._var_amounts.get(),
            detect_phones=self._var_phones.get(),
            detect_emails=self._var_emails.get(),
            detect_ids=self._var_ids.get(),
            detect_addresses=self._var_addresses.get(),
            detect_names=self._var_names.get(),
            detect_other_companies=self._var_companies.get(),
        )

    def _get_custom_terms(self) -> dict[str, str]:
        """Return {term: replacement} for user-entered custom terms."""
        raw = self._custom_text.get("1.0", "end-1c")
        repl = self._custom_repl_var.get() or "【】"
        return {
            term.strip(): repl
            for term in raw.splitlines()
            if term.strip()
        }

    def _preview(self) -> None:
        if not self._selected_paths:
            messagebox.showwarning("警告 Warning", "请先选择文件。\nPlease select a file first.")
            return

        path = self._selected_paths[0]
        try:
            proc    = get_processor(path)
            text    = proc.extract_text(path)
            det     = self._build_detector()
            result  = det.analyze(text)
            repl    = det.build_replacements(result)
            repl.update(self._get_custom_terms())

            lines = ["=" * 56, "脱敏预览 Desensitization Preview", "=" * 56, ""]

            if result.parties:
                lines.append("【合同签署方 Contract Parties】")
                for full, alias in result.parties.items():
                    lines.append(f"  {full!r}  →  {alias!r}")
                lines.append("")

            by_type: dict[str, list[str]] = {}
            for em in result.entities:
                by_type.setdefault(em.entity_type, []).append(em.text)

            for etype, items in by_type.items():
                lines.append(f"【{etype}】")
                for t in items[:10]:
                    lines.append(f"  {t!r}  →  {repl.get(t, '?')!r}")
                if len(items) > 10:
                    lines.append(f"  ... 共 {len(items)} 项")
                lines.append("")

            custom = self._get_custom_terms()
            if custom:
                lines.append("【自定义词语 Custom Terms】")
                for t, r in custom.items():
                    lines.append(f"  {t!r}  →  {r!r}")
                lines.append("")

            lines += ["=" * 56, f"合计 Total replacements: {len(repl)} 种类型"]

            win = tk.Toplevel(self.root)
            win.title("预览 Preview")
            win.geometry("640x480")
            win.transient(self.root)

            txt = tk.Text(win, font=(FONT_FAMILY, 10), wrap="word")
            txt.pack(fill="both", expand=True, padx=10, pady=10)
            txt.insert("end", "\n".join(lines))
            txt.configure(state="disabled")

            sb = ttk.Scrollbar(win, command=txt.yview)
            sb.pack(side="right", fill="y")
            txt.configure(yscrollcommand=sb.set)

            ttk.Button(win, text="关闭 Close", command=win.destroy,
                       style="Secondary.TButton").pack(pady=8)

        except Exception as exc:
            messagebox.showerror("错误 Error", str(exc))

    def _start(self) -> None:
        if self._processing:
            messagebox.showinfo("提示 Info", "正在处理中，请稍候。\nProcessing in progress, please wait.")
            return
        if not self._selected_paths:
            messagebox.showwarning("警告 Warning", "请先选择文件。\nPlease select a file first.")
            return

        confirm = messagebox.askyesno(
            "确认 Confirm",
            f"将处理 {len(self._selected_paths)} 个文件。\n"
            f"Will process {len(self._selected_paths)} file(s).\n\n继续？ Continue?",
        )
        if not confirm:
            return

        self._processing = True
        self._start_btn.configure(state="disabled")
        self._preview_btn.configure(state="disabled")
        self._progress_var.set(0)
        self._log("── 开始处理 Processing started ──")

        thread = threading.Thread(target=self._process_all, daemon=True)
        thread.start()

    def _process_all(self) -> None:
        """Background thread: process all selected files."""
        paths   = list(self._selected_paths)
        total   = len(paths)
        det     = self._build_detector()
        custom  = self._get_custom_terms()
        suffix  = self._suffix_var.get() or "_脱敏"
        errors: list[str] = []
        total_replaced = 0

        for file_idx, path in enumerate(paths):
            fname = os.path.basename(path)
            self._post_log(f"\n[{file_idx+1}/{total}] {fname}")
            try:
                proc       = get_processor(path)
                text       = proc.extract_text(path)
                result     = det.analyze(text)
                replacements = det.build_replacements(result)
                replacements.update(custom)

                # Log detected entities
                if result.parties:
                    for full, alias in result.parties.items():
                        self._post_log(f"  合同方: {full!r} → {alias!r}")
                for em in result.entities[:8]:
                    self._post_log(f"  {em.entity_type}: {em.text!r} → {em.replacement!r}")
                if len(result.entities) > 8:
                    self._post_log(f"  ... 共检测到 {len(result.entities)} 个实体")

                output_path = make_output_path(path, suffix)

                def _progress(cur: int, tot: int) -> None:
                    # Para-level progress within this file, scaled to file's share
                    file_pct  = file_idx / total
                    file_share = 1 / total
                    overall = (file_pct + file_share * (cur / max(tot, 1))) * 100
                    self._post_progress(overall)

                stats = proc.process(path, replacements, output_path, _progress)
                n = stats.get("__total__", 0)
                total_replaced += n
                self._post_log(f"  ✓ 完成 Done → {os.path.basename(output_path)}  ({n} 处替换)")

            except Exception as exc:
                msg = f"  ✗ 失败 Failed: {exc}"
                self._post_log(msg)
                errors.append(f"{fname}: {exc}")
                logger.exception("Error processing %s", path)

            self._post_progress((file_idx + 1) / total * 100)

        # Done
        self._post_progress(100)
        summary = (
            f"\n── 完成 Done ──\n"
            f"处理 {total} 个文件，共替换 {total_replaced} 处。\n"
            f"Processed {total} file(s), {total_replaced} replacements total."
        )
        if errors:
            summary += f"\n失败 {len(errors)} 个: " + "; ".join(errors)
        self._post_log(summary)
        self.root.after(0, self._on_done)

    def _on_done(self) -> None:
        self._processing = False
        self._start_btn.configure(state="normal")
        self._preview_btn.configure(state="normal")
        self._status_var.set("完成 Done — 文件已保存 Files saved.")
        messagebox.showinfo("完成 Done", "脱敏处理完成！\nDesensitization complete!")

    # ─────────────────────────────────────────────────────────────────────────
    # Thread-safe UI helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _post_log(self, msg: str) -> None:
        self.root.after(0, self._log, msg)

    def _post_progress(self, pct: float) -> None:
        self.root.after(0, self._progress_var.set, min(pct, 100))

    def _log(self, msg: str) -> None:
        self._log_text.configure(state="normal")
        self._log_text.insert("end", msg + "\n")
        self._log_text.see("end")
        self._log_text.configure(state="disabled")

    # ─────────────────────────────────────────────────────────────────────────
    # Clear + Close
    # ─────────────────────────────────────────────────────────────────────────

    def _clear(self) -> None:
        self._selected_paths = []
        self._path_var.set("")
        self._custom_text.delete("1.0", "end")
        self._log_text.configure(state="normal")
        self._log_text.delete("1.0", "end")
        self._log_text.configure(state="disabled")
        self._progress_var.set(0)
        self._status_var.set("已清空 Cleared — 请重新选择文件 Please re-select files.")

    def _on_close(self) -> None:
        self._save_config()
        self.root.destroy()

    def _save_config(self) -> None:
        self.cfg.detect_parties          = self._var_parties.get()
        self.cfg.detect_amounts          = self._var_amounts.get()
        self.cfg.detect_phones           = self._var_phones.get()
        self.cfg.detect_emails           = self._var_emails.get()
        self.cfg.detect_ids              = self._var_ids.get()
        self.cfg.detect_addresses        = self._var_addresses.get()
        self.cfg.detect_names            = self._var_names.get()
        self.cfg.detect_other_companies  = self._var_companies.get()
        self.cfg.custom_replacement      = self._custom_repl_var.get()
        self.cfg.window_geometry         = self.root.geometry()

        raw   = self._custom_text.get("1.0", "end-1c")
        terms = [t.strip() for t in raw.splitlines() if t.strip()]
        self.cfg.custom_terms = terms

        save_config(self.cfg)

    # ─────────────────────────────────────────────────────────────────────────
    # Run
    # ─────────────────────────────────────────────────────────────────────────

    def run(self) -> None:
        self.root.mainloop()
