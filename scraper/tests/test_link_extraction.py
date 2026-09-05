from __future__ import annotations

import unittest

from scraper.scrapers.link_extraction import (
    JOBS_COUNT_RE,
    MAX_TITLE_LEN,
    NON_JOB_TEXT,
    _clean_job_title_and_type,
    _looks_like_job_detail_path,
    clean_job_title,
    extract_accordion_jobs,
    extract_job_links,
    extract_jobs,
    extract_jsonld_jobs,
    is_furniture_title,
)


class TestWordFusion(unittest.TestCase):
    def test_adjacent_spans_get_space_separated(self) -> None:
        html = """
        <html><body>
        <a href="https://example.com/careers/senior-audio-engineer-4471">
          <span>Senior Audio Engineer</span><span>Remote</span>
        </a>
        </body></html>
        """
        jobs = extract_job_links(html, "https://example.com/careers")
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].title, "Senior Audio Engineer")

    def test_no_separator_would_have_fused(self) -> None:
        html = """
        <html><body>
        <a href="https://example.com/careers/dsp-engineer-8821">
          <span>DSP</span><span>Engineer</span>
        </a>
        </body></html>
        """
        jobs = extract_job_links(html, "https://example.com/careers")
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].title, "DSP Engineer")


class TestCleanJobTitleRealExamples(unittest.TestCase):
    def test_deal_desk_example(self) -> None:
        raw = "Deal Desk Senior Analyst Remote Posted 8 days ago"
        self.assertEqual(clean_job_title(raw), "Deal Desk Senior Analyst")

    def test_senior_machine_learning_engineer_example(self) -> None:
        raw = "Senior Machine Learning Engineer Mountain View, CA Apply"
        self.assertEqual(clean_job_title(raw), "Senior Machine Learning Engineer")

    def test_product_manager_example(self) -> None:
        raw = (
            "Product manager Milan (Italy), London (UK), Madrid (Spain), "
            "Warsaw (Poland), or fully remote from eligible countries"
        )
        self.assertEqual(clean_job_title(raw), "Product manager")

    def test_enterprise_account_executive_example(self) -> None:
        raw = "Enterprise Account Executive, Expansion Remote Apply"
        self.assertEqual(
            clean_job_title(raw), "Enterprise Account Executive, Expansion"
        )

    def test_new_business_account_executive_example(self) -> None:
        raw = (
            "New Business Account Executive (German speaker) "
            "Remote - United Kingdom Remote Posted 7 days ago"
        )
        self.assertEqual(
            clean_job_title(raw),
            "New Business Account Executive (German speaker)",
        )


class TestCleanJobTitleJobType(unittest.TestCase):
    def test_trailing_contract_captured_as_job_type(self) -> None:
        html = """
        <html><body>
        <a href="https://example.com/careers/mix-engineer-9910">
          <span>Studio Mix Engineer</span><span>Contract</span>
        </a>
        </body></html>
        """
        jobs = extract_job_links(html, "https://example.com/careers")
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].title, "Studio Mix Engineer")
        self.assertEqual(jobs[0].job_type, "Contract")

    def test_trailing_internship_captured_as_job_type_but_kept_in_title(self) -> None:
        html = """
        <html><body>
        <a href="https://example.com/careers/sound-design-intern-4402">
          <span>Sound Design Assistant</span><span>Internship</span>
        </a>
        </body></html>
        """
        jobs = extract_job_links(html, "https://example.com/careers")
        self.assertEqual(jobs[0].title, "Sound Design Assistant Internship")
        self.assertEqual(jobs[0].job_type, "Internship")


