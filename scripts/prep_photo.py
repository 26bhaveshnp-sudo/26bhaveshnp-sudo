#!/usr/bin/env python3
"""
prep_photo.py  <path/to/source.jpg>

Prepares a face photo for ASCII conversion:
  1. Removes the background (rembg / U2Net)
  2. Boosts local contrast with CLAHE
  3. Composites onto pure white so the background maps to spaces

Writes source-prepped.png in the repo root. Run once per photo change.
"""

import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from rembg import remove

ROOT = Path(__file__).resolve().parents[1]


def prep_image(src_path: str) -> None:
    print(f"Loading  {src_path} ...")
    img = Image.open(src_path).convert("RGBA")

    print("Removing background ...")
    no_bg = remove(img)

    # Convert to numpy for OpenCV processing
    rgb = no_bg.convert("RGB")
    arr = np.array(rgb)

    # Boost local contrast (CLAHE) on grayscale channel
    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    gray = clahe.apply(gray)

    # White background where alpha == 0 (was background)
    alpha = np.array(no_bg.getchannel("A"))
    mask = alpha > 0
    white = np.full(gray.shape, 255, dtype=np.uint8)
    result = np.where(mask, gray, white)

    out_path = ROOT / "source-prepped.png"
    Image.fromarray(result).save(out_path, format="PNG")
    print(f"Saved  →  {out_path}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scripts/prep_photo.py path/to/photo.jpg")
        raise SystemExit(1)
    src = Path(sys.argv[1])
    if not src.exists():
        raise SystemExit(f"Source image not found: {src}")
    prep_image(str(src))
