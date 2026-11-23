import json
from contextlib import closing, contextmanager
from itertools import chain, zip_longest
from pathlib import Path
from tempfile import TemporaryDirectory

from filelock import FileLock, Timeout
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font
from openpyxl.worksheet.hyperlink import Hyperlink

OUTPUT_FILE = Path(__file__).resolve().parent / "output.xlsx"
RANKING_FILE = OUTPUT_FILE.with_name("ranking.xlsx")
HEADERS = ("File name", "Data", "Extracted JSON")
RANK_HEADERS = (
    "Job description", "File name", "CV JSON", "Education score",
    "Experience score", "Skills score", "Overall score",
)
SCORE_FIELDS = ("education_score", "experience_score", "skills_score", "overall_score")

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


@contextmanager
def _edit_book(path):
    # Hold the lock across both reading and replacing the file so concurrent testers can append safely.
    try:
        with FileLock(str(path) + ".lock", timeout=5):
            book = load_workbook(path, rich_text=True) if path.exists() else Workbook()
            with closing(book):
                yield book
                with TemporaryDirectory(dir=path.parent) as folder:
                    saved = Path(folder) / path.name
                    book.save(saved)
                    saved.replace(path)
    except (PermissionError, Timeout) as error:
        raise OSError(f"Close {path.name} and retry the save.") from error


def _text_cell(sheet, row, column, text):
    cell = sheet.cell(row, column, text)
    cell.data_type = "s"  # A leading equals sign in a CV or job posting is literal text.
    cell.alignment = Alignment(wrap_text=True, vertical="top")
    return cell


def append_cv(file_name: str, text: str, path: Path = OUTPUT_FILE, *, extracted_json: str = "") -> None:
    with _edit_book(path) as book:
        sheet = book["CV data"] if "CV data" in book.sheetnames else book.active
        json_column = _json_column(sheet)
        raw_parts = _cell_parts(text.translate(_XML_ESCAPES))
        json_parts = _cell_parts(extracted_json.translate(_XML_ESCAPES))
        file_name = file_name.translate(_XML_ESCAPES)
        for row, (raw, details) in enumerate(zip_longest(raw_parts, json_parts), sheet.max_row + 1):
            _text_cell(sheet, row, 1, file_name)
            if raw is not None:
                _text_cell(sheet, row, 2, raw)
            if details is not None:
                _text_cell(sheet, row, json_column, details)


def read_saved_cvs(path: Path = OUTPUT_FILE):
    if not path.exists():
        return []
    with closing(load_workbook(path, read_only=True)) as book:
        sheet = book["CV data"] if "CV data" in book.sheetnames else book.active
        rows = iter(sheet.values)
        headers = [str(value).casefold() for value in next(rows, ())]
        if headers[:2] != ["file name", "data"] or "extracted json" not in headers:
            return []
        json_column = headers.index("extracted json")
        saved, parts, raw_parts = [], [], []
        start_row, active_name = 0, ""
        for row_number, row in enumerate(rows, 2):
            name, raw, chunk = row[0], str(row[1] or ""), row[json_column]
            if not chunk:
                # Raw text can continue after the last JSON piece for this CV.
                if saved and name == saved[-1][1] and not parts:
                    saved[-1][2].append(raw)
                continue
            if not parts:
                start_row, active_name = row_number, name
            if name != active_name or not isinstance(chunk, str):
                raise ValueError(f"Invalid CV JSON in {path.name} at row {start_row}.")
            parts.append(chunk)
            raw_parts.append(raw)
            if not chunk.rstrip().endswith("}"):
                continue
            try:
                fields = json.loads("".join(parts))
            except json.JSONDecodeError:
                continue  # A nested object may end exactly at a cell boundary.
            if not isinstance(fields, dict) or not isinstance(active_name, str):
                raise ValueError(f"Invalid saved CV in {path.name} at row {start_row}.")
            saved.append((start_row, name, raw_parts, fields))
            parts, raw_parts = [], []
        if parts:
            raise ValueError(f"Incomplete CV JSON in {path.name} at row {start_row}.")
        return [(row, {"file_name": name, "data": "".join(raw), "extracted_data": fields})
                for row, name, raw, fields in saved]


def _ranking_text(sheet, row, column, text):
    parts = iter(_cell_parts(text.translate(_XML_ESCAPES)))
    first, second = next(parts), next(parts, None)
    if second is None:
        _text_cell(sheet, row, column, first)
        return

    # Keep one ranking row per person, even when the full JSON or job description exceeds Excel's cell limit.
    book = sheet.parent
    if "Long text" in book.sheetnames:
        detail = book["Long text"]
    else:
        detail = book.create_sheet("Long text")
        detail.append(("Ranking row", "Field", "Part", "Text"))
        detail.column_dimensions["D"].width = 90
    start = detail.max_row + 1
    label = RANK_HEADERS[column - 1]
    for part, value in enumerate(chain((first, second), parts), 1):
        detail.append((row, label, part))
        _text_cell(detail, start + part - 1, 4, value)
    cell = _text_cell(sheet, row, column, f"Full {label} on the Long text sheet")
    cell.hyperlink = Hyperlink(ref=cell.coordinate, location=f"'Long text'!D{start}")


def append_ranking(job_description: str, ranked_cvs: list[dict], path: Path = RANKING_FILE) -> None:
    if not ranked_cvs:
        raise ValueError("There are no ranked CVs to save.")
    with _edit_book(path) as book:
        sheet = book["Ranking"] if "Ranking" in book.sheetnames else book.active
        if sheet.max_row == 1 and all(cell.value is None for cell in sheet[1]):
            sheet.title = "Ranking"
            for column, (name, width) in enumerate(zip(RANK_HEADERS, (50, 32, 64, 18, 18, 16, 16)), 1):
                cell = sheet.cell(1, column, name)
                cell.font = Font(bold=True)
                sheet.column_dimensions[cell.column_letter].width = width
            sheet.freeze_panes = "A2"
        elif tuple(sheet.cell(1, i).value for i in range(1, 8)) != RANK_HEADERS:
            raise ValueError(f"The columns in {path.name} do not match the ranking report.")

        first_row = sheet.max_row + 1
        _ranking_text(sheet, first_row, 1, job_description)
        for row, cv in enumerate(ranked_cvs, first_row):
            _ranking_text(sheet, row, 2, cv["file_name"])
            details = json.dumps(cv["extracted_data"], ensure_ascii=False, separators=(",", ":"))
            _ranking_text(sheet, row, 3, details)
            for column, key in enumerate(SCORE_FIELDS, 4):
                sheet.cell(row, column, cv[key]).number_format = "0.00"
            sheet.row_dimensions[row].height = 34
