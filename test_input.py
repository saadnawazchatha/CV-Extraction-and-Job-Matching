from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, ttk
from tkinter.scrolledtext import ScrolledText

import httpx

from workbook import append_cv

API_URL = "http://127.0.0.1:8000/cv/raw"


def process_files(paths, cache):
    """Send each CV to the local API, then save the returned text."""
    failed, reports = [], []
    with httpx.Client(timeout=httpx.Timeout(300, connect=5), trust_env=False) as client:
        for path in paths:
            text = ""
            try:
                if path not in cache:
                    with path.open("rb") as source:
                        response = client.post(API_URL, files={"file": (path.name, source)})
                    if response.is_error:
                        raise ValueError(response.json()["detail"])
                    result = response.json()
                    cache[path] = (result["file_name"], result["data"])
                name, text = cache[path]
                append_cv(name, text)
                del cache[path]
                reports.append(f"{name}\n{text}")
            except Exception as error:
                failed.append(path)
                message = "Start the local API and retry." if isinstance(error, httpx.RequestError) else str(error)
                reports.append(f"{path.name}\n{message}\n{text}".rstrip())
    return failed, "\n\n".join(reports)


def main():
    window = tk.Tk()
    window.title("CV text reader")
    pending, cache = [], {}
    worker = ThreadPoolExecutor(max_workers=1)

    def show(text):
        preview.configure(state="normal")
        preview.delete("1.0", "end")
        preview.insert("1.0", text)
        preview.configure(state="disabled")

    def choose():
        names = filedialog.askopenfilenames(filetypes=[
            ("CV files", "*.doc *.docx *.pdf *.png *.jpg *.jpeg *.tif *.tiff *.bmp *.webp"),
        ])
        pending.extend(Path(name) for name in names)
        if pending:
            show("\n".join(path.name for path in pending))
            status.set(f"{len(pending)} queued")
            process_button.configure(state="normal")

    def process():
        add_button.configure(state="disabled")
        process_button.configure(state="disabled")
        status.set("Reading CVs...")
        job = worker.submit(process_files, pending.copy(), cache)
        finish(job)

    def finish(job):
        if not job.done():
            window.after(100, finish, job)
            return
        try:
            retry, report = job.result()
            status.set(f"{len(pending) - len(retry)} saved, {len(retry)} pending")
            pending[:] = retry
            show(report)
        finally:
            add_button.configure(state="normal")
            process_button.configure(state="normal" if pending else "disabled")

    buttons = ttk.Frame(window, padding=8)
    buttons.pack(fill="x")
    add_button = ttk.Button(buttons, text="Add CVs", command=choose)
    add_button.pack(side="left")
    process_button = ttk.Button(buttons, text="Process", command=process, state="disabled")
    process_button.pack(side="left", padx=6)
    status = tk.StringVar(value="Ready")
    ttk.Label(buttons, textvariable=status).pack(side="right")
    preview = ScrolledText(window, wrap="word", height=20, width=72, state="disabled")
    preview.pack(fill="both", expand=True, padx=8, pady=(0, 8))
    window.mainloop()
    worker.shutdown(wait=False, cancel_futures=True)


if __name__ == "__main__":
    main()
