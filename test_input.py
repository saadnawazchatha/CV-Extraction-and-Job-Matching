import json
import tkinter as tk
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from queue import Empty, SimpleQueue
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText

import httpx

from app.ranking.schema import SavedCV
from workbook import (
    INFO_FILE, LEGACY_FILE, RANKING_FILE, RAW_FILE, SCORE_FIELDS,
    append_information, append_ranking, append_raw, read_saved,
)

API_URL = "http://127.0.0.1:8000"
CV_TYPES = [("CV files", "*.doc *.docx *.pdf *.png *.jpg *.jpeg *.tif *.tiff *.bmp *.webp")]
RAW, INFO, RANK = "Raw text", "Information", "Ranking"


@dataclass(eq=False)
class QueuedCV:
    key: object  # Path, (source, record number), or a unique token for pasted input.
    name: str
    upload: Path | None = None
    raw_text: str | None = None
    information: dict | None = None
    raw_pending_save: bool = False
    info_pending_save: bool = False


def raw_input(key, name, text):
    if not name.strip() or not text.strip():
        raise ValueError("Supply a filename and nonempty raw text.")
    return QueuedCV(key, name.strip(), raw_text=text)


def json_inputs(source, fallback_name, value):
    """Accept an extraction response, one bare CV, or a batch of named extraction responses."""
    if isinstance(value, dict) and "cvs" in value:
        value = value["cvs"]
        if not isinstance(value, list):
            raise ValueError("The 'cvs' field must contain a list.")
    records = value if isinstance(value, list) else [value]
    if not records:
        raise ValueError("The JSON contains no CVs.")
    items = []
    for number, record in enumerate(records, 1):
        if not isinstance(record, dict):
            raise ValueError(f"CV {number} must be a JSON object.")
        if "extracted_data" not in record:
            if len(records) != 1 or not fallback_name.strip():
                raise ValueError("Give each CV a file_name and extracted_data in a JSON batch."
                                 " For a single bare CV, supply a filename.")
            record = {"file_name": fallback_name, "extracted_data": record}
        try:
            cv = SavedCV.model_validate(record)
        except ValueError as error:
            raise ValueError(f"Invalid CV {number}: {error}") from error
        items.append(QueuedCV((source, number), cv.file_name, information=cv.extracted_data.model_dump()))
    return items


def api_result(response):
    if response.is_error:
        try:
            detail = response.json().get("detail")
        except (ValueError, AttributeError):
            detail = None
        if isinstance(detail, list):
            detail = "\n".join(
                f"{'.'.join(map(str, item.get('loc', ())))}: {item.get('msg', '')}"
                for item in detail if isinstance(item, dict)
            )
        if response.status_code == 404:
            detail = f"Restart the updated FastAPI service to enable {response.request.url.path}."
        raise ValueError(detail or f"The API returned HTTP {response.status_code}.")
    response.raise_for_status()
    result = response.json()
    if not isinstance(result, dict):
        raise ValueError("The API returned an unexpected response.")
    return result


def prepare_cv(cv, goal, client, notify):
    # Imported text and JSON already satisfy their stages. Only newly produced outputs need saving.
    if goal == RAW or cv.information is None:
        if cv.raw_text is None:
            if cv.upload is None:
                raise ValueError("Raw text is unavailable for a JSON-only input.")
            notify(f"Parsing {cv.name}...")
            with cv.upload.open("rb") as stream:
                result = api_result(client.post("/cv/raw", files={"file": (cv.name, stream)}))
            text, name = result.get("raw_text"), result.get("file_name")
            if not isinstance(text, str) or not text.strip() or not isinstance(name, str) or not name.strip():
                raise ValueError("Expected file_name and raw_text from /cv/raw. Restart the updated API.")
            cv.name, cv.raw_text, cv.raw_pending_save = name, text, True
        if cv.raw_pending_save:
            append_raw(cv.name, cv.raw_text)
            cv.raw_pending_save = False
    if goal == RAW:
        return
    if cv.information is None:
        notify(f"Extracting information from {cv.name}...")
        result = api_result(client.post("/cv/extract", json={"file_name": cv.name, "raw_text": cv.raw_text}))
        if result.get("file_name") != cv.name or not isinstance(result.get("extracted_data"), dict):
            raise ValueError("Expected the submitted filename and extracted_data from /cv/extract.")
        cv.information, cv.info_pending_save = result["extracted_data"], True
    if cv.info_pending_save:
        append_information(cv.name, cv.information)
        cv.info_pending_save = False


