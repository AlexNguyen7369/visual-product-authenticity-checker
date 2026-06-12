"""M12 — Image -> Gemini yes/no detector (the vertical slice closes = Phase 0, Step 0.3).

Goal: capture/load -> BGR->RGB -> JPEG-encode -> ask Gemini "is there a sneaker?" -> parse.
Learn: this is a degenerate identify() — same encode+POST+parse plumbing as Phase 2, simpler
       prompt. The PARSER is where robustness lives: model output is unreliable text.
Maps to: Phase 0 complete; the seed of Phase 2's identify().

See ../src/notes/roadmap.md (M12). parse_yes_no() is unit-tested in tests/.
"""
from pathlib import Path

import cv2

from m07_encode_base64 import to_jpeg_bytes
from m11_gemini_text import get_api_key

ASSETS = Path(__file__).resolve().parent / "assets"


def parse_yes_no(text: str) -> bool:
    """Map messy model text -> bool. Decide the contract for ambiguous answers (see M12 drill).

    Examples to handle: 'YES', 'yes.', 'Yes, it is', 'NO', 'I cannot determine'.
    """
    # TODO: normalize (strip/lower), check startswith('yes')/('no'); decide what UNKNOWN does.
    normalized = text.strip().lower()
    if normalized.startswith("yes"):
        return True
    elif normalized.startswith("no"):
        return False
    else:
        raise ValueError(f"Unexpected model output: {text!r}")
    raise NotImplementedError


def is_sneaker(frame_bgr) -> bool:
    """Send the frame to Gemini and return whether it contains a sneaker."""
    # TODO:
    #   from google import genai
    #   rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    #   jpeg = to_jpeg_bytes(rgb)
    #   client = genai.Client(api_key=get_api_key())
    #   resp = client.models.generate_content(
    #       model="gemini-2.5-flash",
    #       contents=[
    #           genai.types.Part.from_bytes(data=jpeg, mime_type="image/jpeg"),
    #           "Reply with only YES or NO: is there a sneaker/athletic shoe in this image?",
    #       ],
    #   )
    #   return parse_yes_no(resp.text)

    from google import genai
    rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    jpeg = to_jpeg_bytes(rgb)
    client = genai.Client(api_key=get_api_key())
    response = client.models.generate_content(
        model = "gemini-2.5-flash",
        contents = [
            genai.types.Part.from_bytes(data=jpeg, mime_type="image/jpeg"),
            "Reply with only YES or NO: is there a sneaker/athletic shoe in this image?",
        ]
    )
    return parse_yes_no(response.text)


def main() -> None:
    img = cv2.imread(str(ASSETS / "capture.jpg"))   # from M9, or swap in sample.jpg
    if img is None:
        raise FileNotFoundError("Run M9 first to capture.jpg, or point this at sample.jpg")
    print("sneaker?", is_sneaker(img))


if __name__ == "__main__":
    main()
