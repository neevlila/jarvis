"""
Coordinate Space and Transformation System for J.A.R.V.I.S. Desktop Engine.

Explicitly represents and converts between coordinate spaces:
- SCREEN: Global absolute desktop screen coordinates (in pixels, as used by OS/PyAutoGUI)
- WINDOW: Coordinates relative to the active window top-left corner (in pixels)
- IMAGE: Pixel coordinates inside a screenshot or viewport image
- OCR_NORMALIZED: Relative normalized coordinates in range [0.0, 1.0] relative to image dimensions
- UI_AUTOMATION: Bounding rectangles directly reported by OS UI Automation tree (in screen pixels)
"""

from enum import Enum
from typing import Tuple, Optional, Union, Dict, Any


class CoordinateSpace(str, Enum):
    SCREEN = "screen"
    WINDOW = "window"
    IMAGE = "image"
    OCR_NORMALIZED = "ocr_normalized"
    UI_AUTOMATION = "ui_automation"


class Point:
    """Represents a 2D coordinate tagged with its coordinate space."""
    def __init__(self, x: float, y: float, space: CoordinateSpace = CoordinateSpace.SCREEN):
        self.x = float(x)
        self.y = float(y)
        self.space = space

    def to_tuple(self) -> Tuple[int, int]:
        """Returns integer (x, y) tuple for OS click execution."""
        return int(round(self.x)), int(round(self.y))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "x": self.x,
            "y": self.y,
            "space": self.space.value
        }

    def __repr__(self) -> str:
        return f"Point({self.x:.1f}, {self.y:.1f}, space={self.space.value})"

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Point):
            return False
        return (
            abs(self.x - other.x) < 1e-4 and
            abs(self.y - other.y) < 1e-4 and
            self.space == other.space
        )


class BoundingBox:
    """Represents a rectangular region tagged with its coordinate space."""
    def __init__(
        self,
        left: float,
        top: float,
        width: float,
        height: float,
        space: CoordinateSpace = CoordinateSpace.SCREEN
    ):
        self.left = float(left)
        self.top = float(top)
        self.width = max(0.0, float(width))
        self.height = max(0.0, float(height))
        self.space = space

    @property
    def right(self) -> float:
        return self.left + self.width

    @property
    def bottom(self) -> float:
        return self.top + self.height

    @property
    def center(self) -> Point:
        return Point(
            self.left + (self.width / 2.0),
            self.top + (self.height / 2.0),
            self.space
        )

    def contains(self, point: Point) -> bool:
        """Checks if a point is contained within this bounding box (requires matching coordinate space)."""
        if point.space != self.space:
            raise ValueError(f"Cannot check containment across different spaces: {point.space} vs {self.space}")
        return (
            self.left <= point.x <= self.right and
            self.top <= point.y <= self.bottom
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "left": int(round(self.left)),
            "top": int(round(self.top)),
            "width": int(round(self.width)),
            "height": int(round(self.height)),
            "space": self.space.value
        }

    def __repr__(self) -> str:
        return (
            f"BoundingBox(left={self.left:.1f}, top={self.top:.1f}, "
            f"w={self.width:.1f}, h={self.height:.1f}, space={self.space.value})"
        )

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, BoundingBox):
            return False
        return (
            abs(self.left - other.left) < 1e-4 and
            abs(self.top - other.top) < 1e-4 and
            abs(self.width - other.width) < 1e-4 and
            abs(self.height - other.height) < 1e-4 and
            self.space == other.space
        )