class TestEmploymentWordNotMangled(unittest.TestCase):
    def test_contract_manager_kept_intact(self) -> None:
        self.assertEqual(clean_job_title("Contract Manager"), "Contract Manager")

    def test_full_stack_developer_kept_intact(self) -> None:
        self.assertEqual(
            clean_job_title("Full Stack Developer"), "Full Stack Developer"
        )

    def test_internship_coordinator_kept_intact(self) -> None:
        self.assertEqual(
            clean_job_title("Internship Coordinator"), "Internship Coordinator"
        )

    def test_department_word_before_comma_not_mangled(self) -> None:
        self.assertEqual(clean_job_title("Head of Sales, EU"), "Head of Sales, EU")

    def test_role_noun_before_state_code_not_mangled(self) -> None:
        self.assertEqual(
            clean_job_title("Regional Sales Manager, TX"),
            "Regional Sales Manager, TX",
        )

    def test_single_paren_qualifier_not_mangled(self) -> None:
        self.assertEqual(
            clean_job_title("Software Engineer (Remote)"),
            "Software Engineer (Remote)",
        )
        self.assertEqual(
            clean_job_title("Data Analyst (US)"), "Data Analyst (US)"
        )

    def test_internship_head_noun_survives_verbatim(self) -> None:
        self.assertEqual(
            clean_job_title("Game Audio Internship"), "Game Audio Internship"
        )
        self.assertEqual(
            clean_job_title("Audio Engineering Internship"),
            "Audio Engineering Internship",
        )

    def test_intern_head_noun_survives_verbatim(self) -> None:
        self.assertEqual(
            clean_job_title("Sound Design Intern"), "Sound Design Intern"
        )

    def test_internship_and_intern_still_set_job_type(self) -> None:
        title, job_type = _clean_job_title_and_type("Game Audio Internship")
        self.assertEqual(title, "Game Audio Internship")
        self.assertEqual(job_type, "Internship")

        title, job_type = _clean_job_title_and_type("Sound Design Intern")
        self.assertEqual(title, "Sound Design Intern")
        self.assertEqual(job_type, "Intern")

    def test_internship_titles_remain_detectable_as_entry_seniority(self) -> None:
        from scraper.normalizer import detect_seniority

        for title in ("Game Audio Internship", "Sound Design Intern"):
            cleaned = clean_job_title(title)
            self.assertEqual(cleaned, title)
            self.assertEqual(detect_seniority(cleaned), "entry")


class TestShoutyCaseNormalization(unittest.TestCase):
    def test_all_caps_audio_title_is_titlecased_not_rejected(self) -> None:
        self.assertFalse(
            is_furniture_title("SENIOR AUDIO DSP ENGINEER - CUPERTINO")
        )
        self.assertEqual(
            clean_job_title("SENIOR AUDIO DSP ENGINEER - CUPERTINO"),
            "Senior Audio DSP Engineer - Cupertino",
        )

    def test_all_caps_title_without_acronym_is_titlecased(self) -> None:
        self.assertFalse(
            is_furniture_title("LIVE SOUND ENGINEER FOR TOURING PRODUCTION")
        )
        self.assertEqual(
            clean_job_title("LIVE SOUND ENGINEER FOR TOURING PRODUCTION"),
            "Live Sound Engineer For Touring Production",
        )

    def test_all_lowercase_title_is_titlecased_not_rejected(self) -> None:
        self.assertFalse(is_furniture_title("support agent for reverse logistics"))
        self.assertEqual(
            clean_job_title("support agent for reverse logistics"),
            "Support Agent For Reverse Logistics",
        )

    def test_short_all_caps_title_left_alone(self) -> None:
        self.assertEqual(clean_job_title("VP OF SALES"), "VP OF SALES")

    def test_mixed_case_title_untouched(self) -> None:
        self.assertEqual(
            clean_job_title("Senior Audio Engineer"), "Senior Audio Engineer"
        )


class TestFurnitureRejection(unittest.TestCase):
    def test_apply_for_financing_rejected(self) -> None:
        self.assertTrue(is_furniture_title("Apply for Financing"))

    def test_long_sentence_with_link_phrase_rejected(self) -> None:
        text = (
            "Follow this link to reach our Job Search page to search for "
            "available jobs in a more accessible format."
        )
        self.assertTrue(is_furniture_title(text))

    def test_contact_us_reach_out_rejected(self) -> None:
        text = (
            "Contact Us Reach out to discuss licensing, integrations, or "
            "partnership opportunities. Keep Reading"
        )
        self.assertTrue(is_furniture_title(text))

    def test_house_of_worship_marketing_copy_rejected(self) -> None:
        text = (
            "House of Worship Modernize your infrastructure to support new "
            "opportunities and transform the worship experience."
        )
        self.assertTrue(is_furniture_title(text))

    def test_committed_to_marketing_copy_rejected(self) -> None:
        text = (
            "Learning and Development We are committed to building the "
            "strongest Emerson and helping our team members reach their "
            "highest potential."
        )
        self.assertTrue(is_furniture_title(text))

    def test_category_card_with_job_count_rejected(self) -> None:
        text = (
            "Engineering United States A brief description highlighting "
            "the key message or action users can take. 0 jobs"
        )
        self.assertTrue(is_furniture_title(text))

    def test_ellipsis_teaser_rejected(self) -> None:
        text = (
            "Lakepointe Church Find out how Lakepointe is pursuing new "
            "opportunities for ministry with cutting-edge SMPTE…"
        )
        self.assertTrue(is_furniture_title(text))

    def test_bare_jobs_count_rejected(self) -> None:
        self.assertTrue(is_furniture_title("Rail 25 jobs"))
        self.assertTrue(is_furniture_title("Group 0 jobs"))

    def test_abbreviation_period_not_treated_as_sentence_break(self) -> None:
        self.assertFalse(
            is_furniture_title("Sr. Director, Content Commerce, Robotics")
        )
        self.assertFalse(
            is_furniture_title("Bilingual U.S. Tax Business Partner")
        )

    def test_year_prefix_not_treated_as_job_count(self) -> None:
        self.assertFalse(bool(JOBS_COUNT_RE.search("2026 Senior Producer")))


