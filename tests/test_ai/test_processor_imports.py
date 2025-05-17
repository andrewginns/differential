"""Test that processor.py can be imported without errors."""

import unittest


class TestProcessorImports(unittest.TestCase):
    """Test that processor.py can be imported without errors."""

    def test_import_processor(self):
        """Test that processor.py can be imported without errors."""
        try:
            from newsletter_generator.ai.processor import get_ai_processor
            self.assertTrue(True, "Successfully imported processor")
        except ImportError as e:
            self.fail(f"Failed to import processor: {e}")


if __name__ == "__main__":
    unittest.main()