def ranked_rows(cvs, report):
    ranked = report.get("ranked_cvs")
    if not isinstance(ranked, list) or len(ranked) != len(cvs):
        raise ValueError("The API did not rank the complete batch.")
    by_name = defaultdict(list)
    for cv in cvs:
        by_name[cv.name.strip()].append(cv)
    rows = []
    for position, item in enumerate(ranked, 1):
        if not isinstance(item, dict) or item.get("rank") != position:
            raise ValueError("Expected consecutive ranks starting at 1. Restart the updated API.")
        if any(type(item.get(k)) not in (float, int) or not 0 <= item[k] <= 10 for k in SCORE_FIELDS):
            raise ValueError("The API returned an invalid score.")
        # Filenames can repeat. Match the normalized JSON as well and consume each input once.
        choices = by_name.get(item.get("file_name"), [])
        cv = next((entry for entry in choices if entry.information == item.get("extracted_data")), None)
        if cv is None:
            raise ValueError("A ranked result could not be matched to the submitted CVs.")
        choices.remove(cv)
        rows.append((cv, item))
    return rows


class Batch:
    def __init__(self):
        self.cvs = []
        self.ranked_for = None
        self.report = None
        self.rows = []
        self.ranking_saved = False

    def run(self, goal, description, notify):
        description = description.strip()
        if not self.cvs:
            raise ValueError("Add at least one CV, raw text, or JSON record.")
        if goal == RANK and not description:
            raise ValueError("Enter a job description to rank CVs.")
        if goal == RAW and any(cv.raw_text is None and cv.upload is None for cv in self.cvs):
            raise ValueError("Remove JSON-only inputs to request raw text.")
        timeout = httpx.Timeout(30, connect=5, read=None)
        with httpx.Client(base_url=API_URL, timeout=timeout, trust_env=False) as client:
            failures = []
            for cv in self.cvs:
                try:
                    prepare_cv(cv, goal, client, notify)
                except httpx.ConnectError:
                    raise
                except (OSError, ValueError, httpx.HTTPError) as error:
                    failures.append(f"{cv.name}: {error}")
            if failures:
                raise ValueError("\n".join(failures))
            if goal != RANK:
                return [(cv, None) for cv in self.cvs], None

            key = description, tuple(self.cvs)
            if self.ranked_for != key:
                notify(f"Ranking {len(self.cvs)} CVs...")
                inputs = [{"file_name": cv.name, "extracted_data": cv.information} for cv in self.cvs]
                report = api_result(client.post(
                    "/cv/rank", params={"include_details": "true"},
                    json={"job_description": description, "cvs": inputs},
                ))
                if report.get("job_description") != description:
                    raise ValueError("The API returned results for a different job description.")
                self.rows = ranked_rows(self.cvs, report)
                self.report, self.ranked_for, self.ranking_saved = report, key, False
        if not self.ranking_saved:
            notify(f"Saving {RANKING_FILE.name}...")
            append_ranking(description, self.report["ranked_cvs"])
            self.ranking_saved = True
        return self.rows, self.report