class TestUrlHeuristic(unittest.TestCase):
    def test_detail_path_with_hyphen_and_digit_accepted(self) -> None:
        html = (
            '<html><body><a href="/careers/senior-audio-engineer-1234">'
            "Senior Audio Engineer</a></body></html>"
        )
        jobs = extract_job_links(html, "https://example.com/careers")
        self.assertEqual(len(jobs), 1)
        self.assertEqual(
            jobs[0].url, "https://example.com/careers/senior-audio-engineer-1234"
        )

    def test_bare_careers_root_rejected(self) -> None:
        html = '<html><body><a href="/careers/">Careers</a></body></html>'
        jobs = extract_job_links(html, "https://example.com/careers")
        self.assertEqual(len(jobs), 0)

    def test_careers_teams_section_rejected(self) -> None:
        html = '<html><body><a href="/careers/teams">Our Teams</a></body></html>'
        jobs = extract_job_links(html, "https://example.com/careers")
        self.assertEqual(len(jobs), 0)

    def test_careers_benefits_section_rejected(self) -> None:
        html = '<html><body><a href="/careers/benefits">Benefits</a></body></html>'
        jobs = extract_job_links(html, "https://example.com/careers")
        self.assertEqual(len(jobs), 0)

    def test_short_generic_segment_without_job_hint_text_rejected(self) -> None:
        html = (
            '<html><body><a href="/careers/openings">See What Is Available</a>'
            "</body></html>"
        )
        jobs = extract_job_links(html, "https://example.com/careers")
        self.assertEqual(len(jobs), 0)


class TestTitleLength(unittest.TestCase):
    def test_title_over_max_len_rejected(self) -> None:
        long_title = (
            "Senior Principal Staff Distinguished Fellow Software Systems "
            "Architecture Audio Platform Engineer"
        )
        self.assertGreater(len(long_title), MAX_TITLE_LEN)
        self.assertLessEqual(len(long_title.split()), 12)
        html = (
            f'<html><body><a href="/careers/audio-role-5521">{long_title}</a>'
            "</body></html>"
        )
        jobs = extract_job_links(html, "https://example.com/careers")
        self.assertEqual(len(jobs), 0)

    def test_title_under_max_len_accepted(self) -> None:
        html = (
            '<html><body><a href="/careers/audio-role-5521">'
            "Senior Audio Engineer</a></body></html>"
        )
        jobs = extract_job_links(html, "https://example.com/careers")
        self.assertEqual(len(jobs), 1)


JSONLD_OVERRIDE_HTML = """
<html><body>
<a href="https://example.com/careers/mixing-engineer-7712">Mixing Engineer</a>
<script type="application/ld+json">
{
  "@type": "JobPosting",
  "title": "Senior Mixing Engineer",
  "description": "Mix records for major labels.",
  "url": "https://example.com/careers/mixing-engineer-7712",
  "datePosted": "2026-08-01",
  "employmentType": "FULL_TIME"
}
</script>
</body></html>
"""


class TestJsonLdStillWorksAndOverrides(unittest.TestCase):
    def test_jsonld_job_parses_and_overrides_anchor(self) -> None:
        jobs = extract_jobs(JSONLD_OVERRIDE_HTML, "https://example.com/careers")
        self.assertEqual(len(jobs), 1)
        job = jobs[0]
        self.assertEqual(job.title, "Senior Mixing Engineer")
        self.assertEqual(job.description, "Mix records for major labels.")
        self.assertEqual(job.job_type, "full-time")
        self.assertEqual(
            job.url, "https://example.com/careers/mixing-engineer-7712"
        )


