# CV extraction and ranking

Use the desktop tester to rank CVs against a job description and save the scores to Excel. Run these PowerShell commands from the project folder.

```powershell
Set-Location -LiteralPath "$env:USERPROFILE\Desktop\CV screening"
```

## One-time setup

Use **64-bit Python 3.12**. Install Ollama for Windows, then open a new PowerShell window so the `ollama` command is available. [Ollama for Windows](https://ollama.com/download/windows)

```powershell
& "$env:USERPROFILE\AppData\Local\Programs\Python\Python312\python.exe" -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe install.py
```

The root `requirements.txt` installs the service and tester together. For the service alone, use `app\requirements.txt` in the pip install command. To activate the environment in PowerShell, run `.\.venv\Scripts\Activate.ps1`.

`install.py` checks the three OCR models in `app/models/OCR/` and the shared `gemma4:e4b` model in `app/models/extractor model/`. It downloads missing files and reuses installed models. After setup, extraction and ranking run offline on the CPU.

## Start the app

In the first PowerShell terminal, start FastAPI and leave it running.

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In a second PowerShell terminal in the same folder, start the tester.

```powershell
.\.venv\Scripts\python.exe test_input.py
```

If an older API is already running and the tester reports that `/cv/rank` is unavailable, stop the server with Ctrl+C and restart it using the command above.

## Rank CVs in the tester

1. Paste the posting into **Job description**. Include at least one education, experience, or skills requirement.
2. Use **Add CVs** as often as needed for new files. To include entries from `output.xlsx`, choose **Add saved CVs**, select the CVs, and click **Add selected**. You can mix both sources.
3. Use **Remove selected** to adjust the queue, then click **Process & rank**. The tester extracts new files and sends the whole batch to the ranking endpoint.
4. Select a result to see the raw text, extracted JSON, job weights, and the CV fields supporting each match. A required item marked **review** has partial or missing evidence.

For extraction alone, leave the job description blank, add new files, and click **Extract only**. If an upload fails, successful extractions stay saved. Fix or remove the failed file, then retry. To rank the same CVs against another job, use **Add saved CVs** with the new description.

Supported uploads are Word (`.doc`, `.docx`), PDF, and JPEG, PNG, TIFF, BMP, or WebP images. The upload limit is 32 MiB per file and the image limit is 50 megapixels per frame. PDF pages with readable text are parsed directly. Scanned pages and embedded Word pictures use local OCR. Legacy `.doc` text requires Antiword on `PATH` or in the Git for Windows installation. OCR text appears at the picture's position when available. In older `.doc` files, any picture text that Antiword cannot place is appended.

## Find the Excel results

Both workbooks are created beside `test_input.py`. Later runs append to them.

| Workbook | Columns in order |
|---|---|
| `output.xlsx` | File name, Data, Extracted JSON |
| `ranking.xlsx` | Job description, File name, CV JSON, Education score, Experience score, Skills score, Overall score |

Each completed ranking adds one row per CV, highest overall score first. The job description appears only on the first row of that batch. Ties keep their submission order. Long values in `ranking.xlsx` link to the **Long text** sheet. In `output.xlsx`, oversized raw text or JSON continues on subsequent rows. The saved-CV picker reassembles those pieces.

An older two-column `output.xlsx` gains the JSON column when a new extraction is saved. Upload the original file to rank an older entry that has only raw text. If Excel blocks a save, close the workbook and retry in the same tester window. Keeping the same job description and queue lets the tester reuse completed extractions and any ranking waiting to be saved.

## Read the scores

Gemma matches every CV against the same job checklist. Python gives required items two points and preferred items one. Supported matches earn full credit, partial matches earn half, and missing evidence earns zero.

| Posting | Education | Experience | Skills |
|---|---:|---:|---:|
| Standard | 10% | 50% | 40% |
| Explicitly entry-level, internship, new-graduate, or no prior experience required | 10% | 30% | 60% |

Each category score is `10 × earned points ÷ possible points`. The overall score is the weighted average of the category scores. A category with no requirements shows 0 and has zero weight. The other weights scale to 100%. For example, if a posting only requires Python and prefers SQL, a CV documenting Python alone earns 2 of 3 points. Its skills and overall scores are both **6.67/10**.

## Call the API directly

Use `http://127.0.0.1:8000` as the base URL. The API returns JSON. The tester writes the Excel reports.

| Endpoint | Input | Returns |
|---|---|---|
| `GET /health` | No body | `{"status":"ok"}` |
| `POST /cv/raw` | One multipart upload in the `file` field | `file_name`, raw text in `data`, and the structured CV in `extracted_data` |
| `POST /cv/rank` | A JSON object with `job_description` and a nonempty `cvs` list. Each entry supplies `file_name` and `extracted_data`. | `job_description`, `weights`, `requirements`, and ordered `ranked_cvs` |

For a single extraction, replace `sample.pdf` with your file.

```powershell
curl.exe -f -F "file=@sample.pdf" http://127.0.0.1:8000/cv/raw
```

`extracted_data` includes contact details, summary, skills, experience, and education. Gemma keeps the candidate's written summary. When it is missing, Gemma summarizes stated professional or educational facts, or reports that none were available.

This Python example ranks two files. Replace the filenames with your own. For previously extracted CVs, send the filename and extracted JSON directly to `/cv/rank`. The endpoint accepts `extracted_data` as an object or a JSON string.

```python
from pathlib import Path

import httpx

paths = [Path("candidate-a.pdf"), Path("candidate-b.docx")]
job = "Python is required. SQL is preferred."
timeout = httpx.Timeout(30, connect=5, read=None)
with httpx.Client(base_url="http://127.0.0.1:8000", timeout=timeout, trust_env=False) as api:
    cvs = []
    for path in paths:
        with path.open("rb") as file:
            response = api.post("/cv/raw", files={"file": (path.name, file)})
        response.raise_for_status()
        cv = response.json()
        cvs.append({"file_name": cv["file_name"], "extracted_data": cv["extracted_data"]})

    response = api.post("/cv/rank", json={"job_description": job, "cvs": cvs})
    response.raise_for_status()
    for cv in response.json()["ranked_cvs"]:
        print(cv["file_name"], cv["overall_score"])
```

Each ranked CV includes `file_name`, `extracted_data`, `education_score`, `experience_score`, `skills_score`, `overall_score`, `matches`, and `required_to_review`. Evidence points to fields such as `skills[0]`. Review IDs identify requirements with partial or missing evidence among the required items.

## Extract from a text file

To print the structured CV directly from a UTF-8 text file, run the standalone extractor.

```powershell
.\.venv\Scripts\python.exe -m app.extraction .\cv.txt
```
