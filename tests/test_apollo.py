import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

import apollo
import lead_classifier as app
from local_settings import load_env
from test_classifier import response_for


def contact(number, domain="example.com"):
    return {"id": f"contact-{number}", "title": "Founder", "email": "private@example.com",
            "name": "Private Person", "organization_name": "Example",
            "organization": {"name": "Example", "primary_domain": domain},
            "typed_custom_fields": {"field-notes": "A supplied research note"}}


class ApolloTests(unittest.TestCase):
    def test_pagination_keeps_page_size_and_deduplicates(self):
        pages = [
            {"contacts": [contact(n) for n in range(100)], "pagination": {"total_pages": 3}},
            {"contacts": [contact(99)] + [contact(n) for n in range(100, 104)], "pagination": {"total_pages": 3}},
            {"contacts": [contact(104)], "pagination": {"total_pages": 3}},
        ]
        with patch.object(apollo, "api_request", side_effect=pages) as request:
            leads, meta = apollo.fetch_leads({}, "test", 105)
        self.assertEqual(len(leads), 105)
        self.assertEqual(len({r["lead_id"] for r in leads}), 105)
        self.assertEqual([c.kwargs["payload"]["per_page"] for c in request.call_args_list], [100, 100, 100])
        self.assertEqual([c.kwargs["payload"]["page"] for c in request.call_args_list], [1, 2, 3])
        self.assertEqual(meta["company_enrichments"], 0)

    def test_personal_fields_excluded_and_custom_mapping_explicit(self):
        source = {"contacts": [contact(1)]}
        with patch.object(apollo, "api_request", return_value=source):
            leads, _ = apollo.fetch_leads({"custom_fields": {"research_notes": "field-notes"}}, "test", 1)
        serialized = json.dumps(leads)
        self.assertNotIn("private@example.com", serialized)
        self.assertNotIn("Private Person", serialized)
        self.assertEqual(leads[0]["research_notes"], "A supplied research note")
        self.assertEqual(leads[0]["research_source"], "")
        self.assertEqual(leads[0]["industry"], "")

    def test_enrichment_opt_in_cached_by_domain_and_schema_fields_mapped(self):
        source = {"contacts": [contact(1), contact(2)]}
        enriched = {"organization": {"primary_domain": "example.com", "industry": "Design", "estimated_num_employees": 12,
                                     "short_description": "A service business", "country": "Australia", "technology_names": ["HubSpot"]}}
        with patch.object(apollo, "api_request", side_effect=[source, enriched]) as request:
            leads, meta = apollo.fetch_leads({}, "test", 2, enrich=True)
        self.assertEqual(request.call_count, 2)
        self.assertEqual(request.call_args.kwargs["query"], {"domain": "example.com"})
        self.assertEqual(meta["company_enrichments"], 1)
        self.assertEqual(meta["rows_missing_fit_context"], 0)
        self.assertEqual(leads[1]["employees"], "12")

    def test_enrichment_mismatch_stops_import(self):
        with patch.object(apollo, "api_request", side_effect=[{"contacts": [contact(1)]}, {"organization": {"primary_domain": "wrong.example"}}]):
            with self.assertRaisesRegex(ValueError, "different domain"):
                apollo.fetch_leads({}, "test", 1, enrich=True)

    def test_missing_domain_does_not_trigger_enrichment(self):
        with patch.object(apollo, "api_request", return_value={"contacts": [contact(1, "")]}) as request:
            _, meta = apollo.fetch_leads({}, "test", 1, enrich=True)
        self.assertEqual(request.call_count, 1)
        self.assertEqual(meta["companies_without_domain"], 1)

    def test_invalid_empty_and_repeated_pages_fail(self):
        for payload in ({}, {"contacts": []}, {"contacts": [{}]}):
            with self.subTest(payload=payload), patch.object(apollo, "api_request", return_value=payload):
                with self.assertRaises(ValueError):
                    apollo.fetch_leads({}, "test", 10)
        with patch.object(apollo, "api_request", return_value={"contacts": [contact(1)], "pagination": {"total_pages": 9}}):
            with self.assertRaisesRegex(ValueError, "repeated"):
                apollo.fetch_leads({}, "test", 10)

    def test_only_official_host_gets_api_key_and_rate_limit_retries(self):
        limited = HTTPError(apollo.BASE, 429, "limit", {}, None)
        success = io.BytesIO(json.dumps({"contacts": []}).encode())
        with patch.object(apollo, "urlopen", side_effect=[limited, success]) as request, patch.object(apollo.time, "sleep"):
            apollo.api_request("/contacts/search", "fake-test", payload={"page": 1})
        sent = request.call_args.args[0]
        self.assertEqual(sent.full_url, "https://api.apollo.io/api/v1/contacts/search")
        self.assertEqual(sent.get_header("X-api-key"), "fake-test")
        self.assertEqual(sent.get_method(), "POST")
        with patch.object(apollo, "urlopen", return_value=io.BytesIO(b'{"organization":{}}')) as request:
            apollo.api_request("/organizations/enrich", "fake-test", query={"domain": "example.com"})
        self.assertEqual(request.call_args.args[0].get_method(), "GET")

    def test_local_env_no_evaluation_and_environment_wins(self):
        with tempfile.TemporaryDirectory() as folder:
            env = Path(folder) / ".env"
            env.write_text('APOLLO_API_KEY="literal-$(not-executed)"\nTYPESAFE_API_KEY=file-value\nIGNORED_FIELD=value\n')
            with patch.dict(os.environ, {"TYPESAFE_API_KEY": "existing"}, clear=True):
                load_env(env)
                self.assertEqual(os.environ["TYPESAFE_API_KEY"], "existing")
                self.assertEqual(os.environ["APOLLO_API_KEY"], "literal-$(not-executed)")
                self.assertNotIn("IGNORED_FIELD", os.environ)

    def test_doctor_offline_and_no_secret_output(self):
        output = io.StringIO()
        with patch("sys.argv", ["lead_classifier.py", "--doctor"]), patch.dict(os.environ, {"APOLLO_API_KEY": "secret-value"}), patch.object(app, "load_env"), patch.object(apollo, "api_request") as request, patch("sys.stdout", output):
            self.assertEqual(app.main(), 0)
        request.assert_not_called()
        self.assertIn("APOLLO_API_KEY: configured", output.getvalue())
        self.assertNotIn("secret-value", output.getvalue())

    def test_apollo_preview_and_csv_round_trip(self):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / "preview"
            source = {"contacts": [contact(1)]}
            with patch("sys.argv", ["lead_classifier.py", "--source", "apollo", "--preview", "--output", str(out)]), patch.object(app, "load_env"), patch.dict(os.environ, {"APOLLO_API_KEY": "test"}), patch.object(apollo, "api_request", return_value=source), patch.object(app, "post_jev") as jev:
                self.assertEqual(app.main(), 0)
            jev.assert_not_called()
            self.assertEqual(json.loads((out / "summary.json").read_text())["mode"], "apollo_preview_no_jev_calls")
            imported = app.load_leads(out / "imported-leads.csv", 10)
            self.assertEqual(imported[0]["company_domain"], "example.com")
            self.assertNotIn("private@example.com", (out / "imported-leads.csv").read_text())

    def test_full_pipeline_with_simulated_providers(self):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / "simulated-run"
            args = ["lead_classifier.py", "--source", "apollo", "--live", "--draft-messages", "--limit", "1", "--output", str(out)]
            with patch("sys.argv", args), patch.object(app, "load_env"), patch.dict(os.environ, {"APOLLO_API_KEY": "test", "TYPESAFE_API_KEY": "test"}), patch.object(apollo, "api_request", return_value={"contacts": [contact(1)]}), patch.object(app, "post_jev", side_effect=lambda body, key: response_for(body)):
                self.assertEqual(app.main(), 0)
            summary = json.loads((out / "summary.json").read_text())
            self.assertEqual(summary["successful_rows"], 1)
            self.assertEqual(summary["source"]["source"], "apollo_saved_contacts")
            self.assertEqual(summary["messaging"]["drafts_created"], 1)
            self.assertEqual(summary["messaging"]["review_before_sending"], 1)
            self.assertTrue((out / "message_drafts.csv").exists())

    def test_existing_output_blocks_calls(self):
        with tempfile.TemporaryDirectory() as folder:
            args = ["lead_classifier.py", "--source", "apollo", "--preview", "--output", folder]
            with patch("sys.argv", args), patch.object(app, "load_env"), patch.object(apollo, "api_request") as request, patch("sys.stderr", io.StringIO()):
                with self.assertRaises(SystemExit):
                    app.main()
            request.assert_not_called()


if __name__ == "__main__":
    unittest.main()
