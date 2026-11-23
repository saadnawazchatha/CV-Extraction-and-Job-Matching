from contextlib import ExitStack
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


# Build the CPU predictor on the first image that needs it and reuse it for later uploads.
@cache
def _engine():
    try:
        for model, (_, files) in MODELS.items():
            if not all(verified(MODEL_DIR / model / name, digest) for name, digest in files.items()):
                raise OCRUnavailable(f"OCR model {model} is missing or incomplete. Run python install.py.")
    except OSError as error:
        raise OCRUnavailable("Cannot read the OCR models. Check access to app/models/OCR.") from error

    # Set offline options before importing Paddle so startup uses the models installed by install.py.
    os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"
    os.environ["PADDLE_PDX_CACHE_HOME"] = str(MODEL_DIR / ".cache")
    os.environ["HF_HUB_OFFLINE"] = "1"
    try:
        from paddleocr import PaddleOCR

        return PaddleOCR(
            device="cpu",
            cpu_threads=2,
            enable_mkldnn=False,
            text_detection_model_name=DETECTOR,
            text_detection_model_dir=str(MODEL_DIR / DETECTOR),
            text_recognition_model_name=RECOGNIZER,
            text_recognition_model_dir=str(MODEL_DIR / RECOGNIZER),
            doc_orientation_classify_model_name=ORIENTATION,
            doc_orientation_classify_model_dir=str(MODEL_DIR / ORIENTATION),
            use_doc_orientation_classify=True,
            use_doc_unwarping=False,
            use_textline_orientation=False,
            text_det_limit_side_len=1600,
            text_det_limit_type="max",
        )
    except Exception as error:
        raise OCRUnavailable("CPU OCR could not start. Check the requirements and run python install.py.") from error


def recognize(image: Image.Image) -> str:
    # Requests share a predictor, so finish one prediction before starting the next.
    with _engine_lock:
        # Blend transparency onto white so invisible pixels cannot be mistaken for text.
        with image.convert("RGBA") as rgba, Image.new("RGB", image.size, "white") as rgb:
            rgb.paste(rgba, mask=rgba.getchannel("A"))
            if all(low == high for low, high in rgb.getextrema()):
                return ""
            # Convert Pillow's RGB pixels into the contiguous BGR array the predictor expects.
            pixels = np.asarray(rgb)[:, :, ::-1].copy()
        engine = _engine()
        try:
            page = engine.predict(pixels)[0]
            return "\n".join(line.strip() for line in page["rec_texts"] if line.strip())
        except Exception as error:
            raise OCRUnavailable("The local OCR engine could not read this image.") from error


def read_image(
    content: bytes,
    *,
    formats: tuple[str, ...] = tuple(IMAGE_FORMATS),
    crop: tuple[float, float, float, float] | None = None,
) -> str:
    try:
        with Image.open(BytesIO(content), formats=formats) as source:
            pages = []
            # A TIFF may contain several CV pages. Read the frames in page order.
            for frame in ImageSequence.Iterator(source):
                if frame.width * frame.height > 50_000_000:
                    raise ValueError("Each image page must be 50 megapixels or smaller.")
                with ExitStack() as images:
                    # Apply the stored rotation before measuring Word's crop on the visible image.
                    upright = images.enter_context(ImageOps.exif_transpose(frame))
                    if crop:
                        left, top, right, bottom = (min(1, max(0, value)) for value in crop)
                        width, height = upright.size
                        box = (
                            round(width * left),
                            round(height * top),
                            round(width * (1 - right)),
                            round(height * (1 - bottom)),
                        )
                        if box[0] >= box[2] or box[1] >= box[3]:
                            continue
                        upright = images.enter_context(upright.crop(box))
                    # Limit the size of each scan to bound memory use during prediction.
                    upright.thumbnail((3200, 3200))
                    pages.append(recognize(upright))
            return "\n\n".join(filter(None, pages))
    except (Image.DecompressionBombError, OSError, SyntaxError) as error:
        raise ValueError("The image could not be decoded. Check that it opens correctly.") from error