def ranking_notes(report, item):
    weights = ", ".join(f"{key} {value:.0%}" for key, value in report["weights"].items())
    lines = [f"Rank {item['rank']}     Overall {item['overall_score']:.2f}/10", f"Job weights: {weights}"]
    requirements = {r["id"]: r for r in report["requirements"]}
    for match in item["matches"]:
        number = match["requirement_id"]
        requirement = requirements[number]
        evidence = ", ".join(match["evidence"]) or "no supporting CV field"
        status = match["status"].replace("_", " ")
        if number in item["required_to_review"]:
            status += " (review)"
        lines.append(f"{requirement['text']} [{requirement['priority']}]\n    {status} — {evidence}")
    return "\n\n".join(lines)


class ScreeningWindow:
    def __init__(self, window):
        self.window = window
        self.worker = ThreadPoolExecutor(max_workers=1)
        self.batch = Batch()
        self.rows, self.report, self.view = [], None, None
        self.busy = False
        window.title("CV screening tester")
        window.geometry("930x680")
        frame = ttk.Frame(window, padding=10)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Job description (required for ranking)").pack(anchor="w")
        self.description = ScrolledText(frame, height=4, wrap="word")
        self.description.pack(fill="x", pady=(2, 8))
        self.description.bind("<<Modified>>", self.description_changed)

        sources = ttk.Frame(frame)
        sources.pack(fill="x")
        self.add_buttons = []
        add_cv = ttk.Button(sources, text="Add CV files…", command=lambda: self.choose_files("CV"))
        add_cv.pack(side="left", padx=(0, 5))
        self.add_buttons.append(add_cv)
        for kind, label in ((RAW, "Add raw text"), (INFO, "Add JSON")):
            button = ttk.Menubutton(sources, text=label)
            menu = tk.Menu(button, tearoff=False)
            menu.add_command(label="Choose files…", command=lambda k=kind: self.choose_files(k))
            menu.add_command(label="Paste…", command=lambda k=kind: self.paste(k))
            button.configure(menu=menu)
            button.pack(side="left", padx=(0, 5))
            self.add_buttons.append(button)
        saved = ttk.Menubutton(sources, text="Add from Excel")
        menu = tk.Menu(saved, tearoff=False)
        for path in (RAW_FILE, INFO_FILE, LEGACY_FILE):
            menu.add_command(label=path.name, command=lambda p=path: self.choose_saved(p))
        saved.configure(menu=menu)
        saved.pack(side="left", padx=(0, 5))
        self.add_buttons.append(saved)
        self.remove = ttk.Button(sources, text="Remove selected", command=self.remove_selected)
        self.remove.pack(side="right")

        actions = ttk.Frame(frame)
        actions.pack(fill="x", pady=8)
        self.actions = {}
        for goal, label in ((RAW, "Get raw text"), (INFO, "Extract information"), (RANK, "Rank CVs")):
            button = ttk.Button(actions, text=label, command=lambda g=goal: self.start(g))
            button.pack(side="left", padx=(0, 5))
            self.actions[goal] = button

        panels = ttk.Panedwindow(frame, orient="vertical")
        panels.pack(fill="both", expand=True)
        top = ttk.Frame(panels)
        panels.add(top, weight=1)
        columns = ("Rank", "File name", "Available", "Education /10", "Experience /10", "Skills /10", "Overall /10")
        self.table = ttk.Treeview(top, columns=columns, show="headings", height=7, selectmode="extended")
        for column, width in zip(columns, (45, 260, 100, 100, 100, 90, 90), strict=True):
            self.table.heading(column, text=column)
            self.table.column(column, width=width, anchor="w" if column == "File name" else "center")
        scroll = ttk.Scrollbar(top, orient="vertical", command=self.table.yview)
        self.table.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.table.pack(fill="both", expand=True)
        self.table.bind("<<TreeviewSelect>>", self.show_selection)
        self.details = ScrolledText(panels, height=12, wrap="word", state="disabled")
        panels.add(self.details, weight=2)
        self.status = tk.StringVar(value="Add CV files, raw text, or extracted JSON to begin.")
        ttk.Label(frame, textvariable=self.status).pack(anchor="w", pady=(6, 0))
        self.controls()

    def controls(self):
        ready = bool(self.batch.cvs) and not self.busy
        can_read = ready and all(cv.raw_text is not None or cv.upload is not None for cv in self.batch.cvs)
        has_job = bool(self.description.get("1.0", "end-1c").strip())
        for goal, enabled in ((RAW, can_read), (INFO, ready), (RANK, ready and has_job)):
            self.actions[goal].configure(state="normal" if enabled else "disabled")
        self.remove.configure(state="normal" if ready and self.table.selection() else "disabled")
        for button in self.add_buttons:
            button.configure(state="disabled" if self.busy else "normal")
        self.description.configure(state="disabled" if self.busy else "normal")

    def description_changed(self, _event):
        if self.description.edit_modified():
            self.description.edit_modified(False)
            self.controls()

    def show_text(self, text):
        self.details.configure(state="normal")
        self.details.delete("1.0", "end")
        self.details.insert("1.0", text)
        self.details.configure(state="disabled")

    def display(self, rows, report=None, view=None):
        self.rows, self.report, self.view = rows, report, view
        self.table.delete(*self.table.get_children())
        for index, (cv, item) in enumerate(rows):
            available = INFO if cv.information is not None else RAW if cv.raw_text is not None else "CV file"
            scores = [f"{item[key]:.2f}" for key in SCORE_FIELDS] if item else [""] * len(SCORE_FIELDS)
            values = (item["rank"] if item else "", cv.name, available, *scores)
            self.table.insert("", "end", iid=str(index), values=values)
        if rows:
            self.table.selection_set("0")
        self.show_selection()

    def show_selection(self, _event=None):
        self.controls()
        selected = self.table.selection()
        if not selected:
            self.show_text("")
            return
        cv, item = self.rows[int(selected[0])]
        parts = []
        if item:
            parts.append(ranking_notes(self.report, item))
        if cv.information is not None and self.view != RAW:
            parts.append("Extracted JSON\n" + json.dumps(cv.information, ensure_ascii=False, indent=2))
        if cv.raw_text is not None and self.view != INFO:
            parts.append("Raw text\n" + cv.raw_text)
        self.show_text("\n\n".join(parts) or f"{cv.name} is ready to parse.")

    def update_queue(self, additions=()):
        keys = {cv.key for cv in self.batch.cvs}
        for cv in additions:
            if cv.key not in keys:
                self.batch.cvs.append(cv)
                keys.add(cv.key)
        self.display([(cv, None) for cv in self.batch.cvs])
        self.status.set(f"{len(self.batch.cvs)} CV(s) in the queue.")

    def choose_files(self, kind):
        types = {"CV": CV_TYPES, RAW: [("UTF-8 text files", "*.txt")], INFO: [("JSON files", "*.json")]}
        names = filedialog.askopenfilenames(parent=self.window, filetypes=types[kind])
        additions, errors = [], []
        for name in names:
            path = Path(name)
            try:
                if kind == "CV":
                    additions.append(QueuedCV(path, path.name, upload=path))
                else:
                    with path.open(encoding="utf-8-sig", newline="") as stream:
                        if kind == RAW:
                            additions.append(raw_input(path, path.name, stream.read()))
                        else:
                            additions.extend(json_inputs(path, path.name, json.load(stream)))
            except (OSError, ValueError) as error:
                errors.append(f"{path.name}: {error}")
        if additions:
            self.update_queue(additions)
        if errors:
            messagebox.showerror("Could not add some inputs", "\n".join(errors), parent=self.window)

    def paste(self, kind):
        dialog = tk.Toplevel(self.window)
        dialog.title("Paste raw text" if kind == RAW else "Paste extracted JSON")
        dialog.transient(self.window)
        label = "CV filename" if kind == RAW else "CV filename (used for a single bare CV object)"
        ttk.Label(dialog, text=label).pack(anchor="w", padx=8, pady=(8, 0))
        name = ttk.Entry(dialog, width=62)
        name.pack(fill="x", padx=8, pady=4)
        body = ScrolledText(dialog, width=72, height=16, wrap="word")
        body.pack(fill="both", expand=True, padx=8)

        def accept():
            text = body.get("1.0", "end-1c")
            try:
                if kind == RAW:
                    items = [raw_input(object(), name.get(), text)]
                else:
                    items = json_inputs(object(), name.get(), json.loads(text))
            except ValueError as error:
                messagebox.showerror("Invalid input", str(error), parent=dialog)
                return
            self.update_queue(items)
            dialog.destroy()

        ttk.Button(dialog, text="Add to queue", command=accept).pack(pady=8)
        name.focus_set()
        dialog.grab_set()

    def choose_saved(self, path):
        try:
            records = read_saved(path)
        except Exception as error:
            messagebox.showerror(f"Could not read {path.name}", str(error), parent=self.window)
            return
        if not records:
            self.status.set(f"No saved CVs found in {path.name}.")
            return
        dialog = tk.Toplevel(self.window)
        dialog.title(f"Select CVs from {path.name}")
        dialog.transient(self.window)
        choices = tk.Listbox(dialog, selectmode="extended", width=70, height=12, exportselection=False)
        scrollbar = ttk.Scrollbar(dialog, orient="vertical", command=choices.yview)
        choices.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        choices.pack(fill="both", expand=True, padx=8, pady=6)
        for row, record in records:
            stage = INFO if "extracted_data" in record else RAW
            choices.insert("end", f"{record['file_name']}   (row {row}, {stage})")

        def accept(_event=None):
            items = []
            try:
                for index in choices.curselection():
                    row, record = records[index]
                    key = path, row
                    if "extracted_data" in record:
                        cv = SavedCV.model_validate(record)
                        items.append(QueuedCV(key, cv.file_name, raw_text=record.get("raw_text") or None,
                                              information=cv.extracted_data.model_dump()))
                    else:
                        items.append(raw_input(key, record["file_name"], record["raw_text"]))
            except ValueError as error:
                messagebox.showerror("Invalid saved CV", str(error), parent=dialog)
                return
            if items:
                self.update_queue(items)
                dialog.destroy()

        ttk.Button(dialog, text="Add selected", command=accept).pack(pady=(0, 6))
        choices.bind("<Double-Button-1>", accept)
        dialog.grab_set()

    def remove_selected(self):
        selected = {self.rows[int(index)][0] for index in self.table.selection()}
        self.batch.cvs[:] = [cv for cv in self.batch.cvs if cv not in selected]
        self.update_queue()

    def start(self, goal):
        if self.busy or self.actions[goal].instate(["disabled"]):
            return
        self.busy = True
        self.updates = SimpleQueue()
        self.controls()
        self.status.set("Processing...")
        job = self.worker.submit(self.batch.run, goal, self.description.get("1.0", "end-1c"), self.updates.put)
        self.finish(job, goal)

    def finish(self, job, goal):
        while True:
            try:
                self.status.set(self.updates.get_nowait())
            except Empty:
                break
        if not job.done():
            self.window.after(100, self.finish, job, goal)
            return
        self.busy = False
        try:
            rows, report = job.result()
        except Exception as error:
            self.status.set("Batch pending. Fix the error or remove the file, then retry.")
            self.show_text("Start the local FastAPI service and retry." if isinstance(error, httpx.ConnectError)
                           else str(error))
        else:
            self.display(rows, report, goal)
            self.status.set(f"{goal} ready for {len(rows)} CV(s).")
        self.controls()


def main():
    window = tk.Tk()
    tester = ScreeningWindow(window)
    try:
        window.mainloop()
    finally:
        tester.worker.shutdown(wait=False, cancel_futures=True)


if __name__ == "__main__":
    main()
