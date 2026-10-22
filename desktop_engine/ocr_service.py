"""
OCR Service for J.A.R.V.I.S. Desktop Engine.
Handles optical character recognition requests via NVIDIA Nemotron OCR v2 with caching.
"""

from typing import Dict, Any
from providers.provider_manager import ProviderManager


class OCRService:
    """
    Service responsible strictly for analyzing image content for textual characters
    and returning detected words and bounding coordinates.
    """

    @staticmethod
    def perform_ocr(image_b64: str) -> Dict[str, Any]:
        """
        Invokes Nemotron OCR v2 via ProviderManager.
        Returns a dict with 'predictions' list containing text_prediction and bounding_box.
        """
        try:
            return ProviderManager.ocr(image_b64)
        except Exception as e:
            print(f"[OCRService Error] OCR request failed: {e}")
            return {"error": str(e), "predictions": []}
