from __future__ import annotations

import unittest

from scraper.normalizer import SCOPE_THRESHOLDS, category_to_scope, score_relevance


class TestCategoryScope(unittest.TestCase):
    def test_conglomerates_are_partial(self) -> None:
        cats = (
            "Automotive OEMs",
            "Consumer Electronics & Tech",
            "Audio Retailers & Distributors",
        )
        for cat in cats:
            self.assertEqual(category_to_scope(cat), "partial", cat)

    def test_audio_native_categories(self) -> None:
        for cat in (
            "Recording Studios & Post Houses",
            "Professional Audio & Live Sound",
            "Headphones & Personal Audio",
            "Transducer & Driver Manufacturers",
            "Audio Semiconductors",
        ):
            self.assertEqual(category_to_scope(cat), "native", cat)


class TestAgencyScope(unittest.TestCase):
    def test_staffing_agencies_get_the_strictest_scope(self) -> None:
        self.assertEqual(category_to_scope("Staffing & Recruiting Agencies"), "all")

    def test_agency_does_not_vouch_for_a_neutral_title(self) -> None:
        description = (
            "You will work on our audio subsystem, tuning DSP pipelines and "
            "acoustic performance. Requirements: audio codecs, microphone "
            "arrays and loudspeaker characterisation."
        )
        _, native = score_relevance("Software Engineer", description, ["dsp"], "native")
        _, agency = score_relevance("Software Engineer", description, ["dsp"], "all")
        self.assertTrue(native)
        self.assertFalse(agency)

    def test_agency_still_surfaces_an_explicitly_audio_title(self) -> None:
        _, related = score_relevance(
            "Electrical Audio Engineer", None, ["audio_systems"], "all"
        )
        self.assertTrue(related)


