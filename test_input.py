import json
import tkinter as tk
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from queue import Empty, SimpleQueue
from tkinter import filedialog, ttk
from tkinter.scrolledtext import ScrolledText

import httpx

from workbook import SCORE_FIELDS, append_cv, append_ranking, read_saved_cvs


API_URL = "http://127.0.0.1:8000"
CV_TYPES = [("CV files", "*.doc *.docx *.pdf *.png *.jpg *.jpeg *.tif *.tiff *.bmp *.webp")]


@dataclass(eq=False)
class QueuedCV:
    # A path identifies an upload. The original Excel row identifies a previously saved CV.
    source: Path | int
    name: str
    result: dict | None = None
    saved: bool = False


def api_result(response):
    if response.is_error:
        try:
            detail = response.json().get("detail")
        except (ValueError, AttributeError):
            detail = None
        if isinstance(detail, list):
            detail = "\n".join(item.get("msg", "") for item in detail if isinstance(item, dict))
        if response.status_code == 404 and response.request.url.path == "/cv/rank":
            detail = "Restart the updated FastAPI service to enable /cv/rank."
        raise ValueError(detail or f"The API returned HTTP {response.status_code}.")
    response.raise_for_status()
    result = response.json()
    if not isinstance(result, dict):
        raise ValueError("The API returned an unexpected response.")
    return result


def ranked_rows(cvs, ranking):
    # The service returns results in score order. Match them to their raw text, even if names repeat.
    items = ranking.get("ranked_cvs")
    if not isinstance(items, list) or len(items) != len(cvs):
        raise ValueError("The API did not return a ranking for the complete batch.")
    by_name = defaultdict(list)
    for cv in cvs:
        by_name[cv.result["file_name"]].append(cv)
    rows = []
    for item in items:
        if not (isinstance(item, dict) and isinstance(item.get("file_name"), str)
                and isinstance(item.get("extracted_data"), dict)):
            raise ValueError("A ranked CV is missing its filename or extracted JSON.")
        if any(type(item.get(key)) not in (int, float) or not 0 <= item[key] <= 10 for key in SCORE_FIELDS):
            raise ValueError("A ranked CV is missing a valid score out of 10.")
        choices = by_name.get(item.get("file_name"), [])
        if len(choices) == 1:
            cv = choices.pop()
        else:
            cv = next((c for c in choices if c.result["extracted_data"] == item["extracted_data"]), None)
            if cv is None:
                raise ValueError("A ranked CV could not be matched to the submitted files.")
            choices.remove(cv)
        rows.append((cv, item))
    return rows


class Batch:
    def __init__(self):
        self.cvs = []
        self.ranked_for = None
        self.ranking = None
        self.rows = []

    def run(self, description, notify):
        description = description.strip()
        if not self.cvs:
            raise ValueError("Add at least one CV.")
        failures = []
        # Local CPU inference can take minutes. All HTTP and Excel work runs off the Tk thread.
        with httpx.Client(base_url=API_URL, timeout=httpx.Timeout(30, connect=5, read=None), trust_env=False) as client:
            for index, cv in enumerate(self.cvs, 1):
                if cv.saved:
                    continue
                try:
                    if cv.result is None:
                        notify(f"Extracting {index} of {len(self.cvs)}: {cv.name}")
                        with cv.source.open("rb") as source:
                            result = api_result(client.post("/cv/raw", files={"file": (cv.name, source)}))
                        if not (isinstance(result.get("file_name"), str) and isinstance(result.get("data"), str)
                                and isinstance(result.get("extracted_data"), dict)):
                            raise ValueError("The extraction response needs file_name, data, and extracted_data.")
                        cv.result = result
                    details = json.dumps(cv.result["extracted_data"], ensure_ascii=False, indent=2)
                    append_cv(cv.result["file_name"], cv.result["data"], extracted_json=details)
                    cv.saved = True
                except httpx.ConnectError:
                    raise
                except (OSError, ValueError, httpx.HTTPError) as error:
                    failures.append(f"{cv.name}: {error}")
            if failures:
                raise ValueError("\n".join(failures))
            if not description:
                return [(cv, None) for cv in self.cvs], None

            # Keep a completed ranking available if Excel locks the report, and invalidate it
            # when either the job description or the selected CVs change.
            key = description, tuple(self.cvs)
            if key != self.ranked_for:
                notify(f"Ranking {len(self.cvs)} CVs against the job description...")
                inputs = [{"file_name": cv.result["file_name"], "extracted_data": cv.result["extracted_data"]}
                          for cv in self.cvs]
                ranking = api_result(client.post("/cv/rank", json={"job_description": description, "cvs": inputs}))
                if ranking.get("job_description") != description:
                    raise ValueError("The API returned a ranking for a different job description.")
                self.rows = ranked_rows(self.cvs, ranking)
                self.ranking = ranking
                self.ranked_for = key

        notify("Saving ranking.xlsx...")
        append_ranking(description, self.ranking["ranked_cvs"])
        return self.rows, self.ranking


