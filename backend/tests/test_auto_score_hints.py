import os
import sys
import json
import unittest
from unittest.mock import patch, MagicMock

# Ensure the backend package is on the import path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from auto_score_hints import auto_score_hints

class TestAutoScoreHintsBiology(unittest.TestCase):
    def setUp(self):
        # Path to the sample hints markdown file
        self.sample_file = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'tests', 'sample_hints.md'))
        # Expected output report path
        self.report_file = self.sample_file.replace('.md', '_automated_audit.md')
        # Ensure any previous report is removed
        if os.path.exists(self.report_file):
            os.remove(self.report_file)
        # Mock API key (unused in mock)
        self.api_key = 'test-key'

    @patch('requests.post')
    def test_scoring_eight_samples(self, mock_post):
        # Mock response for each call
        def mock_response(*args, **kwargs):
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "choices": [{"message": {"content": json.dumps({"score": 8, "critique": "Good"})}}]
            }
            return mock_resp
        mock_post.side_effect = mock_response

        # Run the scoring function
        auto_score_hints(self.sample_file, self.api_key)

        # Verify that requests.post was called 8 times (one per sample)
        self.assertEqual(mock_post.call_count, 8, "Expected 8 API calls for 8 samples")

        # Verify that the report file was created
        self.assertTrue(os.path.exists(self.report_file), "Report file was not generated")
        with open(self.report_file, 'r', encoding='utf-8') as f:
            report_content = f.read()
        # Check that average score line is present and correctly calculated (8 per sample => avg 8.0)
        self.assertIn("Average Score**: 8.00 / 10", report_content)
        # Ensure each sample header appears
        for i in range(1, 9):
            self.assertIn(f"### Sample #{i}", report_content)

if __name__ == '__main__':
    unittest.main()
