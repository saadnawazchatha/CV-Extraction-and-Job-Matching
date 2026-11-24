
# How to Use — CV Extraction & Job Matching

![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.13-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![Ollama](https://img.shields.io/badge/Ollama-Local_AI-black)
![VS Code](https://img.shields.io/badge/Editor-VS_Code-007ACC)

This guide explains how to install, run, and integrate the CV Extraction & Job Matching microservice.

The service provides three independently accessible features:

| Feature | Purpose |
|---------|---------|
| Parsing | Extract raw text from CV documents |
| Information Extraction | Convert raw text into structured JSON |
| CV Ranking | Score and rank CVs against a job description |

---

## 1. Prerequisites

### Python Compatibility

This project was developed and tested using **64-bit Python 3.12 on Windows**.

Based on the current project dependencies, the expected Python compatibility range is **Python 3.11–3.13 (64-bit)**.

| Python Version | Compatibility |
|----------------|---------------|
| Python 3.10 and older | ❌ Not Supported |
| Python 3.11 | ✅ Dependency Compatible — Not Yet Tested |
| Python 3.12 | ✅ Tested & Recommended |
| Python 3.13 | ✅ Dependency Compatible — Not Yet Tested |
| Python 3.14 and newer | ❌ Not Supported by Current Dependencies |

Python 3.12 is recommended for the most reliable experience.

Python compatibility is limited by the pinned versions of [NumPy](https://pypi.org/project/numpy/2.3.5/) and [PaddlePaddle](https://pypi.org/project/paddlepaddle/3.3.1/).

### Required Software

Install the following before proceeding:

- [Python](https://www.python.org/downloads/windows/) — 64-bit, preferably Python 3.12
- [Visual Studio Code](https://code.visualstudio.com/download)
- [Git for Windows](https://git-scm.com/download/win)
- [Ollama for Windows](https://ollama.com/download/windows)
- [Python Extension for VS Code](https://marketplace.visualstudio.com/items?itemName=ms-python.python)

Ensure Python, Git, and Ollama are accessible from the terminal.

Legacy `.doc` text extraction also requires Antiword, available through supported Git for Windows installations or separately on PATH.

---

## 2. Clone the Repository

Open VS Code and select **Terminal > New Terminal**.

Use the dropdown next to the terminal's `+` button to select **Command Prompt (CMD)**.

Navigate to your preferred location and run:

```bat
git clone https://github.com/saadnawazchatha/CV-Extraction-and-Job-Matching.git

cd CV-Extraction-and-Job-Matching

code .
```

This opens the cloned project in VS Code.

Run all subsequent commands from the project root, which contains `install.py`, `requirements.txt`, and `test_input.py`.

---

## 3. One-Time Installation

### Create a Virtual Environment

Check the installed Python versions:

```bat
py -0p
```

Create a virtual environment using your installed Python version.

**Python 3.12 (Recommended):**

```bat
py -3.12 -m venv .venv
```

**Alternatively, for Python 3.11:**

```bat
py -3.11 -m venv .venv
```

**Alternatively, for Python 3.13:**

```bat
py -3.13 -m venv .venv
```

Run only one of the above commands.

In VS Code, press `Ctrl + Shift + P`, select **Python: Select Interpreter**, and choose the interpreter inside `.venv`.

Verify the selected Python version:

```bat
.\.venv\Scripts\python.exe --version
```

### Install Dependencies

```bat
.\.venv\Scripts\python.exe -m pip install --upgrade pip

.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

The root `requirements.txt` installs dependencies for both the microservice and desktop tester.

If you only require the API service without the desktop tester, install:

```bat
.\.venv\Scripts\python.exe -m pip install -r app\requirements.txt
```

### Install AI and OCR Models

Verify that Ollama is installed:

```bat
ollama --version
```

Download the required models:

```bat
.\.venv\Scripts\python.exe install.py
```

The installation script automatically downloads and verifies:

| Model | Purpose |
|-------|---------|
| PaddleOCR models | Image and scanned document text extraction |
| Gemma 4 (`gemma4:e4b`) | Structured information extraction and CV ranking |

Models are stored inside `app/models/`.

An internet connection is required for initial installation. Once installed, AI and OCR processing run locally on the CPU without requiring cloud API keys.

Running `install.py` again reuses existing models and downloads missing files.

---

## 4. Running the Application

The project can be used in two ways:

- **Desktop Tester:** A graphical interface for testing the service and exporting results to Excel.
- **Standalone API:** A FastAPI microservice that can be integrated into other applications.

### Start the Microservice

Open a Command Prompt terminal in VS Code and run:

```bat
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The API is now available at:

`http://127.0.0.1:8000`

Keep this terminal running while using the service.

To verify that the server is running, open:

[http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

Expected response:

```json
{
  "status": "ok"
}
```

---

## 5. Using the Desktop Tester

With the microservice running, open a second Command Prompt terminal in VS Code.

Run:

```bat
.\.venv\Scripts\python.exe test_input.py
```

### Adding CVs

The tester accepts multiple input types:

| Option | Description |
|--------|-------------|
| Add CV files | Upload PDF, Word, or image files |
| Add raw text | Import text files or paste existing CV text |
| Add JSON | Import or paste extracted candidate information |
| Add from Excel | Reuse CV information from existing workbooks |

### Processing CVs

Select the required operation:

| Action | Result |
|--------|--------|
| Get raw text | Returns parsed CV text |
| Extract information | Returns structured candidate JSON |
| Rank CVs | Scores and ranks candidates against a job description |

Enter a job description when using **Rank CVs**. A job description is not required for parsing or information extraction.

The tester automatically performs any preceding processing stages required for the selected operation.

Previously extracted information can be reused without processing the original CV again.

### Supported File Formats

- Word documents (`.doc`, `.docx`)
- PDF documents, including scanned PDFs
- JPEG, PNG, TIFF, BMP, and WebP images
- Word documents containing embedded images

**Maximum upload size:** 32 MiB per CV.

### Excel Results

The desktop tester automatically creates the following workbooks in the project directory:

| File | Contents |
|------|----------|
| `raw data.xlsx` | CV filenames and extracted raw text |
| `information.xlsx` | CV filenames and structured JSON |
| `ranking.xlsx` | Job descriptions, candidate scores, and ranking results |

Ranking results are ordered by overall relevance score, with Rank 1 representing the highest-scoring candidate.

Close open Excel workbooks before saving additional results.

---

## 6. Using the Standalone API

The desktop tester is optional.

Any application capable of making HTTP requests can communicate directly with the microservice.

Start the server using the command in Section 4.

### Base URL

```text
http://127.0.0.1:8000
```

### Available API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/health` | Check service availability |
| POST | `/cv/raw` | Parse a CV into raw text |
| POST | `/cv/extract` | Extract structured candidate information |
| POST | `/cv/rank` | Score and rank candidates |

All endpoints return JSON responses.

The API does not generate Excel files. Excel reporting is handled separately by the desktop tester.

### Endpoint 1 — Raw Text Extraction

**POST `/cv/raw`**

Send a CV document as multipart form data using the `file` field.

Example using the VS Code terminal:

```bat
curl.exe -f -F "file=@sample.pdf" http://127.0.0.1:8000/cv/raw
```

Example response:

```json
{
  "file_name": "sample.pdf",
  "raw_text": "John Doe. Software Developer. Skills: Python, SQL."
}
```

Use this endpoint when only document parsing is required.

### Endpoint 2 — Structured Information Extraction

**POST `/cv/extract`**

Send a JSON request containing the CV filename and raw text.

Example request body:

```json
{
  "file_name": "sample.pdf",
  "raw_text": "John Doe. Software Developer. Skills: Python, SQL."
}
```

The response contains:

- `file_name` — Original CV filename.
- `extracted_data` — Structured candidate information.

The extracted information includes contact details, LinkedIn, GitHub, summary, skills, experience, and education.

Existing raw text can be submitted directly without uploading the original CV.

### Endpoint 3 — CV Ranking

**POST `/cv/rank`**

Send a JSON request containing:

- `job_description` — Requirements of the job.
- `cvs` — A nonempty list of previously extracted CV responses.

Each CV entry must contain `file_name` and `extracted_data`.

The response contains the job description and an ordered `ranked_cvs` list.

Each ranked candidate includes:

| Field | Description |
|-------|-------------|
| `rank` | Candidate's ranking position |
| `file_name` | Original CV filename |
| `education_score` | Education relevance score |
| `experience_score` | Experience relevance score |
| `skills_score` | Skills relevance score |
| `overall_score` | Overall candidate relevance score |

Scores range from **0 to 10**.

For detailed matching evidence, job requirements, and scoring weights, use:

```text
POST /cv/rank?include_details=true
```

**Note:** The ranking system is operational but remains under testing and refinement.

---

## 7. Integrating the API into Your Own Application

The microservice can be integrated into Python, JavaScript, Flutter, Java, .NET, or any other application supporting HTTP requests.

### Processing Workflow

```text
CV Document
    |
    v
POST /cv/raw
    |
    v
Raw Text
    |
    v
POST /cv/extract
    |
    v
Structured JSON
    |
    v
POST /cv/rank + Job Description
    |
    v
Ranked Candidates
```

Each stage can be accessed independently.

Applications can start at any stage if they already have the required input.

### Python Integration Example

Create a file named `api_example.py` in the project root using VS Code.

Paste the following code:

```python
from pathlib import Path

import httpx

BASE_URL = "http://127.0.0.1:8000"

cv_files = [
    Path("candidate-a.pdf"),
    Path("candidate-b.docx")
]

job_description = """
Python developer with experience in SQL
and software development.
"""

timeout = httpx.Timeout(30, connect=5, read=None)

with httpx.Client(
    base_url=BASE_URL,
    timeout=timeout,
    trust_env=False
) as client:

    extracted_cvs = []

    for path in cv_files:

        # Stage 1: Parse the CV
        with path.open("rb") as file:
            response = client.post(
                "/cv/raw",
                files={"file": (path.name, file)}
            )

        response.raise_for_status()
        raw_data = response.json()

        # Stage 2: Extract structured information
        response = client.post(
            "/cv/extract",
            json=raw_data
        )

        response.raise_for_status()
        extracted_cvs.append(response.json())

    # Stage 3: Rank candidates
    response = client.post(
        "/cv/rank",
        json={
            "job_description": job_description,
            "cvs": extracted_cvs
        }
    )

    response.raise_for_status()

    for cv in response.json()["ranked_cvs"]:
        print(
            cv["rank"],
            cv["file_name"],
            cv["overall_score"]
        )
```

Replace the example filenames and job description with your own.

With the microservice running, execute:

```bat
.\.venv\Scripts\python.exe api_example.py
```

If only parsing or information extraction is required, stop after the corresponding stage.

If structured candidate JSON is already available, submit it directly to `/cv/rank` without repeating earlier stages.

### Connecting from Another Device

To make the microservice accessible to other devices on a trusted local network, start it using:

```bat
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Other applications can communicate with the service using:

```text
http://SERVER_IP:8000
```

Replace `SERVER_IP` with the local IP address of the computer hosting the microservice.

Ensure the firewall permits the intended connections on port 8000.

The current API does not implement authentication. Do not expose it directly to the public internet.

Production deployments should include authentication, HTTPS, and appropriate access controls for candidate information.

Browser-based applications may also require CORS configuration or a backend proxy.

---

## 8. Troubleshooting

| Problem | Solution |
|---------|----------|
| Python not recognized | Install a compatible Python version and restart VS Code |
| Dependency installation fails | Verify that Python is 64-bit and within the expected 3.11–3.13 range; prefer 3.12 |
| Ollama not recognized | Install Ollama and restart VS Code |
| AI or OCR models missing | Run `install.py` again |
| Cannot connect to API | Verify that the Uvicorn server is running |
| Excel file cannot be saved | Close the workbook and retry |
| Legacy `.doc` extraction fails | Verify that Antiword is installed |
| AI processing takes time | Processing speed depends on CPU performance and document complexity |

To stop the microservice, press `Ctrl + C` in its terminal.

---

For project information and development progress, see [README.md](README.md).
