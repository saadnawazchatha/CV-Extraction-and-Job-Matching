import re
from pathlib import Path
from tempfile import TemporaryDirectory

from filelock import FileLock, Timeout
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment

OUTPUT_FILE = Path(__file__).resolve().parent / "output.xlsx"
HEADERS = ("File name", "Data")


def _cell_parts(text: str):
    # Continue on the next row only when the text would exceed an Excel cell.
    start = units = breaks = 0
    for index, char in enumerate(text):
        width = 2 if ord(char) > 65535 else 1
        if units + width > 32767 or (char == "\n" and breaks == 253):
            yield text[start:index]
            start, units, breaks = index, 0, 0
        units += width
        breaks += char == "\n"
    yield text[start:]


def append_cv(file_name: str, text: str, path: Path = OUTPUT_FILE) -> None:
    # Make control characters that Excel cannot store visible as text.
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff\ufffe\uffff]",
                  lambda match: f"\\u{ord(match[0]):04x}", text)
    try:
        with FileLock(str(path) + ".lock", timeout=5):
            book = load_workbook(path, rich_text=True) if path.exists() else Workbook()
            try:
                sheet = book["CV data"] if "CV data" in book.sheetnames else book.active
                if sheet.max_row == 1 and all(cell.value is None for cell in sheet[1]):
                    sheet.title = "CV data"
                    sheet["A1"], sheet["B1"] = HEADERS
                    sheet.column_dimensions["A"].width = 32
                    sheet.column_dimensions["B"].width = 90
                header = tuple(str(sheet.cell(1, n).value).casefold() for n in (1, 2))
                if header != ("file name", "data"):
                    raise ValueError("output.xlsx must have the headers 'File name' and 'Data'.")
                row = sheet.max_row + 1
                for part in _cell_parts(text):
                    for col, value in enumerate((file_name, part), 1):
                        cell = sheet.cell(row, col, value)
                        cell.data_type = "s"  # Even a leading '=' is literal CV text.
                    sheet.cell(row, 2).alignment = Alignment(wrap_text=True, vertical="top")
                    row += 1
                # Replace the old file only after the new workbook has been saved.
                with TemporaryDirectory(dir=path.parent) as folder:
                    saved = Path(folder) / "output.xlsx"
                    book.save(saved)
                    saved.replace(path)
            finally:
                book.close()
    except (PermissionError, Timeout) as error:
        raise OSError("Close output.xlsx and press Process to retry.") from error