class TestScoreRelevance(unittest.TestCase):
    def test_audio_role_at_conglomerate_passes(self) -> None:
        score, related = score_relevance(
            "Senior DSP Engineer",
            "Design audio signal processing algorithms and filters.",
            ["audio_dsp"],
            "partial",
        )
        self.assertTrue(related)
        self.assertGreaterEqual(score, 50)

    def test_corporate_role_at_conglomerate_hidden(self) -> None:
        score, related = score_relevance(
            "Senior FP&A Analyst",
            "Build financial models and run the monthly close.",
            [],
            "partial",
        )
        self.assertFalse(related)

    def test_generic_role_at_conglomerate_hidden(self) -> None:
        _, related = score_relevance(
            "National Help Desk Engineer", "Provide IT support to employees.", [], "partial"
        )
        self.assertFalse(related)

    def test_noncorporate_role_at_native_company_passes(self) -> None:
        _, related = score_relevance(
            "Studio Manager",
            "Manage recording studio operations and audio equipment.",
            [],
            "native",
        )
        self.assertTrue(related)

    def test_noncorporate_role_at_native_company_no_desc_hidden(self) -> None:
        _, related = score_relevance("Studio Manager", None, [], "native")
        self.assertFalse(related)

    def test_back_office_role_at_native_company_hidden(self) -> None:
        boilerplate = (
            "Shure is a leading audio company. Our microphones and wireless "
            "audio systems are used worldwide. We build audio products."
        )
        for title in (
            "Senior Credit Collections Specialist",
            "Associate Director, Trade Compliance",
            "Buyer I, Tactical",
            "Auditor, Incoming Inspection",
            "Senior Incentive Plan Administrator",
        ):
            _, related = score_relevance(title, boilerplate, [], "native")
            self.assertFalse(related, title)

    def test_technical_role_admitted_on_company_context_alone(self) -> None:
        boilerplate = (
            "Shure is a leading audio company. Our microphones and wireless "
            "audio systems are used worldwide. We build audio products."
        )
        for title in (
            "Senior Systems Engineer",
            "Sr. NPI Engineer",
            "Engineer Sr, Metrology",
            "Senior Process Engineer",
        ):
            _, related = score_relevance(title, boilerplate, [], "native")
            self.assertTrue(related, title)

    def test_corporate_role_at_native_company_hidden(self) -> None:
        _, related = score_relevance("Human Resources", None, [], "native")
        self.assertFalse(related)

    def test_weak_title_with_categories_passes_partial(self) -> None:
        _, related = score_relevance(
            "Studio Coordinator", None, ["music_production_recording"], "partial"
        )
        self.assertTrue(related)

    def test_photo_editor_at_partial_licenser_hidden(self) -> None:
        _, related = score_relevance("Senior Photo Editor, Sport", None, [], "partial")
        self.assertFalse(related)

    def test_description_signals_help(self) -> None:
        _, related = score_relevance(
            "Acoustics Researcher", None, [], "partial"
        )
        self.assertTrue(related)

    def test_university_lecturer_at_native_company_hidden(self) -> None:
        _, related = score_relevance(
            "Lecturer - Department of English Writing",
            "Teach undergraduate writing courses and evaluate student work.",
            [],
            "native",
        )
        self.assertFalse(related)

    def test_plumber_at_native_company_hidden(self) -> None:
        _, related = score_relevance(
            "Plumber (Downtown)",
            "Repair plumbing fixtures and pipes across campus buildings.",
            [],
            "native",
        )
        self.assertFalse(related)

    def test_network_engineer_at_partial_company_hidden(self) -> None:
        _, related = score_relevance(
            "Network Engineer / Linux Administrator",
            "Maintain network infrastructure and Linux servers for cloud communications platform.",
            [],
            "partial",
        )
        self.assertFalse(related)

    def test_revenue_manager_at_partial_company_hidden(self) -> None:
        _, related = score_relevance(
            "Revenue Manager",
            "Own revenue recognition and monthly close processes.",
            [],
            "partial",
        )
        self.assertFalse(related)

    def test_strong_audio_role_at_partial_passes(self) -> None:
        _, related = score_relevance(
            "Senior DSP Engineer",
            "Design audio signal processing algorithms for noise cancellation.",
            ["audio_dsp_embedded"],
            "partial",
        )
        self.assertTrue(related)

    def test_corporate_role_exempted_by_strong_audio_title(self) -> None:
        _, related = score_relevance("Audio Project Manager", None, [], "native")
        self.assertTrue(related)

    def test_studio_leader_at_architecture_firm_not_related(self) -> None:
        desc = (
            "DLR Group is an integrated design firm delivering architecture, "
            "engineering, interiors, and planning for clients nationwide. "
            "About K-12 Education at DLR Group: our team of architects, "
            "engineers, and interior designers draw from evidence-based design "
            "to help schools improve outcomes for students. Position Summary: "
            "as a Studio Leader you will lead business development and manage "
            "client relationships across our K-12 Education practice."
        )
        _, related = score_relevance(
            "Studio Leader, K-12 Education", desc, [], "native"
        )
        self.assertFalse(related)

    def test_decagon_account_executive_is_not_audio_related(self) -> None:
        """Decagon is a native-scope voice AI company that posts 13 rows to
        the board. Nine of them are sales and recruiting titles with no
        audio signal at all; Enterprise Account Executive is five of those
        nine, and without this pattern each one clears the native threshold
        on job-category and native-bonus points alone."""
        score, related = score_relevance(
            "Enterprise Account Executive",
            "Own the full sales cycle from prospecting to close.",
            ["voice_ai"],
            "native",
        )
        self.assertFalse(related)
        self.assertLess(score, SCOPE_THRESHOLDS["native"])

    def test_decagon_director_of_sales_is_not_audio_related(self) -> None:
        """Decagon posts Director of Sales, Enterprise three times among its
        nine sales and recruiting rows; nothing in the title or a generic
        sales description mentions audio."""
        score, related = score_relevance(
            "Director of Sales, Enterprise",
            "Lead and scale our enterprise go-to-market sales team.",
            ["voice_ai"],
            "native",
        )
        self.assertFalse(related)
        self.assertLess(score, SCOPE_THRESHOLDS["native"])

    def test_decagon_recruiting_coordinator_is_not_audio_related(self) -> None:
        """The ninth of Decagon's nine non-audio rows, Go to Market
        Recruiting Coordinator, is a recruiting title riding the native
        bonus with no audio content anywhere in the posting."""
        score, related = score_relevance(
            "Go to Market Recruiting Coordinator",
            "Coordinate interviews and offers for our go-to-market org.",
            ["voice_ai"],
            "native",
        )
        self.assertFalse(related)
        self.assertLess(score, SCOPE_THRESHOLDS["native"])

    def test_sweetwater_sound_director_of_sales_home_audio_stays_related(self) -> None:
        """Sweetwater Sound's Director of Sales - Home Audio matches the new
        sales terms, but the title itself is strong audio, and the -70
        corporate penalty is gated on `not title_strong` precisely so a
        genuine audio sales role keeps its place."""
        _, related = score_relevance(
            "Director of Sales - Home Audio",
            "Lead the home audio sales team and channel partnerships.",
            ["home_audio"],
            "partial",
        )
        self.assertTrue(related)

    def test_iheartradio_audio_and_digital_account_executive_stays_related(self) -> None:
        """iHeartRadio's Audio and Digital Account Executive matches the new
        account executive term, but its strong audio title trips the same
        `not title_strong` gate and survives."""
        _, related = score_relevance(
            "Audio and Digital Account Executive",
            "Sell audio and digital advertising campaigns to local clients.",
            ["radio_advertising"],
            "partial",
        )
        self.assertTrue(related)

    def test_decagon_engineering_role_is_unaffected(self) -> None:
        """Decagon's four genuine engineering rows, like Staff Software
        Engineer, Voice Agent, carry no sales or recruiting terms at all and
        are untouched by this pattern."""
        _, related = score_relevance(
            "Staff Software Engineer, Voice Agent",
            "Build the voice agent platform powering real-time conversations.",
            ["voice_ai"],
            "native",
        )
        self.assertTrue(related)