class TestQueryStringJobIds(unittest.TestCase):
    def test_job_id_in_query_accepted(self) -> None:
        self.assertTrue(_looks_like_job_detail_path("/sfcareer/jobreqcareer", "jobId=1234"))
        self.assertTrue(_looks_like_job_detail_path("/careers/apply", "reqId=99"))
        self.assertTrue(_looks_like_job_detail_path("/x", "gh_jid=4007"))

    def test_query_without_id_still_rejected(self) -> None:
        self.assertFalse(_looks_like_job_detail_path("/careers", "page=2"))
        self.assertFalse(_looks_like_job_detail_path("/jobs", "sort=date"))
        self.assertFalse(_looks_like_job_detail_path("/sfcareer/jobreqcareer", "jobTitle=abc"))

    def test_shared_path_board_extracts_every_job(self) -> None:
        html = """
        <html><body>
        <a href="/sfcareer/jobreqcareer?jobId=101">Manual Test Engineer</a>
        <a href="/sfcareer/jobreqcareer?jobId=102">Patient Care Coordinator</a>
        <a href="/sfcareer/jobreqcareer?jobId=103">Head of Accounting</a>
        </body></html>
        """
        jobs = extract_job_links(html, "https://www.sonova.com/careers/")
        self.assertEqual(len(jobs), 3)


class TestShortTitleAbbreviations(unittest.TestCase):
    def test_short_title_with_abbreviation_survives(self) -> None:
        self.assertFalse(is_furniture_title("Leg. Audionom Norrkoping"))
        self.assertFalse(is_furniture_title("Ing. Acustica Milano"))

    def test_long_prose_still_rejected(self) -> None:
        self.assertTrue(
            is_furniture_title(
                "Contact Us Reach out to discuss licensing options. Keep Reading more"
            )
        )


class TestTemplatePlaceholders(unittest.TestCase):
    def test_placeholder_tokens_stripped(self) -> None:
        raw = (
            "Senior Product Designer London, GB"
            "%LABEL_POSITION_TYPE_REMOTE_HYBRID%%LABEL_POSITION_TYPE_F%"
        )
        self.assertEqual(clean_job_title(raw), "Senior Product Designer")

    def test_mustache_placeholder_stripped(self) -> None:
        self.assertEqual(clean_job_title("Audio Engineer {{location}}"), "Audio Engineer")


class TestStructuralTitleFallback(unittest.TestCase):
    def test_heading_inside_anchor_used_when_flat_text_too_long(self) -> None:
        flat_text = (
            "Audio Systems Engineer Location Menlo Park California Corporate "
            "Headquarters Building Twenty Two"
        )
        self.assertGreater(len(flat_text), MAX_TITLE_LEN)
        self.assertLessEqual(len(flat_text.split()), 12)
        html = """
        <html><body>
        <a href="/jobs/98765-audio-systems-engineer">
          <h3>Audio Systems Engineer</h3>
          <span>Location Menlo Park California Corporate Headquarters Building
          Twenty Two</span>
        </a>
        </body></html>
        """
        jobs = extract_job_links(html, "https://example.com/jobs")
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].title, "Audio Systems Engineer")

    def test_heading_inside_anchor_used_when_flat_text_has_too_many_words(self) -> None:
        flat_text = (
            "Audio Systems Engineer Team Berlin Remote Full Time Senior Level "
            "Great Culture Fun"
        )
        self.assertLessEqual(len(flat_text), MAX_TITLE_LEN)
        self.assertGreater(len(flat_text.split()), 12)
        html = """
        <html><body>
        <a href="/jobs/22222-audio-systems-engineer">
          <h3>Audio Systems Engineer</h3>
          <span>Team Berlin Remote Full Time Senior Level Great Culture Fun</span>
        </a>
        </body></html>
        """
        jobs = extract_job_links(html, "https://example.com/jobs")
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].title, "Audio Systems Engineer")

    def test_card_heading_used_when_anchor_text_is_cta(self) -> None:
        html = """
        <html><body>
        <div class="card">
          <div class="card-body">
            <h5>Audio Systems Engineer</h5>
            <h6>Based in San Jose, CA</h6>
          </div>
          <div class="card-footer">
            <a class="btn" href="/audio_systems_engineer">Learn More</a>
          </div>
        </div>
        </body></html>
        """
        jobs = extract_job_links(html, "https://example.com/careers")
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].title, "Audio Systems Engineer")
        self.assertEqual(jobs[0].url, "https://example.com/audio_systems_engineer")

    def test_card_heading_not_applied_with_multiple_job_anchors(self) -> None:
        html = """
        <html><body>
        <div class="card">
          <div class="card-body">
            <h5>Audio Systems Engineer</h5>
          </div>
          <div class="card-footer">
            <a class="btn" href="/audio_systems_engineer">Learn More</a>
            <a class="btn" href="/audio_systems_engineer/apply">Apply Now</a>
          </div>
        </div>
        </body></html>
        """
        jobs = extract_job_links(html, "https://example.com/careers")
        self.assertEqual(len(jobs), 0)

    def test_structural_title_still_rejected_when_furniture(self) -> None:
        html = """
        <html><body>
        <div class="card">
          <div class="card-body">
            <h5>Benefits</h5>
          </div>
          <div class="card-footer">
            <a class="btn" href="/benefits-overview">Learn More</a>
          </div>
        </div>
        </body></html>
        """
        jobs = extract_job_links(html, "https://example.com/careers")
        self.assertEqual(len(jobs), 0)

    def test_structural_fallback_does_not_fire_without_job_hint_page(self) -> None:
        html = """
        <html><body>
        <div class="card">
          <div class="card-body">
            <h5>Audio Systems Engineer</h5>
            <h6>Based in San Jose, CA</h6>
          </div>
          <div class="card-footer">
            <a class="btn" href="/audio_systems_engineer">Learn More</a>
          </div>
        </div>
        </body></html>
        """
        jobs = extract_job_links(html, "https://example.com/company")
        self.assertEqual(len(jobs), 0)

    def test_flat_text_already_good_title_is_unchanged(self) -> None:
        html = """
        <html><body>
        <a href="/careers/senior-audio-engineer-9911">Senior Audio Engineer</a>
        </body></html>
        """
        jobs = extract_job_links(html, "https://example.com/careers")
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].title, "Senior Audio Engineer")


