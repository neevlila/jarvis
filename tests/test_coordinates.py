"""
Unit Tests for Coordinate Space Conversions.
"""

import unittest
from desktop_engine.coordinates import (
    CoordinateSpace,
    Point,
    BoundingBox,
    CoordinateConverter
)


class TestCoordinateConversions(unittest.TestCase):

    def test_point_and_bounding_box_basics(self):
        p = Point(100.4, 200.6, CoordinateSpace.SCREEN)
        self.assertEqual(p.to_tuple(), (100, 201))
        self.assertEqual(p.space, CoordinateSpace.SCREEN)

        bbox = BoundingBox(100, 200, 50, 40, CoordinateSpace.SCREEN)
        self.assertEqual(bbox.right, 150)
        self.assertEqual(bbox.bottom, 240)
        self.assertEqual(bbox.center, Point(125, 220, CoordinateSpace.SCREEN))
        self.assertTrue(bbox.contains(Point(120, 210, CoordinateSpace.SCREEN)))
        self.assertFalse(bbox.contains(Point(90, 210, CoordinateSpace.SCREEN)))

    def test_ocr_normalized_to_image(self):
        norm_point = Point(0.5, 0.5, CoordinateSpace.OCR_NORMALIZED)
        img_point = CoordinateConverter.ocr_normalized_to_image(norm_point, 1000, 500)
        self.assertEqual(img_point.space, CoordinateSpace.IMAGE)
        self.assertEqual(img_point.x, 500.0)
        self.assertEqual(img_point.y, 250.0)

        norm_bbox = BoundingBox(0.1, 0.2, 0.3, 0.4, CoordinateSpace.OCR_NORMALIZED)
        img_bbox = CoordinateConverter.ocr_normalized_to_image(norm_bbox, 1000, 500)
        self.assertEqual(img_bbox.space, CoordinateSpace.IMAGE)
        self.assertEqual(img_bbox.left, 100.0)
        self.assertEqual(img_bbox.top, 100.0)
        self.assertEqual(img_bbox.width, 300.0)
        self.assertEqual(img_bbox.height, 200.0)

    def test_image_to_window_scaling(self):
        # Image is 500x500, but actual window on screen is 1000x1000 (2x scaling)
        img_point = Point(100, 50, CoordinateSpace.IMAGE)
        win_point = CoordinateConverter.image_to_window(img_point, (500, 500), (1000, 1000))
        self.assertEqual(win_point.space, CoordinateSpace.WINDOW)
        self.assertEqual(win_point.x, 200.0)
        self.assertEqual(win_point.y, 100.0)

    def test_window_to_screen_offset(self):
        # Window is at screen position (300, 200)
        win_point = Point(50, 80, CoordinateSpace.WINDOW)
        screen_point = CoordinateConverter.window_to_screen(win_point, {"left": 300, "top": 200})
        self.assertEqual(screen_point.space, CoordinateSpace.SCREEN)
        self.assertEqual(screen_point.x, 350.0)
        self.assertEqual(screen_point.y, 280.0)

        # Reverse: Screen to window
        converted_back = CoordinateConverter.screen_to_window(screen_point, {"left": 300, "top": 200})
        self.assertEqual(converted_back.space, CoordinateSpace.WINDOW)
        self.assertEqual(converted_back.x, 50.0)
        self.assertEqual(converted_back.y, 80.0)

    def test_complete_ocr_to_screen_pipeline_window(self):
        # Normalized OCR point (0.5, 0.5) inside a cropped 640x480 screenshot of a window
        # Window is positioned at (100, 150) on screen and is size 640x480
        norm_point = Point(0.5, 0.5, CoordinateSpace.OCR_NORMALIZED)
        screen_pt = CoordinateConverter.ocr_to_screen(
            point_or_bbox=norm_point,
            image_size=(640, 480),
            window_rect={"left": 100, "top": 150, "width": 640, "height": 480},
            is_fullscreen=False
        )
        self.assertEqual(screen_pt.space, CoordinateSpace.SCREEN)
        self.assertEqual(screen_pt.to_tuple(), (420, 390))

    def test_screen_bounds_validation(self):
        in_bounds = Point(500, 500, CoordinateSpace.SCREEN)
        out_bounds = Point(2500, 500, CoordinateSpace.SCREEN)
        negative_bounds = Point(-10, 50, CoordinateSpace.SCREEN)

        self.assertTrue(CoordinateConverter.is_within_screen_bounds(in_bounds, (1920, 1080)))
        self.assertFalse(CoordinateConverter.is_within_screen_bounds(out_bounds, (1920, 1080)))
        self.assertFalse(CoordinateConverter.is_within_screen_bounds(negative_bounds, (1920, 1080)))


if __name__ == "__main__":
    unittest.main()
