from functools import cache
from io import BytesIO
import os
from threading import Lock

import numpy as np
from PIL import Image, ImageOps, ImageSequence

from .models import DETECTOR, MODEL_DIR, MODELS, ORIENTATION, RECOGNIZER, verified

IMAGE_FORMATS = {
    "PNG": (".png",),
    "JPEG": (".jpg", ".jpeg"),
    "TIFF": (".tif", ".tiff"),
    "BMP": (".bmp",),
    "WEBP": (".webp",),
}
_engine_lock = Lock()


class OCRUnavailable(RuntimeError):
    pass


@cache
def _engine():
    try:
        for model, (_, files) in MODELS.items():
            if not all(verified(MODEL_DIR / model / name, digest) for name, digest in files.items()):
                raise OCRUnavailable(f"OCR model {model} is missing or incomplete. Run python install.py.")
    except OSError as error:
        raise OCRUnavailable("Cannot read the OCR models. Check access to app/models/OCR.") from error

    # Configure Paddle before importing it. All three predictors use explicit local paths.
    os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"
    os.environ["PADDLE_PDX_CACHE_HOME"] = str(MODEL_DIR / ".cache")
    os.environ["HF_HUB_OFFLINE"] = "1"
    try:
        from paddleocr import PaddleOCR

        return PaddleOCR(
            device="cpu", cpu_threads=2, enable_mkldnn=False,
            text_detection_model_name=DETECTOR, text_detection_model_dir=str(MODEL_DIR / DETECTOR),
            text_recognition_model_name=RECOGNIZER, text_recognition_model_dir=str(MODEL_DIR / RECOGNIZER),
            doc_orientation_classify_model_name=ORIENTATION,
            doc_orientation_classify_model_dir=str(MODEL_DIR / ORIENTATION),
            use_doc_orientation_classify=True, use_doc_unwarping=False, use_textline_orientation=False,
            text_det_limit_side_len=1600, text_det_limit_type="max",
        )
    except Exception as error:
        raise OCRUnavailable("CPU OCR could not start. Check the requirements and run python install.py.") from error


def recognize(image: Image.Image) -> str:
    """Return the lines PaddleOCR reads from one page, in reading order."""
    with _engine_lock:
        engine = _engine()
        # Paddle expects BGR pixels. White also preserves dark text in transparent PNGs.
        with image.convert("RGBA") as rgba, Image.new("RGB", image.size, "white") as rgb:
            rgb.paste(rgba, mask=rgba.getchannel("A"))
            pixels = np.asarray(rgb)[:, :, ::-1].copy()
        try:
            page = engine.predict(pixels)[0]
            return "\n".join(line.strip() for line in page["rec_texts"] if line.strip())
        except Exception as error:
            raise OCRUnavailable("The local OCR engine could not read this image.") from error


def read_image(content: bytes) -> str:
    try:
        with Image.open(BytesIO(content), formats=list(IMAGE_FORMATS)) as source:
            pages = []
            for frame in ImageSequence.Iterator(source):
                if frame.width * frame.height > 50_000_000:
                    raise ValueError("Each image page must be 50 megapixels or smaller.")
                with ImageOps.exif_transpose(frame) as upright:
                    upright.thumbnail((3200, 3200))
                    pages.append(recognize(upright))
            return "\n\n".join(filter(None, pages))
    except (Image.DecompressionBombError, OSError, SyntaxError) as error:
        raise ValueError("The image could not be decoded. Check that it opens correctly.") from error