class TestCookieBannerRejected(unittest.TestCase):
    def test_cookie_notice_is_not_a_job_title(self) -> None:
        html = """
        <div class="cookie-bar">
          <h4>This website uses cookies to ensure you get the best experience.</h4>
          <a href="/careers/privacy-and-cookies">Learn More</a>
        </div>
        """
        jobs = extract_jobs(html, "https://example.com/careers")
        self.assertEqual(jobs, [])

    def test_cookie_preferences_link_is_not_a_job_title(self) -> None:
        html = """
        <div class="cookie-bar">
          <h4>Select which cookies you accept</h4>
          <a href="/careers/cookie-preferences">Learn More</a>
        </div>
        """
        jobs = extract_jobs(html, "https://example.com/careers")
        self.assertEqual(jobs, [])


JSONLD_LIST_LOCATION = """
<html><body><script type="application/ld+json">
{"@type": "JobPosting", "title": "Audio Test Engineer",
 "url": "https://example.com/jobs/1",
 "jobLocation": [{"@type": "Place", "address": {"@type": "PostalAddress",
   "addressLocality": "Ciudad Juarez", "addressRegion": "CHH",
   "addressCountry": "MX", "postalCode": "UNAVAILABLE"}}]}
</script></body></html>
"""

JSONLD_TWO_LOCATIONS = """
<html><body><script type="application/ld+json">
{"@type": "JobPosting", "title": "Audio Test Engineer",
 "url": "https://example.com/jobs/1",
 "jobLocation": [
   {"@type": "Place", "address": {"@type": "PostalAddress",
     "addressLocality": "Skokie", "addressRegion": "IL", "addressCountry": "US"}},
   {"@type": "Place", "address": {"@type": "PostalAddress",
     "addressLocality": "Edinburgh", "addressRegion": "UNAVAILABLE",
     "addressCountry": "UK"}}]}
</script></body></html>
"""


class TestJsonLdListLocations(unittest.TestCase):
    def test_a_single_entry_list_is_unwrapped(self) -> None:
        jobs = extract_jsonld_jobs(JSONLD_LIST_LOCATION, "https://example.com/jobs")
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].location, "Ciudad Juarez, CHH, MX")

    def test_unavailable_placeholders_are_dropped(self) -> None:
        jobs = extract_jsonld_jobs(JSONLD_TWO_LOCATIONS, "https://example.com/jobs")
        self.assertIn("Edinburgh, UK", jobs[0].location or "")
        self.assertNotIn("UNAVAILABLE", jobs[0].location or "")

    def test_several_places_are_joined(self) -> None:
        jobs = extract_jsonld_jobs(JSONLD_TWO_LOCATIONS, "https://example.com/jobs")
        self.assertEqual(jobs[0].location, "Skokie, IL, US; Edinburgh, UK")