class TestTalentPoolTitles(unittest.TestCase):
    def test_ramboll_rail_power_supply_is_a_pipeline_ad(self) -> None:
        """Ramboll Group publishes this exact title 13 times across Danish and
        Swedish offices with distinct locations, external_ids and URLs. It is
        one pipeline advertisement duplicated into 13 board rows, not 13 jobs."""
        score, related = score_relevance(
            "Ramboll is growing its Rail Power Supply team!",
            None,
            ["audio_ee"],
            "partial",
        )
        self.assertEqual(score, 0)
        self.assertFalse(related)

    def test_ramboll_title_case_variant_is_caught(self) -> None:
        _, related = score_relevance(
            "Ramboll Is Growing Its Data Centre Projects Team in Germany",
            None,
            [],
            "partial",
        )
        self.assertFalse(related)

    def test_demant_talent_pool_is_caught(self) -> None:
        _, related = score_relevance(
            "Clinicians - Audika's Talent pool", None, [], "native"
        )
        self.assertFalse(related)

    def test_join_our_talent_community_is_caught(self) -> None:
        _, related = score_relevance(
            "Join our Talent Community", None, [], "native"
        )
        self.assertFalse(related)

    def test_starkey_future_opportunities_is_not_caught_as_talent_pool(self) -> None:
        """"Future opportunities" is deliberately not treated as talent-pool
        phrasing on its own -- TALENT_POOL_TITLE still lets this Starkey
        title through. But "Hearing Instrument Specialist" is a genuine
        dispensing role (the description trains people to fit hearing aids
        for patients in clinic), so the clinical-hearing-title filter now
        correctly removes it from the board instead."""
        _, related = score_relevance(
            "Hearing Instrument Specialist Trainee - Future Opportunities",
            "Train alongside licensed hearing instrument specialists fitting "
            "hearing aids and supporting patients in clinic.",
            ["audio_hearing"],
            "native",
        )
        self.assertFalse(related)

    def test_normal_title_with_team_still_scores_normally(self) -> None:
        _, related = score_relevance(
            "Audio Team Lead",
            "Lead the audio engineering team building loudspeaker products.",
            ["audio_systems"],
            "native",
        )
        self.assertTrue(related)


class TestClinicalHearingTitles(unittest.TestCase):
    def test_beltone_hearing_care_professional_is_dispensing_not_audio(self) -> None:
        """Beltone posts this exact title 31 times on the board; it is
        retail hearing-aid dispensing staffing, not engineering."""
        score, related = score_relevance(
            "Hearing Care Professional -- Licensed", None, [], "native"
        )
        self.assertEqual(score, 0)
        self.assertFalse(related)

    def test_beltone_town_variant_audiologist_title_is_dispensing(self) -> None:
        """Beltone posts town-by-town variants of this title across the
        board; "Gilbert, AZ" is one storefront among dozens."""
        _, related = score_relevance(
            "Audiologist or Hearing Instrument Specialist (Gilbert, AZ)",
            None,
            [],
            "native",
        )
        self.assertFalse(related)

    def test_demant_audioprothesiste_is_dispensing_not_audio(self) -> None:
        """"Audioprothésiste" is the French hearing-aid dispensing title;
        it is 22 board rows across Demant and Advanced Bionics."""
        _, related = score_relevance(
            "Audioprothésiste - Auxerre et alentours (89)", None, [], "native"
        )
        self.assertFalse(related)

    def test_spanish_audiologia_receptionist_is_dispensing_not_audio(self) -> None:
        _, related = score_relevance(
            "Auxiliar de Audiología / Recepcionista Sevilla", None, [], "native"
        )
        self.assertFalse(related)

    def test_demant_clinician_is_dispensing_not_audio(self) -> None:
        """Demant posts this title for clinical roles in Australia and
        New Zealand; it is 6 board rows."""
        _, related = score_relevance("Clinician, Langwarrin", None, [], "native")
        self.assertFalse(related)

    def test_embedded_audio_dsp_engineer_at_native_hearing_company_survives(
        self,
    ) -> None:
        _, related = score_relevance(
            "Embedded Audio DSP Engineer", None, ["audio_dsp_embedded"], "native"
        )
        self.assertTrue(related)

    def test_audiological_engineer_survives_via_engineering_exemption(self) -> None:
        """"Audiological Engineer" never matches CLINICAL_HEARING_TITLE at
        all -- the vocabulary is deliberately narrow -- but the engineering
        exemption exists precisely so a future clinical-shaped match on a
        title like this one is not dropped."""
        _, related = score_relevance(
            "Audiological Engineer", None, ["audio_ee"], "native"
        )
        self.assertTrue(related)

    def test_research_audiology_intern_survives(self) -> None:
        _, related = score_relevance(
            "Research Audiology Intern", None, ["audio_hearing"], "native"
        )
        self.assertTrue(related)

    def test_audio_technician_is_not_confused_with_audiology_technician(self) -> None:
        """"Audio Technician (Covington, WA)" is a Starkey engineering role;
        it must not be caught by the "audiology technician" branch of
        CLINICAL_HEARING_TITLE."""
        _, related = score_relevance(
            "Audio Technician (Covington, WA)", None, ["audio_dsp_embedded"], "native"
        )
        self.assertTrue(related)


if __name__ == "__main__":
    unittest.main()
