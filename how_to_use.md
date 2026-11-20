# CV parsing and information extraction

Use **64-bit Python 3.12**. For Gemma, install the Ollama application once and open a new PowerShell window in this project folder. [Ollama for Windows](https://ollama.com/download/windows)

```powershell
& "$env:USERPROFILE\AppData\Local\Programs\Python\Python312\python.exe" -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe install.py
```

The root requirements install the service and tester together. For the service alone, use `app\requirements.txt` in the pip install command.

With the virtual environment active, `python install.py` checks the three OCR models in `app/models/OCR/` and the Ollama model `gemma4:e4b` in `app/models/extractor model/`. The installer downloads missing models and reuses them on later runs. After setup, CV processing runs offline on the CPU.

## Run the API and desktop tester

Start the API in the first terminal.

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Upload one Word file (`.doc`, `.docx`), PDF, or image (JPEG, PNG, TIFF, BMP, WebP) to `POST /cv/raw` in the multipart field `file`. Uploads support up to 32 MiB per file and 50 megapixels per image frame. To send `sample.pdf` from the current folder, run this in a second terminal.

```powershell
curl.exe -F "file=@sample.pdf" http://127.0.0.1:8000/cv/raw
```

The response contains `file_name`, `data` (the original raw text), and `extracted_data` (a JSON object). Gemma fills every candidate field, including email, phone, LinkedIn and GitHub. Missing values are `null` or `[]`.

Inside the service, `main.py` passes the upload to `cv_parser.py`, then sends the filename and raw text to `information_extraction.py`. That module calls the local Gemma extractor. If extraction fails, the API returns an error and the tester keeps the file available for retry.

Images go through OCR. For PDFs, pdfplumber reads each page first. A page with visible content and no extractable text is rendered and sent to OCR. The response keeps the original page order.

Upload a Word CV as usual, even if the whole CV is a pasted scan. In `.docx`, python-docx reads the typed text and locates embedded pictures, including pictures in tables, headers and footers. In Word 97–2003 `.doc`, Antiword reads the typed text and olefile opens the streams that hold embedded pictures. Git for Windows supplies Antiword on this computer. The service sends embedded raster pictures to the existing local OCR engine. Pictures linked from a website are skipped.

OCR text appears at the picture's position when available. For older `.doc` files, picture text that Antiword cannot position is appended to the response.

Start the optional Tkinter tester in a second terminal in the same folder.

```powershell
.\.venv\Scripts\python.exe test_input.py
```

Choose **Add CVs**, then **Process**. The tester displays the raw text and structured JSON and appends each result to `output.xlsx` under **File name**, **Data** and **Extracted JSON**. An existing two-column workbook gains the JSON column on its next successful save. Earlier rows retain their data and have a blank JSON cell. Oversized text or JSON continues on the following rows with the same filename.

## Test Gemma with a text file

Save one CV’s raw text as a UTF-8 file named `cv.txt`, then run the extractor directly to print the same structured object.

```powershell
.\.venv\Scripts\python.exe -m app.extraction .\cv.txt
```