class ScreeningWindow:
    def __init__(self, window):
        self.window = window
        self.worker = ThreadPoolExecutor(max_workers=1)
        self.batch = Batch()
        self.rows = []
        self.ranking = None
        self.busy = False
        window.title("CV screening tester")
        window.geometry("860x650")
        frame = ttk.Frame(window, padding=10)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Job description (leave blank to extract new CVs only)").pack(anchor="w")
        self.description = ScrolledText(frame, height=4, wrap="word")
        self.description.pack(fill="x", pady=(2, 6))
        self.description.bind("<<Modified>>", self.description_changed)

        bar = ttk.Frame(frame)
        bar.pack(fill="x", pady=(0, 6))
        self.add = ttk.Button(bar, text="Add CVs", command=self.choose_files)
        self.saved = ttk.Button(bar, text="Add saved CVs", command=self.choose_saved)
        self.remove = ttk.Button(bar, text="Remove selected", command=self.remove_selected)
        self.process = ttk.Button(bar, command=self.start)
        for button in (self.add, self.saved, self.remove, self.process):
            button.pack(side="left", padx=(0, 6))

        panels = ttk.Panedwindow(frame, orient="vertical")
        panels.pack(fill="both", expand=True)
        top = ttk.Frame(panels)
        panels.add(top, weight=1)
        columns = ("File name", "Education /10", "Experience /10", "Skills /10", "Overall /10")
        self.table = ttk.Treeview(top, columns=columns, show="headings", height=6, selectmode="extended")
        for column in columns:
            self.table.heading(column, text=column)
            self.table.column(column, width=300 if column == "File name" else 105,
                              anchor="w" if column == "File name" else "center")
        scroll = ttk.Scrollbar(top, orient="vertical", command=self.table.yview)
        self.table.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.table.pack(fill="both", expand=True)
        self.table.bind("<<TreeviewSelect>>", self.show_selection)

        self.details = ScrolledText(panels, height=10, wrap="word", state="disabled")
        panels.add(self.details, weight=2)
        self.status = tk.StringVar(value="Ready")
        ttk.Label(frame, textvariable=self.status).pack(anchor="w", pady=(6, 0))
        self.controls()

    def controls(self):
        queued = bool(self.batch.cvs)
        has_job = bool(self.description.get("1.0", "end-1c").strip())
        can_process = queued and (has_job or any(isinstance(cv.source, Path) for cv in self.batch.cvs))
        self.process.configure(text="Process & rank" if has_job else "Extract only",
                               state="normal" if can_process and not self.busy else "disabled")
        self.remove.configure(state="normal" if queued and self.table.selection() and not self.busy else "disabled")
        for button in (self.add, self.saved):
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

    def display(self, rows, ranking=None):
        self.rows, self.ranking = rows, ranking
        self.table.delete(*self.table.get_children())
        for index, (cv, item) in enumerate(rows):
            scores = [f"{item[key]:.2f}" for key in SCORE_FIELDS] if item else [""] * 4
            self.table.insert("", "end", iid=str(index), values=(cv.name, *scores))
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
        if cv.result is None:
            self.show_text(f"{cv.name} is queued for extraction.")
            return
        parts = []
        if item:
            weights = self.ranking.get("weights", {})
            parts.append("Job weights\n" + ", ".join(f"{key} {value:.0%}" for key, value in weights.items()))
            requirements = {r["id"]: r for r in self.ranking.get("requirements", [])}
            review = set(item.get("required_to_review", []))
            lines = []
            for match in item.get("matches", []):
                requirement = requirements.get(match["requirement_id"], {})
                evidence = ", ".join(match["evidence"]) or "no supporting CV field"
                status = match["status"].replace("_", " ")
                if match["requirement_id"] in review:
                    status += " (review)"
                lines.append(f"{requirement.get('text', '')} [{requirement.get('priority', '')}]"
                             f"\n    {status} — {evidence}")
            if lines:
                parts.append("Requirement matches\n" + "\n".join(lines))
        parts.append("Raw text\n" + cv.result["data"])
        parts.append("Extracted JSON\n" + json.dumps(cv.result["extracted_data"], ensure_ascii=False, indent=2))
        self.show_text("\n\n".join(parts))

    def update_queue(self, additions=()):
        existing = {cv.source for cv in self.batch.cvs}
        for cv in additions:
            if cv.source not in existing:
                self.batch.cvs.append(cv)
                existing.add(cv.source)
        self.display([(cv, None) for cv in self.batch.cvs])
        self.status.set(f"{len(self.batch.cvs)} queued")

    def choose_files(self):
        names = filedialog.askopenfilenames(parent=self.window, filetypes=CV_TYPES)
        if names:
            self.update_queue(QueuedCV(Path(name), Path(name).name) for name in names)

    def choose_saved(self):
        try:
            records = read_saved_cvs()
        except Exception as error:
            self.status.set("Could not read output.xlsx")
            self.show_text(str(error))
            return
        if not records:
            self.status.set("No stored CVs with extracted JSON in output.xlsx.")
            return
        dialog = tk.Toplevel(self.window)
        dialog.title("Select CVs from output.xlsx")
        dialog.transient(self.window)
        choices = tk.Listbox(dialog, selectmode="extended", width=65, height=12, exportselection=False)
        scrollbar = ttk.Scrollbar(dialog, orient="vertical", command=choices.yview)
        choices.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        choices.pack(fill="both", expand=True, padx=8, pady=6)
        for row, result in records:
            choices.insert("end", f"{result['file_name']}  (row {row})")

        def accept(_event=None):
            selected = [records[i] for i in choices.curselection()]
            if selected:
                self.update_queue(QueuedCV(row, result["file_name"], result, True) for row, result in selected)
                dialog.destroy()

        ttk.Button(dialog, text="Add selected", command=accept).pack(pady=(0, 6))
        choices.bind("<Double-Button-1>", accept)
        dialog.grab_set()

    def remove_selected(self):
        selected = {self.rows[int(index)][0] for index in self.table.selection()}
        self.batch.cvs[:] = [cv for cv in self.batch.cvs if cv not in selected]
        self.update_queue()

    def start(self):
        if self.busy or self.process.instate(["disabled"]):
            return
        self.busy = True
        self.updates = SimpleQueue()
        self.controls()
        self.status.set("Processing...")
        job = self.worker.submit(self.batch.run, self.description.get("1.0", "end-1c"), self.updates.put)
        self.finish(job)

    def finish(self, job):
        while True:
            try:
                self.status.set(self.updates.get_nowait())
            except Empty:
                break
        if not job.done():
            self.window.after(100, self.finish, job)
            return
        self.busy = False
        try:
            rows, ranking = job.result()
        except Exception as error:
            self.status.set("Batch pending. Retry after resolving the error.")
            self.show_text("Start the local API and retry." if isinstance(error, httpx.ConnectError) else str(error))
        else:
            self.batch = Batch()
            self.display(rows, ranking)
            target = "ranking.xlsx" if ranking else "output.xlsx"
            self.status.set(f"{len(rows)} CVs processed. Results in {target}.")
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
