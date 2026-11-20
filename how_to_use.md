# Read raw text from CVs

Use **64-bit Python 3.12**. Open PowerShell in this project folder.

```powershell
& "$env:USERPROFILE\AppData\Local\Programs\Python\Python312\python.exe" -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe install.py
```

The root requirements install the service and tester together. For the service alone, use `app\requirements.txt` in the pip install command.

With the virtual environment active, `python install.py` checks the three PaddleOCR models in `app/models/OCR/`. It downloads only missing or damaged files. After setup, CV processing runs offline on the CPU.

Start the API in the first terminal.

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Upload a Word file (`.doc`, `.docx`), PDF, or image (JPEG, PNG, TIFF, BMP, WebP) to `POST /cv/raw` in the multipart field `file`. The response contains `file_name` and `data` (raw text). Uploads support up to 32 MiB per file and 50 megapixels per image frame.

Images go through OCR. For PDFs, pdfplumber reads each page first. A page with visible content and no extractable text is rendered and sent to OCR. The response keeps the original page order.

Upload a Word CV as usual, even if the whole CV is a pasted scan. In `.docx`, python-docx reads the typed text and locates embedded pictures, including pictures in tables, headers and footers. In Word 97–2003 `.doc`, Antiword reads the typed text and olefile opens the streams that hold embedded pictures. Git for Windows supplies Antiword on this computer. The service sends embedded raster pictures to the existing local OCR engine. Pictures linked from a website are skipped.

OCR text appears at the picture's position when available. For older `.doc` files, picture text that Antiword cannot position is appended to the response.

Start the optional Tkinter tester in a second terminal in the same folder.

```powershell
.\.venv\Scripts\python.exe test_input.py
```

Choose **Add CVs**, then **Process**. The tester displays the response and uses `workbook.py` beside it to append the filename and text to `output.xlsx` in the project folder.