BASE_TAG_HTML = """
<html><head><base href="https://example.com/about/careers/applications/"></head>
<body>
<a href="jobs/results/12345-audio-dsp-engineer">Audio DSP Engineer</a>
</body></html>
"""

RELATIVE_BASE_HTML = """
<html><head><base href="../"></head>
<body><a href="jobs/results/12345-audio-dsp-engineer">Audio DSP Engineer</a></body>
</html>
"""

BAD_BASE_HTML = """
<html><head><base href="javascript:void(0)"></head>
<body><a href="jobs/12345-audio-dsp-engineer">Audio DSP Engineer</a></body>
</html>
"""


class TestDocumentBaseTag(unittest.TestCase):
    def test_relative_hrefs_resolve_against_the_base_tag(self) -> None:
        jobs = extract_job_links(
            BASE_TAG_HTML,
            "https://example.com/about/careers/applications/jobs/results/?q=audio",
        )
        self.assertEqual(len(jobs), 1)
        self.assertEqual(
            jobs[0].url,
            "https://example.com/about/careers/applications"
            "/jobs/results/12345-audio-dsp-engineer",
        )

    def test_a_relative_base_is_resolved_against_the_page(self) -> None:
        jobs = extract_job_links(
            RELATIVE_BASE_HTML, "https://example.com/careers/listing/?q=audio"
        )
        self.assertEqual(
            jobs[0].url, "https://example.com/careers/jobs/results/12345-audio-dsp-engineer"
        )

    def test_a_non_http_base_is_ignored(self) -> None:
        jobs = extract_job_links(BAD_BASE_HTML, "https://example.com/careers/")
        self.assertEqual(
            jobs[0].url, "https://example.com/careers/jobs/12345-audio-dsp-engineer"
        )

    def test_pages_without_a_base_tag_are_unchanged(self) -> None:
        html = (
            "<html><body>"
            '<a href="jobs/12345-audio-dsp-engineer">Audio DSP Engineer</a>'
            "</body></html>"
        )
        jobs = extract_job_links(html, "https://example.com/careers/")
        self.assertEqual(
            jobs[0].url, "https://example.com/careers/jobs/12345-audio-dsp-engineer"
        )


class TestPaginationControlRejected(unittest.TestCase):
    def test_next_with_chevrons_rejected(self) -> None:
        self.assertTrue(is_furniture_title("Next >>"))

    def test_bare_next_rejected(self) -> None:
        self.assertTrue(is_furniture_title("next"))

    def test_double_chevron_previous_rejected(self) -> None:
        self.assertTrue(is_furniture_title("<< Previous"))

    def test_bare_guillemet_rejected(self) -> None:
        self.assertTrue(is_furniture_title("»"))

    def test_page_number_rejected(self) -> None:
        self.assertTrue(is_furniture_title("Page 2"))

    def test_bare_number_rejected(self) -> None:
        self.assertTrue(is_furniture_title("3"))

    def test_bare_last_rejected(self) -> None:
        self.assertTrue(is_furniture_title("Last"))

    def test_nextjs_engineer_not_rejected(self) -> None:
        self.assertFalse(is_furniture_title("Next.js Engineer"))

    def test_first_officer_not_rejected(self) -> None:
        self.assertFalse(is_furniture_title("First Officer"))

    def test_last_mile_operations_manager_not_rejected(self) -> None:
        self.assertFalse(is_furniture_title("Last Mile Operations Manager"))

    def test_page_layout_designer_not_rejected(self) -> None:
        self.assertFalse(is_furniture_title("Page Layout Designer"))

    def test_senior_audio_engineer_not_rejected(self) -> None:
        self.assertFalse(is_furniture_title("Senior Audio Engineer"))


SAME_PAGE_ANCHOR_HTML = """
<html><body>
<a href="#pagetop">^top^</a>
<div id="pagetop"></div>
<a href="#featured">FEATURED</a>
<div id="featured"></div>
<a href="#">PRODUCTS</a>
<a href="#it_firmware_engineer_20200529">Firmware Engineer</a>
<a name="it_firmware_engineer_20200529"></a>
<a href="#it_yocto_ambedded_developer_20251031">Yocto Embedded Developer</a>
<a name="it_yocto_ambedded_developer_20251031"></a>
</body></html>
"""