class CoordinateConverter:
    """
    Deterministic converter between coordinate spaces.
    Accounts for image scaling, window bounding offsets, and screen dimensions.
    """

    @staticmethod
    def ocr_normalized_to_image(
        point_or_bbox: Union[Point, BoundingBox],
        image_width: int,
        image_height: int
    ) -> Union[Point, BoundingBox]:
        """Converts normalized [0, 1] OCR coordinates to image pixel coordinates."""
        if image_width <= 0 or image_height <= 0:
            raise ValueError(f"Invalid image dimensions: {image_width}x{image_height}")

        if isinstance(point_or_bbox, Point):
            if point_or_bbox.space != CoordinateSpace.OCR_NORMALIZED:
                raise ValueError(f"Expected OCR_NORMALIZED point, got {point_or_bbox.space}")
            return Point(
                x=point_or_bbox.x * image_width,
                y=point_or_bbox.y * image_height,
                space=CoordinateSpace.IMAGE
            )
        elif isinstance(point_or_bbox, BoundingBox):
            if point_or_bbox.space != CoordinateSpace.OCR_NORMALIZED:
                raise ValueError(f"Expected OCR_NORMALIZED bbox, got {point_or_bbox.space}")
            return BoundingBox(
                left=point_or_bbox.left * image_width,
                top=point_or_bbox.top * image_height,
                width=point_or_bbox.width * image_width,
                height=point_or_bbox.height * image_height,
                space=CoordinateSpace.IMAGE
            )
        raise TypeError("Expected Point or BoundingBox")

    @staticmethod
    def image_to_window(
        point_or_bbox: Union[Point, BoundingBox],
        image_size: Tuple[int, int],
        window_size: Tuple[int, int]
    ) -> Union[Point, BoundingBox]:
        """
        Converts image pixel coordinates to window pixel coordinates.
        Handles downscaled/compressed images (e.g. 1280px resized screenshot).
        """
        img_w, img_h = image_size
        win_w, win_h = window_size
        if img_w <= 0 or img_h <= 0 or win_w <= 0 or win_h <= 0:
            raise ValueError("Dimensions must be positive non-zero values")

        scale_x = win_w / img_w
        scale_y = win_h / img_h

        if isinstance(point_or_bbox, Point):
            if point_or_bbox.space != CoordinateSpace.IMAGE:
                raise ValueError(f"Expected IMAGE point, got {point_or_bbox.space}")
            return Point(
                x=point_or_bbox.x * scale_x,
                y=point_or_bbox.y * scale_y,
                space=CoordinateSpace.WINDOW
            )
        elif isinstance(point_or_bbox, BoundingBox):
            if point_or_bbox.space != CoordinateSpace.IMAGE:
                raise ValueError(f"Expected IMAGE bbox, got {point_or_bbox.space}")
            return BoundingBox(
                left=point_or_bbox.left * scale_x,
                top=point_or_bbox.top * scale_y,
                width=point_or_bbox.width * scale_x,
                height=point_or_bbox.height * scale_y,
                space=CoordinateSpace.WINDOW
            )
        raise TypeError("Expected Point or BoundingBox")

    @staticmethod
    def window_to_screen(
        point_or_bbox: Union[Point, BoundingBox],
        window_rect: Union[BoundingBox, Dict[str, Any], Tuple[int, int, int, int]]
    ) -> Union[Point, BoundingBox]:
        """
        Converts window-relative coordinates to absolute desktop screen coordinates.
        window_rect can be a BoundingBox, dict {"left", "top", ...}, or tuple (left, top, width, height).
        """
        if isinstance(window_rect, BoundingBox):
            win_left, win_top = window_rect.left, window_rect.top
        elif isinstance(window_rect, dict):
            win_left = float(window_rect.get("left", 0))
            win_top = float(window_rect.get("top", 0))
        elif isinstance(window_rect, (tuple, list)) and len(window_rect) >= 2:
            win_left, win_top = float(window_rect[0]), float(window_rect[1])
        else:
            raise ValueError(f"Invalid window_rect format: {window_rect}")

        if isinstance(point_or_bbox, Point):
            if point_or_bbox.space != CoordinateSpace.WINDOW:
                raise ValueError(f"Expected WINDOW point, got {point_or_bbox.space}")
            return Point(
                x=point_or_bbox.x + win_left,
                y=point_or_bbox.y + win_top,
                space=CoordinateSpace.SCREEN
            )
        elif isinstance(point_or_bbox, BoundingBox):
            if point_or_bbox.space != CoordinateSpace.WINDOW:
                raise ValueError(f"Expected WINDOW bbox, got {point_or_bbox.space}")
            return BoundingBox(
                left=point_or_bbox.left + win_left,
                top=point_or_bbox.top + win_top,
                width=point_or_bbox.width,
                height=point_or_bbox.height,
                space=CoordinateSpace.SCREEN
            )
        raise TypeError("Expected Point or BoundingBox")

    @staticmethod
    def screen_to_window(
        point_or_bbox: Union[Point, BoundingBox],
        window_rect: Union[BoundingBox, Dict[str, Any], Tuple[int, int, int, int]]
    ) -> Union[Point, BoundingBox]:
        """Converts absolute desktop screen coordinates to window-relative coordinates."""
        if isinstance(window_rect, BoundingBox):
            win_left, win_top = window_rect.left, window_rect.top
        elif isinstance(window_rect, dict):
            win_left = float(window_rect.get("left", 0))
            win_top = float(window_rect.get("top", 0))
        elif isinstance(window_rect, (tuple, list)) and len(window_rect) >= 2:
            win_left, win_top = float(window_rect[0]), float(window_rect[1])
        else:
            raise ValueError(f"Invalid window_rect format: {window_rect}")

        if isinstance(point_or_bbox, Point):
            if point_or_bbox.space != CoordinateSpace.SCREEN:
                raise ValueError(f"Expected SCREEN point, got {point_or_bbox.space}")
            return Point(
                x=point_or_bbox.x - win_left,
                y=point_or_bbox.y - win_top,
                space=CoordinateSpace.WINDOW
            )
        elif isinstance(point_or_bbox, BoundingBox):
            if point_or_bbox.space != CoordinateSpace.SCREEN:
                raise ValueError(f"Expected SCREEN bbox, got {point_or_bbox.space}")
            return BoundingBox(
                left=point_or_bbox.left - win_left,
                top=point_or_bbox.top - win_top,
                width=point_or_bbox.width,
                height=point_or_bbox.height,
                space=CoordinateSpace.WINDOW
            )
        raise TypeError("Expected Point or BoundingBox")

    @classmethod
    def ocr_to_screen(
        cls,
        point_or_bbox: Union[Point, BoundingBox],
        image_size: Tuple[int, int],
        window_rect: Optional[Union[BoundingBox, Dict[str, Any], Tuple[int, int, int, int]]] = None,
        is_fullscreen: bool = True,
        screen_size: Optional[Tuple[int, int]] = None
    ) -> Union[Point, BoundingBox]:
        """
        Complete conversion pipeline: OCR_NORMALIZED -> IMAGE -> [WINDOW ->] SCREEN.
        If is_fullscreen=True: converts normalized coords directly against image -> screen scale.
        If is_fullscreen=False: converts normalized coords against image -> window -> screen offset.
        """
        img_w, img_h = image_size
        img_obj = cls.ocr_normalized_to_image(point_or_bbox, img_w, img_h)

        if is_fullscreen:
            if screen_size:
                scr_w, scr_h = screen_size
                scale_x = scr_w / img_w
                scale_y = scr_h / img_h
                if isinstance(img_obj, Point):
                    return Point(img_obj.x * scale_x, img_obj.y * scale_y, CoordinateSpace.SCREEN)
                else:
                    return BoundingBox(
                        img_obj.left * scale_x,
                        img_obj.top * scale_y,
                        img_obj.width * scale_x,
                        img_obj.height * scale_y,
                        CoordinateSpace.SCREEN
                    )
            # Default 1:1 image to screen
            if isinstance(img_obj, Point):
                return Point(img_obj.x, img_obj.y, CoordinateSpace.SCREEN)
            return BoundingBox(img_obj.left, img_obj.top, img_obj.width, img_obj.height, CoordinateSpace.SCREEN)

        # Window-specific capture
        if window_rect is None:
            raise ValueError("window_rect is required when is_fullscreen=False")

        if isinstance(window_rect, BoundingBox):
            win_w, win_h = int(window_rect.width), int(window_rect.height)
        elif isinstance(window_rect, dict):
            win_w = int(window_rect.get("width", img_w))
            win_h = int(window_rect.get("height", img_h))
        else:
            win_w, win_h = int(window_rect[2]), int(window_rect[3])

        win_obj = cls.image_to_window(img_obj, (img_w, img_h), (win_w, win_h))
        return cls.window_to_screen(win_obj, window_rect)

    @staticmethod
    def is_within_screen_bounds(
        point_or_bbox: Union[Point, BoundingBox],
        screen_size: Tuple[int, int]
    ) -> bool:
        """Validates that a screen coordinate is inside visible monitor boundaries."""
        scr_w, scr_h = screen_size
        if isinstance(point_or_bbox, Point):
            if point_or_bbox.space != CoordinateSpace.SCREEN:
                return False
            return 0 <= point_or_bbox.x < scr_w and 0 <= point_or_bbox.y < scr_h
        elif isinstance(point_or_bbox, BoundingBox):
            if point_or_bbox.space != CoordinateSpace.SCREEN:
                return False
            return (
                0 <= point_or_bbox.left < scr_w and
                0 <= point_or_bbox.top < scr_h and
                point_or_bbox.right <= scr_w + 1 and
                point_or_bbox.bottom <= scr_h + 1
            )
        return False
