from hashlib import file_digest
from pathlib import Path

MODEL_DIR = Path(__file__).resolve().parents[2] / "models" / "OCR"
DETECTOR = "PP-OCRv6_small_det"
RECOGNIZER = "PP-OCRv6_small_rec"
ORIENTATION = "PP-LCNet_x1_0_doc_ori"

# Official model revisions and the SHA-256 of each file needed for CPU inference.
MODELS = {
    DETECTOR: ("106c97591b235f607453300d9fc8c1cad1b25488", {
        "inference.json": "89240f689a4a77aad75ef55a8df0a15c8e1d4980a327d17e58f24bbadde5aeab",
        "inference.pdiparams": "5043d4ccc8d63402ccea8feefcee4db57077431a873e78d2191836a178a492da",
        "inference.yml": "193f435274bf9f0b5f71a929bbfbcf148282df7e633b34e7c373e8f44741b516",
    }),
    RECOGNIZER: ("bd619643acac4b9650c040234da8d944476ee3f1", {
        "inference.json": "f0bf53c853937a917affdd74467472167727f8ab0f0f7bded01c4a16c27e46e6",
        "inference.pdiparams": "406e1e689c9a7fbb04178007a3fe10cf852afe7bf8bb3bc6dbb9d532b13bd907",
        "inference.yml": "ab078671bb49f06228eadccd34f1bb501e157f7a047095ffb943ba81512c77d1",
    }),
    ORIENTATION: ("d3b95a6dff5fe8a94f2748e12b61cb26818a0df8", {
        "inference.json": "3580978602f309c3554508dd85d4fe09b73a7e0d80d7f9e63258f5b72c390c69",
        "inference.pdiparams": "e8d6e7c5d264507e40e58a655779059d616b20d7441ea22047d829eb3931989c",
        "inference.yml": "9e195eb729a8173588cd0e8a852c8b373aa606e79e77b4ac7d8346f5426caf26",
    }),
}


def verified(path: Path, expected_hash: str) -> bool:
    if not path.is_file():
        return False
    with path.open("rb") as source:
        return file_digest(source, "sha256").hexdigest() == expected_hash