class TestSamePageAnchorJobs(unittest.TestCase):
    def test_named_anchor_jobs_extracted_and_chrome_excluded(self) -> None:
        jobs = extract_job_links(
            SAME_PAGE_ANCHOR_HTML, "https://www.ikmultimedia.com/careers/"
        )
        titles = sorted(job.title for job in jobs)
        self.assertEqual(titles, ["Firmware Engineer", "Yocto Embedded Developer"])
        urls = sorted(job.url for job in jobs)
        self.assertEqual(
            urls,
            [
                "https://www.ikmultimedia.com/careers/"
                "#it_firmware_engineer_20200529",
                "https://www.ikmultimedia.com/careers/"
                "#it_yocto_ambedded_developer_20251031",
            ],
        )

    def test_named_anchor_ignored_without_page_job_hint(self) -> None:
        html = """
        <html><body>
        <a href="#accountant-role">Accountant</a>
        <a name="accountant-role"></a>
        </body></html>
        """
        jobs = extract_job_links(html, "https://example.com/about/")
        self.assertEqual(jobs, [])

    def test_ordinary_self_link_without_fragment_still_dropped(self) -> None:
        html = '<html><body><a href="/careers/">Careers</a></body></html>'
        jobs = extract_job_links(html, "https://example.com/careers/")
        self.assertEqual(jobs, [])


class TestBoardChromeRejected(unittest.TestCase):
    def test_search_jobs_rejected(self) -> None:
        self.assertIn("search jobs", NON_JOB_TEXT)

    def test_jobs_and_career_rejected(self) -> None:
        self.assertIn("jobs & career", NON_JOB_TEXT)

    def test_sign_up_for_job_alerts_with_period_rejected(self) -> None:
        self.assertIn("sign up for job alerts.", NON_JOB_TEXT)

    def test_sign_up_for_job_alerts_without_period_rejected(self) -> None:
        self.assertIn("sign up for job alerts", NON_JOB_TEXT)

    def test_powered_by_jobvite_rejected(self) -> None:
        self.assertIn("powered by jobvite", NON_JOB_TEXT)

    def test_job_alerts_rejected(self) -> None:
        self.assertIn("job alerts", NON_JOB_TEXT)

    def test_pagination_and_chrome_anchors_excluded_alongside_real_job(self) -> None:
        html = """
        <html><body>
        <a href="/careers/senior-audio-engineer-4471">Senior Audio Engineer</a>
        <a href="/careers?page=2">Next &gt;&gt;</a>
        <a href="/careers/search">Search jobs</a>
        <a href="/careers/alerts">Sign up for Job Alerts.</a>
        <a href="https://www.jobvite.com/">Powered by Jobvite</a>
        </body></html>
        """
        jobs = extract_job_links(html, "https://example.com/careers")
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].title, "Senior Audio Engineer")


ACCORDION_HTML = """
<html><body>
<details id="#ee-audio">
  <summary class="e-n-accordion-item-title">
    Senior Application Engineer &ndash; EE / Audio, Santa Clara
  </summary>
  <p>We are looking for a Senior Application Engineer to join our EE/Audio team
  in Santa Clara. You will design and validate <a href="/audio-hardware">audio hardware</a>.</p>
</details>
<details id="e-n-accordion-item-1154">
  <summary class="e-n-accordion-item-title">West Coast Sales Director, Santa Clara</summary>
  <p>Lead our west coast sales team from our Santa Clara office and drive
  revenue growth across the region.</p>
</details>
<details id="faq-1">
  <summary class="e-n-accordion-item-title">What benefits do you offer?</summary>
  <p>We offer health insurance, a 401k match, and unlimited PTO.</p>
</details>
</body></html>
"""


