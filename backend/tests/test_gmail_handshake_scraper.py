import unittest
from unittest.mock import patch

from services.gmail_handshake_scraper import (
    extract_jobs_from_gmail_emails,
    infer_deadline_info,
    infer_job_attributes,
    infer_message_type,
    infer_title_company_from_text,
    is_trackable_message_type,
)


class GmailHandshakeMessageTypeTest(unittest.TestCase):
    def test_classifies_top_applicant_notice_as_candidate_signal(self):
        email = {
            "subject": "Rutuja Rohidas, Green Mountain Transit sees you as a top applicant for Transit Data Analyst and more",
            "body": "Your weekly jobs round-up New jobs just for you",
        }

        self.assertEqual(infer_message_type(email), "candidate_signal")

    def test_classifies_weekly_roundup_as_job_digest(self):
        email = {
            "subject": "Your weekly jobs round-up",
            "body": "New jobs just for you View more jobs",
        }

        self.assertEqual(infer_message_type(email), "job_digest")

    def test_application_confirmation_takes_priority_over_digest_words(self):
        email = {
            "subject": "Thank you for applying to AI Engineer at Schneider",
            "body": "Your weekly jobs round-up footer",
        }

        self.assertEqual(infer_message_type(email), "application_confirmation")

    def test_trackable_boundary_keeps_only_real_job_flow_messages(self):
        self.assertTrue(is_trackable_message_type("job"))
        self.assertTrue(is_trackable_message_type("internship"))
        self.assertTrue(is_trackable_message_type("application_confirmation"))
        self.assertFalse(is_trackable_message_type("event"))
        self.assertFalse(is_trackable_message_type("job_digest"))
        self.assertFalse(is_trackable_message_type("candidate_signal"))


class GmailHandshakeCardExtractionTest(unittest.TestCase):
    def test_extracts_deadline_after_applications_are_due_line(self):
        text = """
        Applications are due

        Friday, September 04, 2026 at 2 AM EDT.
        """

        info = infer_deadline_info(
            text,
            received_at="2026-08-13T12:00:00+00:00",
            message_type="job",
        )

        self.assertEqual(info["deadline_days"], 22)
        self.assertEqual(info["deadline_text"], "Friday, September 04, 2026")
        self.assertEqual(info["deadline_source"], "applications due date")

    def test_extracts_compact_deadline_without_year(self):
        text = """
        Applications for AI Engineering Intern are due

        Thu, Jul 23 11:59 pm EDT
        """

        info = infer_deadline_info(
            text,
            received_at="2026-07-19T15:24:57+00:00",
            message_type="job",
        )

        self.assertEqual(info["deadline_days"], 4)
        self.assertEqual(info["deadline_text"], "Thu, Jul 23, 2026")

    def test_extracts_job_fact_line_for_card(self):
        attrs = infer_job_attributes(
            "Schneider\nAI & Machine Learning Engineer\nFull-Time • Green Bay, WI (Onsite)"
        )

        self.assertEqual(attrs["employment_type"], "Full-Time")
        self.assertEqual(attrs["work_mode"], "Onsite")
        self.assertEqual(attrs["extracted_location"], "Green Bay, WI")

    def test_extracts_saved_job_title_and_company(self):
        title, company = infer_title_company_from_text(
            """
            Your saved job at Presto is about to close
            Applications for AI Engineering Intern, Voice & LLM Systems are due
            Presto
            AI Engineering Intern, Voice & LLM Systems
            """,
            "Your saved job",
            "Handshake",
        )

        self.assertEqual(title, "AI Engineering Intern, Voice & LLM Systems")
        self.assertEqual(company, "Presto")

    def test_keeps_periods_inside_company_names(self):
        title, company = infer_title_company_from_text(
            "New Data Scientist at U.S. Department of Health and Human Services\nApply early",
            "New Data Scientist at U.S. Department of Health and Human Services",
            "Handshake",
        )

        self.assertEqual(title, "Data Scientist")
        self.assertEqual(company, "U.S. Department of Health and Human Services")


class GmailHandshakeExtractionFilterTest(unittest.TestCase):
    @patch("services.gmail_handshake_scraper.fetch_handshake_emails")
    def test_skips_roundups_and_candidate_signals_but_keeps_trackable_messages(self, fetch_mock):
        fetch_mock.return_value = [
            {
                "email_id": "digest-1",
                "thread_id": "digest-thread",
                "subject": "Rutuja Rohidas, Green Mountain Transit sees you as a top applicant for Transit Data Analyst and more",
                "sender": "Handshake <handshake@g.joinhandshake.com>",
                "received_at": "2026-08-10T20:17:14+00:00",
                "snippet": "",
                "body": "Your weekly jobs round-up New jobs just for you View more jobs",
                "html": '<a href="https://app.joinhandshake.com/job-search/111">View more jobs</a>',
            },
            {
                "email_id": "job-1",
                "thread_id": "job-thread",
                "subject": "New Data Analyst at Acme",
                "sender": "Handshake <handshake@notifications.joinhandshake.com>",
                "received_at": "2026-08-10T20:17:14+00:00",
                "snippet": "",
                "body": "Acme is hiring a Data Analyst.",
                "html": '<a href="https://app.joinhandshake.com/job-search/222">Apply</a>',
            },
            {
                "email_id": "confirmation-1",
                "thread_id": "confirmation-thread",
                "subject": "Thank you for applying to AI Engineer at Schneider",
                "sender": "Handshake <handshake@notifications.joinhandshake.com>",
                "received_at": "2026-08-10T20:17:14+00:00",
                "snippet": "",
                "body": "We have received your application.",
                "html": "",
            },
            {
                "email_id": "job-without-link",
                "thread_id": "job-without-link-thread",
                "subject": "New Data Scientist at No Link Company",
                "sender": "Handshake <handshake@notifications.joinhandshake.com>",
                "received_at": "2026-08-10T20:17:14+00:00",
                "snippet": "",
                "body": "No Link Company is hiring a Data Scientist.",
                "html": "<p>No application URL in this email.</p>",
            },
        ]

        result = extract_jobs_from_gmail_emails(max_results=3, lookback_days=30)
        subjects = [job["email_subject"] for job in result["jobs"]]

        self.assertEqual(len(result["emails"]), 4)
        self.assertEqual(len(result["jobs"]), 2)
        self.assertNotIn(
            "Rutuja Rohidas, Green Mountain Transit sees you as a top applicant for Transit Data Analyst and more",
            subjects,
        )
        self.assertIn("New Data Analyst at Acme", subjects)
        self.assertIn("Thank you for applying to AI Engineer at Schneider", subjects)
        self.assertNotIn("New Data Scientist at No Link Company", subjects)
        job = next(job for job in result["jobs"] if job["email_subject"] == "New Data Analyst at Acme")
        self.assertEqual(job["link_confidence"], "confirmed")
        self.assertIn("extraction_evidence", job)


if __name__ == "__main__":
    unittest.main()
