"""
Perception Engine for J.A.R.V.I.S. Desktop Engine.

Unifies multi-modal desktop perception across:
1. UI Perception (OS Accessibility and Automation controls)
2. OCR Perception (Optical text character detection and spatial bounds)
3. Visual Perception (Optional/Experimental template and computer vision features)

Ensures all visual detections are accurately converted into consistent Screen-space coordinates.
"""

import os
from typing import List, Dict, Any, Optional
from PIL import Image
try:
    import pyautogui
except Exception:
    pyautogui = None

from desktop_engine.coordinates import (
    BoundingBox,
    CoordinateSpace,
    CoordinateConverter
)
from desktop_engine.models import PerceptionTarget, PerceptionState, ObservationState
from desktop_engine.ocr_service import OCRService
from desktop_engine.ui_automation_service import UIAutomationService
from providers.provider_manager import ProviderManager


class PerceptionEngine:
    """
    Coordinates UI Automation, OCR, and Computer Vision perception subsystems.
    """

    @classmethod
    def get_perception_data(
        cls,
        ui_available: bool = True,
        ocr_available: bool = True,
        observation: Optional[ObservationState] = None,
        image_path: str = "active_window.png"
    ) -> Dict[str, Any]:
        """
        Backward-compatible dictionary facade for the perception layer.
        """
        state = cls.perceive(
            ui_available=ui_available,
            ocr_available=ocr_available,
            observation=observation,
            image_path=image_path
        )
        return state.to_dict()

    @classmethod
    def perceive(
        cls,
        ui_available: bool = True,
        ocr_available: bool = True,
        observation: Optional[ObservationState] = None,
        image_path: str = "active_window.png"
    ) -> PerceptionState:
        """
        Executes perception sweep across UI tree, OCR text detector, and visual detectors.
        Returns a strongly-typed PerceptionState.
        """
        # 1. UI Perception
        ui_controls = []
        if ui_available:
            ui_controls = UIAutomationService.get_ui_controls(ui_available)

        # 2. OCR Perception with coordinate conversion
        ocr_controls = []
        if ocr_available and os.path.exists(image_path):
            try:
                ocr_controls = cls._perceive_ocr(image_path, observation)
            except Exception as e:
                print(f"[PerceptionEngine Warning] OCR perception failed: {e}")

        # 3. Multimodal Visual Perception (NVIDIA Nemotron Omni Vision)
        visual_elements: List[PerceptionTarget] = []
        if os.path.exists(image_path) and getattr(observation, 'enable_vision_analysis', False):
            try:
                visual_desc = ProviderManager.vision(
                    image_input=image_path,
                    prompt="Analyze this desktop screenshot and describe all visible application windows, interactive elements, status bars, and active focus."
                )
                if visual_desc:
                    visual_elements.append(PerceptionTarget(
                        source="vision_omni",
                        type="SceneDescription",
                        label=visual_desc[:200],
                        value=visual_desc,
                        confidence=0.90
                    ))
            except Exception as e:
                print(f"[PerceptionEngine Warning] Vision analysis failed: {e}")

        return PerceptionState(
            ui_controls=ui_controls,
            ocr_detections=ocr_controls,
            visual_elements=visual_elements
        )

    @classmethod
    def _perceive_ocr(
        cls,
        image_path: str,
        observation: Optional[ObservationState] = None
    ) -> List[PerceptionTarget]:
        """
        Runs OCR on the given image and accurately converts normalized coordinates into Screen space.
        """
        results: List[PerceptionTarget] = []
        if not os.path.exists(image_path):
            return results

        img = Image.open(image_path)
        img_w, img_h = img.size

        # Compress and encode image for OCR API
        image_b64 = ProviderManager.compress_image_to_b64(img)
        ocr_data = OCRService.perform_ocr(image_b64)

        if not ocr_data or "predictions" not in ocr_data:
            return results

        # Determine coordinate space mapping
        is_fullscreen = True
        window_bounds = None
        if observation:
            window_bounds = observation.active_window_bounds
            if window_bounds and image_path == observation.active_window_screenshot_path:
                is_fullscreen = False
        elif "active_window" in image_path:
            # Check if active window bounds can be acquired
            from desktop_engine.observation_engine import ObservationEngine
            details = ObservationEngine.get_active_window_details(capture_window_image=False)
            window_bounds = details.get("bounds")
            if window_bounds:
                is_fullscreen = False

        try:
            screen_size = pyautogui.size()
        except Exception:
            screen_size = (1920, 1080)

        for pred in ocr_data.get("predictions", []):
            txt_pred = pred.get("text_prediction", {})
            txt = (txt_pred.get("text") or "").strip()
            confidence = float(txt_pred.get("confidence", 0.90))
            bbox_dict = pred.get("bounding_box", {})
            points = bbox_dict.get("points", [])

            if txt and len(points) >= 4:
                xs = [p.get("x", 0.0) for p in points]
                ys = [p.get("y", 0.0) for p in points]

                norm_left = min(xs)
                norm_top = min(ys)
                norm_width = max(xs) - norm_left
                norm_height = max(ys) - norm_top

                norm_bbox = BoundingBox(
                    left=norm_left,
                    top=norm_top,
                    width=norm_width,
                    height=norm_height,
                    space=CoordinateSpace.OCR_NORMALIZED
                )

                # Convert normalized OCR bounds directly to Screen space
                screen_bbox = CoordinateConverter.ocr_to_screen(
                    point_or_bbox=norm_bbox,
                    image_size=(img_w, img_h),
                    window_rect=window_bounds,
                    is_fullscreen=is_fullscreen,
                    screen_size=screen_size
                )

                results.append(
                    PerceptionTarget(
                        source="ocr",
                        type="TextDetection",
                        label=txt,
                        bounds=screen_bbox,
                        confidence=confidence,
                        is_enabled=True,
                        is_focused=False,
                        metadata={"raw_points": points, "image_size": (img_w, img_h)}
                    )
                )

        return results
