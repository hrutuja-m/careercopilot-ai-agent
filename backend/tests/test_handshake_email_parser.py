import unittest
from unittest.mock import Mock, patch

from services.handshake_email_parser import (
    extract_all_links,
    is_handshake_posting_url,
    is_login_or_auth_url,
    is_placeholder_url,
    is_real_apply_url,
    pick_application_link,
    resolve_handshake_tracking_url,
)


class HandshakeEmailParserTest(unittest.TestCase):
    def test_prefers_button_style_apply_cta_href(self):
        html = """
        <html>
          <body>
            <a href="https://joinhandshake.com/stu/postings/12345">Apply</a>
            <a href="https://joinhandshake.com/unsubscribe">Unsubscribe</a>
          </body>
        </html>
        """

        self.assertEqual(
            pick_application_link(html=html),
            {"href": "https://joinhandshake.com/stu/postings/12345", "is_cta": True},
        )

    def test_uses_handshake_posting_path_when_text_is_generic(self):
        html = """
        <a href="https://click.joinhandshake.com/track/open">Logo</a>
        <a href="https://app.joinhandshake.com/jobs/98765">Open</a>
        """

        self.assertEqual(
            pick_application_link(html=html),
            {"href": "https://app.joinhandshake.com/jobs/98765", "is_cta": False},
        )

    def test_falls_back_to_first_non_tracking_link(self):
        html = """
        <a href="https://images.example.com/banner.png">Banner</a>
        <a href="https://example.com/careers/data-intern">Details</a>
        <a href="https://example.com/preferences">Preferences</a>
        """

        self.assertEqual(
            pick_application_link(html=html),
            {"href": "https://example.com/careers/data-intern", "is_cta": False},
        )

    def test_reads_plain_text_fallback_links(self):
        text = "View posting: https://joinhandshake.com/postings/abc123"

        self.assertEqual(
            pick_application_link(text=text),
            {"href": "https://joinhandshake.com/postings/abc123", "is_cta": False},
        )

    def test_extracts_html_and_plain_text_links_without_duplicates(self):
        html = '<a href="https://joinhandshake.com/stu/postings/12345">View Job</a>'
        text = "https://joinhandshake.com/stu/postings/12345 https://example.com/apply"

        self.assertEqual(
            extract_all_links(html=html, text=text),
            [
                "https://joinhandshake.com/stu/postings/12345",
                "https://example.com/apply",
            ],
        )


class HandshakePostingUrlTest(unittest.TestCase):
    def test_accepts_a_genuine_posting_path(self):
        self.assertTrue(
            is_handshake_posting_url(
                "https://app.joinhandshake.com/job-search/11263669?utm_source=approve_job_posting_mailer"
            )
        )

    def test_rejects_login_redirect_that_merely_mentions_the_path_in_the_query_string(self):
        # This is the actual bug: the old implementation did a substring
        # check against the *whole URL*, so a login page redirect that
        # carries the intended destination in a query parameter (very
        # common for auth-gated redirects) was misclassified as a real
        # posting. The path here is "/login" — the "/job-search/" text is
        # only present inside the "next" query parameter.
        self.assertFalse(
            is_handshake_posting_url(
                "https://app.joinhandshake.com/login?next=/job-search/11263669"
            )
        )
        self.assertFalse(
            is_handshake_posting_url(
                "https://app.joinhandshake.com/login?next=%2Fjob-search%2F11263669"
            )
        )

    def test_rejects_non_handshake_domain(self):
        self.assertFalse(is_handshake_posting_url("https://example.com/job-search/123"))


class IsLoginOrAuthUrlTest(unittest.TestCase):
    def test_flags_common_login_paths(self):
        self.assertTrue(is_login_or_auth_url("https://app.joinhandshake.com/login?next=/jobs/1"))
        self.assertTrue(is_login_or_auth_url("https://example.com/users/sign_in"))

    def test_does_not_flag_a_normal_posting_path(self):
        self.assertFalse(is_login_or_auth_url("https://app.joinhandshake.com/job-search/11263669"))


class IsPlaceholderUrlTest(unittest.TestCase):
    def test_flags_example_com(self):
        self.assertTrue(is_placeholder_url("https://apply.example.com/deep-measures/intern"))

    def test_does_not_flag_a_real_domain(self):
        self.assertFalse(is_placeholder_url("https://app.joinhandshake.com/jobs/1"))


class IsRealApplyUrlTest(unittest.TestCase):
    def test_rejects_placeholder_links(self):
        self.assertFalse(is_real_apply_url("https://apply.example.com/deep-measures/intern"))

    def test_rejects_a_handshake_login_redirect_even_if_it_mentions_a_posting_path(self):
        self.assertFalse(
            is_real_apply_url("https://app.joinhandshake.com/login?next=/job-search/11263669")
        )

    def test_accepts_a_genuine_handshake_posting_link(self):
        self.assertTrue(is_real_apply_url("https://app.joinhandshake.com/job-search/11263669"))

    def test_rejects_a_generic_handshake_link_without_cta_trust(self):
        # Some link that's on joinhandshake.com but isn't a posting path
        # and wasn't labeled "Apply" in the email shouldn't be trusted.
        self.assertFalse(is_real_apply_url("https://app.joinhandshake.com/dashboard"))

    def test_trusted_cta_accepts_a_non_handshake_domain(self):
        # A link explicitly labeled "Apply" in the source email should be
        # trusted even when it points at the employer's own career page
        # rather than joinhandshake.com.
        self.assertTrue(
            is_real_apply_url("https://careers.acmecorp.com/jobs/1234", trusted_cta=True)
        )

    def test_trusted_cta_still_rejects_a_login_page(self):
        self.assertFalse(
            is_real_apply_url("https://careers.acmecorp.com/login", trusted_cta=True)
        )

    def test_trusted_cta_rejects_raw_handshake_tracking_link(self):
        self.assertFalse(
            is_real_apply_url(
                "https://email.notifications.joinhandshake.com/c/abc123",
                trusted_cta=True,
            )
        )


class ResolveHandshakeTrackingUrlTest(unittest.TestCase):
    @patch("services.handshake_email_parser.requests.get")
    def test_resolves_tracking_redirect_to_posting_location(self, get_mock):
        response = Mock()
        response.headers = {
            "location": "https://app.joinhandshake.com/job-search/11271397?utm_source=email"
        }
        get_mock.return_value = response

        self.assertEqual(
            resolve_handshake_tracking_url("https://email.notifications.joinhandshake.com/c/abc"),
            "https://app.joinhandshake.com/job-search/11271397?utm_source=email",
        )

    @patch("services.handshake_email_parser.requests.get")
    def test_rejects_tracking_redirect_to_login(self, get_mock):
        response = Mock()
        response.headers = {
            "location": "https://app.joinhandshake.com/login?next=/job-search/11271397"
        }
        get_mock.return_value = response

        self.assertIsNone(
            resolve_handshake_tracking_url("https://email.notifications.joinhandshake.com/c/abc")
        )


if __name__ == "__main__":
    unittest.main()
