from itertools import chain, zip_longest
from pathlib import Path
from tempfile import TemporaryDirectory

from filelock import FileLock, Timeout
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment

OUTPUT_FILE = Path(__file__).resolve().parent / "output.xlsx"
HEADERS = ("File name", "Data", "Extracted JSON")

# Excel's XML cannot store these code points. A literal escape keeps their value visible.
_XML_ESCAPES = {
    code: f"\\u{code:04x}"
    for code in chain(range(9), (11, 12), range(14, 32), range(0xD800, 0xE000), (0xFFFE, 0xFFFF))
}


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


def _json_column(sheet) -> int:
    if sheet.max_row == 1 and all(cell.value is None for cell in sheet[1]):
        sheet.title = "CV data"
        sheet["A1"], sheet["B1"] = HEADERS[:2]
        sheet.column_dimensions["A"].width = 32
        sheet.column_dimensions["B"].width = 90
    header = tuple(str(sheet.cell(1, n).value).casefold() for n in (1, 2))
    if header != ("file name", "data"):
        raise ValueError("output.xlsx must have the headers 'File name' and 'Data'.")
    for cell in sheet[1][2:]:
        if str(cell.value).casefold() == HEADERS[2].casefold():
            return cell.column
    # This also upgrades two-column workbooks without overwriting existing rows or notes.
    cell = sheet.cell(1, sheet.max_column + 1, HEADERS[2])
    sheet.column_dimensions[cell.column_letter].width = 75
    return cell.column


def append_cv(file_name: str, text: str, path: Path = OUTPUT_FILE, *, extracted_json: str = "") -> None:
    try:
        with FileLock(str(path) + ".lock", timeout=5):
            book = load_workbook(path, rich_text=True) if path.exists() else Workbook()
            try:
                sheet = book["CV data"] if "CV data" in book.sheetnames else book.active
                json_column = _json_column(sheet)
                raw_parts = _cell_parts(text.translate(_XML_ESCAPES))
                json_parts = _cell_parts(extracted_json.translate(_XML_ESCAPES))
                file_name = file_name.translate(_XML_ESCAPES)
                for row, (raw, details) in enumerate(zip_longest(raw_parts, json_parts), sheet.max_row + 1):
                    for col, value in ((1, file_name), (2, raw), (json_column, details)):
                        if value is None:
                            continue
                        cell = sheet.cell(row, col, value)
                        cell.data_type = "s"  # Even a leading '=' is literal CV text.
                        if col != 1:
                            cell.alignment = Alignment(wrap_text=True, vertical="top")
                # Replace the old file only after the new workbook has been saved.
                with TemporaryDirectory(dir=path.parent) as folder:
                    saved = Path(folder) / "output.xlsx"
                    book.save(saved)
                    saved.replace(path)
            finally:
                book.close()
    except (PermissionError, Timeout) as error:
        raise OSError("Close output.xlsx and press Process to retry.") from error
