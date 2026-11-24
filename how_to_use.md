# CV extraction and ranking

Use the desktop tester to get raw text from a CV, extract structured information as JSON, or rank CVs against a job description. The tester saves each stage’s results to Excel.

On Windows, open the project folder in VS Code with **File > Open Folder**. Open **Terminal > New Terminal**, then use the dropdown next to **+** in the terminal panel to open a **Command Prompt** terminal. [VS Code terminal guide](https://code.visualstudio.com/docs/terminal/basics)

Run the commands from the folder containing `test_input.py`. 

## One-time setup

Use **64-bit Python 3.12**. Install Ollama for Windows, then restart VS Code and open a new Command Prompt terminal so the `ollama` command is available. [Ollama for Windows](https://ollama.com/download/windows)

```bat
"%LOCALAPPDATA%\Programs\Python\Python312\python.exe" -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe install.py
```

The root `requirements.txt` installs the service and tester together. For the service alone, use `app\requirements.txt` in the pip install command. The commands below use the virtual environment’s interpreter directly. To activate it in Command Prompt, run `.\.venv\Scripts\activate.bat`.

`install.py` checks the three OCR models in `app/models/OCR/` and the shared `gemma4:e4b` model in `app/models/extractor model/`. It downloads missing files and reuses installed models. After setup, extraction and ranking run offline on the CPU.

## Start the app

If the previous version is running, stop its server with `Ctrl+C` and close its tester window before starting the updated files.

In the first **Command Prompt** terminal in VS Code, start FastAPI and leave it running.

```bat
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open a second **Command Prompt** terminal from the same dropdown. In the same project folder, start the tester.

```bat
.\.venv\Scripts\python.exe test_input.py
```

## Parse, extract, or rank CVs in the tester

Add one or more entries to the queue. You can mix CV files, raw text, and extracted JSON in a single ranking batch.

| What you have | How to add it |
|---|---|
| CV documents or images | Click **Add CV files…** and select one or more files. |
| Existing raw text | Use **Add raw text > Choose files…** for UTF-8 `.txt` files, or **Add raw text > Paste…** to enter a CV filename and its text. A text-file import uses the `.txt` filename. |
| Existing extracted JSON | Use **Add JSON > Choose files…** for one or more `.json` files, or **Add JSON > Paste…**. A single `/cv/extract` response already contains the filename. For a bare CV object, the tester uses the JSON filename on import or the CV filename you enter when pasting. |
| Saved Excel entries | Click **Add from Excel**, choose `raw data.xlsx`, `information.xlsx`, or the older `output.xlsx`, select the CVs, and click **Add selected**. |

For multiple CVs in one JSON file or paste, use a list of extraction responses or an object with a `cvs` list. Each entry must contain its own `file_name` and `extracted_data`.

Use **Remove selected** to adjust the queue, then click the action you want. For **Rank CVs**, paste the posting into **Job description** first. Include at least one education, experience, or skills requirement. You can leave the description blank for the other two actions.

| Starting input | Get raw text | Extract information | Rank CVs |
|---|---|---|---|
| CV file | Parse | Parse → extract | Parse → extract → rank |
| Existing raw text | Display the supplied text | Extract | Extract → rank |
| Existing extracted JSON | — | Display the supplied JSON | Rank |

**Get raw text** is available when every queued entry has a CV file or raw text. The queue stays in place after each run. For example, you can inspect a CV’s raw text, click **Extract information** on the same queue, then click **Rank CVs** after entering a posting. To rank the same CVs against another job, edit the description and click **Rank CVs** again.

Select a ranked result to see the extracted JSON, job weights, the CV fields supporting each match, and raw text when available. A required item marked **review** has partial or missing evidence. If a file fails, successful stages stay saved. Fix or remove the failed file, then retry.

Supported uploads are Word (`.doc`, `.docx`), PDF, and JPEG, PNG, TIFF, BMP, or WebP images. The upload limit is 32 MiB per file and the image limit is 50 megapixels per frame. PDF pages with readable text are parsed directly. Scanned pages and embedded Word pictures use local OCR. Legacy `.doc` text requires Antiword on `PATH` or in the Git for Windows installation. OCR text appears at the picture's position when available. In older `.doc` files, any picture text that Antiword cannot place is appended.

## Find the Excel results

Each workbook is created beside `test_input.py` the first time the tester saves that stage. Later runs append new results.

| Workbook | Columns in order |
|---|---|
| `raw data.xlsx` | File name, Raw text |
| `information.xlsx` | File name, Information |
| `ranking.xlsx` | Job description, File name, CV JSON, Education score, Experience score, Skills score, Overall score, Rank |

The **Information** column holds the extracted CV as JSON text. Ranking a new CV file writes to all three workbooks. Ranking supplied raw text writes to `information.xlsx` and `ranking.xlsx`. Ranking supplied JSON writes only to `ranking.xlsx`. If a CV is already in the queue, the tester reuses its completed stages.

Each completed ranking adds one row per CV, highest overall score first. Rank 1 is the best fit. The job description appears only on the first row of that batch. Ties keep their submission order. Long values in `ranking.xlsx` link to the **Long text** sheet. When the tester next saves to an older ranking report, it adds the **Rank** column and numbers the CVs within each existing batch.

In `raw data.xlsx` and `information.xlsx`, oversized text or JSON continues on subsequent rows with a blank filename. **Add from Excel** reassembles those pieces. In a legacy `output.xlsx`, entries with only **Data** can start at extraction, and entries with **Extracted JSON** can go straight to ranking.

If Excel blocks a save, close the workbook and retry in the same tester window. Keeping the same job description and queue lets the tester reuse completed stages and any ranking waiting to be saved.

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
| `POST /cv/raw` | One multipart upload in the `file` field | `file_name` and `raw_text` |
| `POST /cv/extract` | A JSON object with `file_name` and `raw_text` | `file_name` and the structured CV in `extracted_data` |
| `POST /cv/rank` | A JSON object with `job_description` and a nonempty `cvs` list. Each entry supplies `file_name` and `extracted_data`. | `job_description` and the ordered `ranked_cvs` list |

To parse a single file, replace `sample.pdf` with your file. The first command saves the raw response in `raw.json`. Run the second command to extract structured information from it.

```bat
curl.exe -f -F "file=@sample.pdf" -o raw.json http://127.0.0.1:8000/cv/raw
curl.exe -f -H "Content-Type: application/json" --data-binary "@raw.json" http://127.0.0.1:8000/cv/extract
```

If you already have text, you can start with the second command. Save a UTF-8 `raw.json` file containing a filename and text, for example `{"file_name":"candidate-a.pdf","raw_text":"Skills: Python and SQL."}`.

`extracted_data` includes contact details, summary, skills, experience, and education. Gemma keeps the candidate's written summary. When it is missing, Gemma summarizes stated professional or educational facts, or reports that none were available.

This Python example ranks two files. Replace the filenames with your own. To run it in VS Code, save it as `rank_example.py` in the project folder and run `.\.venv\Scripts\python.exe rank_example.py` while the API is running.

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
            parsed = api.post("/cv/raw", files={"file": (path.name, file)})
        parsed.raise_for_status()

        extracted = api.post("/cv/extract", json=parsed.json())
        extracted.raise_for_status()
        cvs.append(extracted.json())

    response = api.post("/cv/rank", json={"job_description": job, "cvs": cvs})
    response.raise_for_status()
    for cv in response.json()["ranked_cvs"]:
        print(cv["rank"], cv["file_name"], cv["overall_score"])
```

For previously extracted CVs, put the saved extraction responses directly in the `cvs` list and send the ranking request. The endpoint accepts `extracted_data` as an object or a JSON string.

Each ranked CV includes `rank`, `file_name`, `education_score`, `experience_score`, `skills_score`, and `overall_score`. To get the evidence shown by the tester, send the same request to `/cv/rank?include_details=true`. This adds job-level `weights` and `requirements`, plus `extracted_data`, `matches`, and `required_to_review` for each CV. Evidence points to fields such as `skills[0]`. Review IDs identify requirements with partial or missing evidence among the required items.

## Extract from a text file

To print the structured CV directly from a UTF-8 text file, run the standalone extractor.

```bat
.\.venv\Scripts\python.exe -m app.extraction .\cv.txt
```
