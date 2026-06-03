"""M1 — Hello venv.  [FULLY IMPLEMENTED — use as a template]

Goal: prove you're running the isolated interpreter and that every dependency imports.
Learn: sys.executable points *inside* .venv\\ ; requirements.txt (declared) vs pip freeze (resolved).
Maps to: Phase 0, Step 0.1.
"""
import sys


def main() -> None:
    import cv2
    import numpy
    import PIL
    import dotenv
    from google import genai

    print ("python executable:", sys.executable)
    print ("in venv:", ".venv" in sys.executable)
    print ("cv2 version:", cv2.__version__)
    print ("numpy version:", numpy.__version__)
    print ("PIL version:", PIL.__version__)
    print ("dotenv version:", dotenv.__version__)
    print ("google-genai version:", genai.__version__)

if __name__ == "__main__":
    main() 
    

