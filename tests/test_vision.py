"""
Unit Tests for NVIDIA Multimodal Vision Integration.
"""

import unittest
from unittest.mock import patch, MagicMock
from providers.provider_manager import ProviderManager
from desktop_engine.models import ObservationState
from desktop_engine.perception_engine import PerceptionEngine


class TestVisionIntegration(unittest.TestCase):

    @patch("providers.provider_manager.ProviderManager._get_session")
    def test_provider_manager_vision_url(self, mock_session_getter):
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": "The image shows a code editor with Python files."
                    }
                }
            ]
        }
        mock_session.post.return_value = mock_response
        mock_session_getter.return_value = mock_session

        res = ProviderManager.vision(
            image_input="https://assets.ngc.nvidia.com/products/api-catalog/phi-3-5-vision/example1b.jpg",
            prompt="What is in this image?"
        )
        self.assertEqual(res, "The image shows a code editor with Python files.")
        mock_session.post.assert_called_once()
        call_kwargs = mock_session.post.call_args.kwargs
        self.assertEqual(call_kwargs["json"]["model"], "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning")


if __name__ == "__main__":
    unittest.main()