class TestAccordionExtraction(unittest.TestCase):
    def test_only_job_titles_are_returned_with_single_hash_urls(self) -> None:
        jobs = extract_accordion_jobs(ACCORDION_HTML, "https://xmems.com/careers/")
        titles = [job.title for job in jobs]
        self.assertEqual(len(jobs), 2)
        self.assertIn("Senior Application Engineer – EE / Audio, Santa Clara", titles)
        self.assertIn("West Coast Sales Director, Santa Clara", titles)
        self.assertNotIn("What benefits do you offer?", titles)

        urls = {job.title: job.url for job in jobs}
        self.assertEqual(
            urls["Senior Application Engineer – EE / Audio, Santa Clara"],
            "https://xmems.com/careers/#ee-audio",
        )
        self.assertEqual(
            urls["West Coast Sales Director, Santa Clara"],
            "https://xmems.com/careers/#e-n-accordion-item-1154",
        )

    def test_descriptions_are_populated_and_omit_the_title(self) -> None:
        jobs = extract_accordion_jobs(ACCORDION_HTML, "https://xmems.com/careers/")
        for job in jobs:
            self.assertTrue(job.description)
            assert job.description is not None
            self.assertFalse(job.description.startswith(job.title))

    def test_details_without_id_is_skipped(self) -> None:
        html = """
        <html><body>
        <details>
          <summary>Audio Firmware Engineer, Remote</summary>
          <p>Build firmware for our next-generation audio products.</p>
        </details>
        </body></html>
        """
        jobs = extract_accordion_jobs(html, "https://xmems.com/careers/")
        self.assertEqual(jobs, [])

    def test_base_url_without_job_hint_returns_empty(self) -> None:
        jobs = extract_accordion_jobs(ACCORDION_HTML, "https://xmems.com/about/")
        self.assertEqual(jobs, [])

    def test_details_inside_nav_is_skipped_but_identical_item_outside_is_kept(
        self,
    ) -> None:
        html = """
        <html><body>
        <nav>
        <details id="nav-audio-engineer">
          <summary>Audio Firmware Engineer, Remote</summary>
          <p>Build firmware for our next-generation audio products.</p>
        </details>
        </nav>
        <details id="audio-engineer">
          <summary>Audio Firmware Engineer, Remote</summary>
          <p>Build firmware for our next-generation audio products.</p>
        </details>
        </body></html>
        """
        jobs = extract_accordion_jobs(html, "https://example.com/careers/")
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].url, "https://example.com/careers/#audio-engineer")

    def test_details_with_mostly_link_text_body_is_skipped(self) -> None:
        html = """
        <html><body>
        <details id="home-audio">
          <summary>Home Audio</summary>
          <ul>
            <li><a href="/collections/turntables">Turntables</a></li>
            <li><a href="/collections/vinyl-records">Vinyl Records</a></li>
            <li><a href="/collections/cases">Cases</a></li>
            <li><a href="/collections/accessories">Accessories</a></li>
          </ul>
        </details>
        </body></html>
        """
        jobs = extract_accordion_jobs(html, "https://example.com/careers/")
        self.assertEqual(jobs, [])


class TestLinkedInExcluded(unittest.TestCase):
    def test_linkedin_job_view_link_rejected(self) -> None:
        html = """
        <html><body>
        <a href="https://www.linkedin.com/jobs/view/4459438450/">Careers on LinkedIn</a>
        </body></html>
        """
        jobs = extract_job_links(html, "https://example.com/careers")
        self.assertEqual(jobs, [])

    def test_linkedin_company_jobs_link_rejected(self) -> None:
        html = """
        <html><body>
        <a href="https://www.linkedin.com/company/acme/jobs/">See Open Roles</a>
        </body></html>
        """
        jobs = extract_job_links(html, "https://example.com/careers")
        self.assertEqual(jobs, [])

    def test_onsite_job_link_still_extracted_beside_linkedin_link(self) -> None:
        html = """
        <html><body>
        <a href="/careers/senior-audio-engineer-4471">Senior Audio Engineer</a>
        <a href="https://www.linkedin.com/jobs/view/4459438450/">Careers on LinkedIn</a>
        </body></html>
        """
        jobs = extract_job_links(html, "https://example.com/careers")
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].title, "Senior Audio Engineer")


class TestNonEnglishFurnitureText(unittest.TestCase):
    def test_french_read_more_falls_back_to_heading(self) -> None:
        html = """
        <html><body>
        <div class="card">
          <div class="card-body">
            <h3>Ingénieur Electronique R&amp;D (F/H)</h3>
          </div>
          <div class="card-footer">
            <a class="btn" href="/careers/ingenieur-electronique-rd-77213">lire la suite</a>
          </div>
        </div>
        </body></html>
        """
        jobs = extract_job_links(html, "https://www.focal.com/fr/recrutement")
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].title, "Ingénieur Electronique R&D (F/H)")


class TestLanguageSwitcherRejected(unittest.TestCase):
    def test_bare_language_endonyms_rejected(self) -> None:
        self.assertTrue(is_furniture_title("Deutsch"))
        self.assertTrue(is_furniture_title("Español - ES"))
        self.assertTrue(is_furniture_title("Čeština, český jazyk"))

    def test_real_job_titles_not_rejected(self) -> None:
        self.assertFalse(is_furniture_title("Audio DSP Engineer"))
        self.assertFalse(is_furniture_title("Senior Sound Designer"))


if __name__ == "__main__":
    unittest.main()
