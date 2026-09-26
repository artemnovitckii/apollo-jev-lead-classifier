import copy
import csv
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

import lead_classifier as app


def response_for(body, confidence=.9):
    """Fabricated protocol response for software tests, never a model result."""
    answers = {}
    for name, question in body["questions"].items():
        choices = list(question["criteria"])
        answers[name] = {"type": "choice", "choice": choices[0],
                         "confidence": confidence,
                         "probabilities": {c: float(i == 0) for i, c in enumerate(choices)}}
    return {"model": "test-model", "answers": answers,
            "usage": {"input_tokens": 100, "output_tokens": 10}}


class ClassifierTests(unittest.TestCase):
    def setUp(self):
        self.config = app.load_config(app.ROOT / "config/offer.json")
        self.leads = app.load_leads(app.ROOT / "examples/leads.csv", 10)
        self.body = app.request_body(self.leads[0], self.config, "jev-latest")

    def test_sample_and_absent_message(self):
        self.assertEqual(len(self.leads), 5)
        body = app.request_body(self.leads[3], self.config, "jev-latest")
        self.assertNotIn("message_check", body["questions"])
        self.assertEqual(body["state"]["prospect"]["industry"], "")

    def test_import_ignores_contact_fields_and_handles_bom(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "leads.csv"
            path.write_text('\ufeffCompany Name,Title,Email,First Name,Phone\n"Example, Inc",Owner,a@example.com,Anna,123\n')
            lead = app.load_leads(path, 1)[0]
            body = app.request_body(lead, self.config, "jev-latest")
            self.assertEqual(lead["company"], "Example, Inc")
            self.assertNotIn("a@example.com", json.dumps(body))
            self.assertNotIn("Anna", json.dumps(body))
            self.assertNotIn("lead_id", body["state"]["prospect"])

    def test_rejects_duplicate_ids_and_malformed_csv(self):
        for content in ("Company,lead_id\nA,1\nB,1\n", "Company\nA,B\n", "Company,Company\nA,B\n"):
            with self.subTest(content=content), tempfile.TemporaryDirectory() as folder:
                path = Path(folder) / "input.csv"
                path.write_text(content)
                with self.assertRaises(ValueError):
                    app.load_leads(path, 10)

    def test_invalid_model_output_cannot_route_to_outreach(self):
        response = response_for(self.body)
        for field, value in (("choice", "unexpected"), ("confidence", float("nan")),
                             ("probabilities", {"good_fit": 1}), ("confidence", True)):
            with self.subTest(field=field, value=value):
                invalid = copy.deepcopy(response)
                invalid["answers"]["fit"][field] = value
                with self.assertRaises(ValueError):
                    app.validate_answers(invalid, self.body)

    def test_unknown_or_any_low_confidence_goes_to_review(self):
        answers = response_for(self.body)["answers"]
        for question in answers:
            uncertain = copy.deepcopy(answers)
            uncertain[question]["confidence"] = .4
            self.assertEqual(app.flatten(self.leads[0], uncertain, .8, "test")["next_step"], "research_or_review")
        answers["angle"]["choice"] = "unknown"
        self.assertEqual(app.flatten(self.leads[0], answers, .8, "test")["next_step"], "research_or_review")

    def test_mismatch_and_poor_fit_routes(self):
        answers = response_for(self.body)["answers"]
        answers["message_check"]["choice"] = "mismatch"
        self.assertEqual(app.flatten(self.leads[0], answers, .8, "test")["next_step"], "revise_message")
        answers["fit"]["choice"] = "poor_fit"
        self.assertEqual(app.flatten(self.leads[0], answers, .8, "test")["next_step"], "deprioritize")

    def test_formula_escaping(self):
        for value in ("=HYPERLINK(1)", " +cmd", "\t@SUM(1)", "-1"):
            self.assertTrue(app.csv_safe(value).startswith("'"))
        self.assertEqual(app.csv_safe(.9), .9)

    def test_http_retries_rate_limit_but_not_auth_or_timeout(self):
        success = io.BytesIO(json.dumps(response_for(self.body)).encode())
        limited = HTTPError(app.ENDPOINT, 429, "rate limited", {}, None)
        with patch.object(app, "urlopen", side_effect=[limited, success]) as call, patch.object(app.time, "sleep") as sleep:
            app.post_jev(self.body, "fake-test-key")
            self.assertEqual(call.call_count, 2)
            sleep.assert_called_once()
            self.assertEqual(call.call_args.args[0].full_url, app.ENDPOINT)
        for error in (HTTPError(app.ENDPOINT, 401, "Unauthorized", {}, None), URLError("offline")):
            with patch.object(app, "urlopen", side_effect=error) as call:
                with self.assertRaises(ValueError):
                    app.post_jev(self.body, "fake-test-key")
                self.assertEqual(call.call_count, 1)

    def test_preview_never_calls_api(self):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / "preview"
            with patch("sys.argv", ["lead_classifier.py", "--preview", "--output", str(out)]), patch.object(app, "post_jev") as call:
                self.assertEqual(app.main(), 0)
                call.assert_not_called()
            summary = json.loads((out / "summary.json").read_text())
            self.assertEqual(summary["mode"], "preview_no_api_calls")
            self.assertIsNone(summary["cost_usd"])
            self.assertFalse((out / "classified.csv").exists())

    def test_mixed_success_and_failure_preserves_all_rows(self):
        def fake_post(body, key):
            if body["state"]["prospect"]["company"] == "Example Bay Agency":
                raise ValueError("JEV HTTP 401; see the troubleshooting guide.")
            return response_for(body)
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / "live-simulation"
            args = ["lead_classifier.py", "--live", "--output", str(out)]
            with patch("sys.argv", args), patch.dict(app.os.environ, {"TYPESAFE_API_KEY": "test"}), patch.object(app, "post_jev", side_effect=fake_post):
                self.assertEqual(app.main(), 1)
            with (out / "classified.csv").open(encoding="utf-8-sig", newline="") as f:
                rows = list(csv.DictReader(f))
            self.assertEqual(len(rows), 5)
            self.assertEqual([r["lead_id"] for r in rows], [r["lead_id"] for r in self.leads])
            self.assertEqual(rows[1]["next_step"], "error_review")
            self.assertEqual(rows[1]["fit_confidence"], "")
            summary = json.loads((out / "summary.json").read_text())
            self.assertEqual(summary["successful_rows"], 4)
            self.assertEqual(summary["failed_rows"], 1)


if __name__ == "__main__":
    unittest.main()
