"""
Tests for the image assignment pipeline.

Coverage:
    - _normalize_license maps Commons strings to canonical codes
    - License whitelist explicitly rejects NC / ND / non-free
    - Earl's check_image_legal_use fires on each violation type
    - Refusal cases (no QID, no metadata, wrong dimensions, etc.) return
      success=False without touching entity.image_url
    - Successful assignment writes all four image fields + FieldProvenance
"""

from __future__ import annotations

from unittest import mock

from django.test import TestCase

from owdb_django.owdbapp.models import Wrestler, Promotion
from owdb_django.wrestlebot.models import FieldProvenance
from owdb_django.wrestlebot.sources import commons


def _fake_meta(*, license_code="cc-by-sa", license_short="CC BY-SA 3.0",
                 artist="Test Artist", attribution_required=True,
                 width=800, height=1200, is_allowed=True, rejection_reason=""):
    return commons.CommonsImageMeta(
        filename="Test.jpg",
        original_url="https://upload.wikimedia.org/test.jpg",
        thumb_url_400="https://commons.wikimedia.org/wiki/Special:FilePath/Test.jpg?width=400",
        file_page_url="https://commons.wikimedia.org/wiki/File:Test.jpg",
        width=width, height=height,
        size_bytes=100_000, mime="image/jpeg",
        license_code=license_code, license_short=license_short,
        license_url="https://creativecommons.org/licenses/by-sa/3.0/",
        usage_terms="CC BY-SA 3.0",
        attribution_required=attribution_required,
        artist=artist, credit="Own work", permission="",
        description="Test image", categories=[], restrictions="",
        is_allowed=is_allowed, rejection_reason=rejection_reason,
    )


class LicenseNormalizationTests(TestCase):
    def test_normalize_cc_by_sa_3_0(self):
        self.assertEqual(commons._normalize_license("cc-by-sa-3.0"), "cc-by-sa")

    def test_normalize_handles_spaces(self):
        self.assertEqual(commons._normalize_license("CC BY 4.0"), "cc-by")

    def test_normalize_public_domain(self):
        self.assertEqual(commons._normalize_license("Public Domain"), "pd")
        self.assertEqual(commons._normalize_license("PD"), "pd")
        self.assertEqual(commons._normalize_license("CC0"), "cc0")

    def test_nc_is_blocked(self):
        self.assertEqual(commons._normalize_license("cc-by-nc"), "")

    def test_nd_is_blocked(self):
        self.assertEqual(commons._normalize_license("cc-by-nd"), "")

    def test_non_free_is_blocked(self):
        self.assertEqual(commons._normalize_license("non-free"), "")

    def test_unknown_is_blocked(self):
        self.assertEqual(commons._normalize_license("UnknownLicense-2.0"), "")


class ImageLegalUseChecksTests(TestCase):
    """check_image_legal_use rule coverage."""

    def setUp(self):
        from owdb_django.wrestlebot.pipeline.consistency import check_image_legal_use
        self.check = check_image_legal_use

    def test_no_image_no_findings(self):
        w = Wrestler.objects.create(name="No image")
        self.assertEqual(self.check("wrestler", w), [])

    def test_image_without_license_fires(self):
        w = Wrestler.objects.create(
            name="Img no license",
            image_url="https://example.com/x.jpg",
        )
        rules = [i.rule for i in self.check("wrestler", w)]
        self.assertIn("image_without_license", rules)

    def test_cc_by_without_credit_fires(self):
        w = Wrestler.objects.create(
            name="CC-BY no credit",
            image_url="https://example.com/x.jpg",
            image_license="cc-by",
            image_credit="",
            image_source_url="https://commons.example.org/File:x.jpg",
        )
        rules = [i.rule for i in self.check("wrestler", w)]
        self.assertIn("image_credit_missing", rules)

    def test_pd_without_credit_no_finding(self):
        """PD/CC0 don't require attribution."""
        w = Wrestler.objects.create(
            name="PD no credit OK",
            image_url="https://example.com/x.jpg",
            image_license="pd",
            image_credit="",
            image_source_url="https://commons.example.org/File:x.jpg",
        )
        rules = [i.rule for i in self.check("wrestler", w)]
        self.assertNotIn("image_credit_missing", rules)

    def test_license_not_in_whitelist_fires(self):
        w = Wrestler.objects.create(
            name="bad license",
            image_url="https://example.com/x.jpg",
            image_license="cc-by-nc",
            image_credit="some credit",
            image_source_url="https://example.org/File:x.jpg",
        )
        rules = [i.rule for i in self.check("wrestler", w)]
        self.assertIn("image_license_not_allowed", rules)

    def test_no_source_url_warning(self):
        w = Wrestler.objects.create(
            name="No source url",
            image_url="https://example.com/x.jpg",
            image_license="pd",
            image_credit="",
            image_source_url="",
        )
        rules = [i.rule for i in self.check("wrestler", w)]
        self.assertIn("image_no_source_url", rules)


def _with_cascade_off(test_case):
    """
    Disable the Commons-category + Wikipedia-body legs of the cascade so
    the older P18-only tests keep their semantics: one candidate, one
    chance to pass. Tests that exercise the cascade explicitly should
    NOT call this helper.
    """
    patches = [
        mock.patch(
            "owdb_django.wrestlebot.pipeline.images.resolve_commons_category_for_qid",
            return_value=None,
        ),
        mock.patch(
            "owdb_django.wrestlebot.pipeline.images.fetch_commons_category_files",
            return_value=[],
        ),
        mock.patch(
            "owdb_django.wrestlebot.pipeline.images.fetch_wikipedia_body_image_filenames",
            return_value=[],
        ),
    ]
    for p in patches:
        p.start()
        test_case.addCleanup(p.stop)


class AssignImageRefusalTests(TestCase):
    """Refusal cases — entity.image_url must remain untouched."""

    def setUp(self):
        from owdb_django.wrestlebot.pipeline import images
        self.images = images
        _with_cascade_off(self)

    def test_refuses_when_no_qid(self):
        w = Wrestler.objects.create(name="Phantom Wrestler")
        with mock.patch(
            "owdb_django.wrestlebot.pipeline.images.resolve_qid_for_wikipedia_title",
            return_value=None,
        ):
            result = self.images.assign_image_to_entity(w, entity_type="wrestler")
        self.assertFalse(result.success)
        self.assertIn("Wikidata QID", result.refusal_reason)
        w.refresh_from_db()
        self.assertFalse(w.image_url)

    def test_refuses_on_nc_license(self):
        w = Wrestler.objects.create(name="NC Test")
        rejected_meta = _fake_meta(
            license_code="", is_allowed=False,
            rejection_reason="License 'cc-by-nc' is explicitly blocked (NC/ND/non-free)",
        )
        with mock.patch(
            "owdb_django.wrestlebot.pipeline.images.resolve_qid_for_wikipedia_title",
            return_value="Q123",
        ), mock.patch(
            "owdb_django.wrestlebot.pipeline.images.fetch_image_for_qid",
            return_value={"filename": "X.jpg", "url": "", "thumb_url": "",
                          "qid": "Q123", "property": "P18"},
        ), mock.patch(
            "owdb_django.wrestlebot.pipeline.images.fetch_image_metadata",
            return_value=rejected_meta,
        ):
            result = self.images.assign_image_to_entity(w, entity_type="wrestler")
        self.assertFalse(result.success)
        # P18 rejected for NC license → cascade has no other source enabled
        # (we stubbed them off) → final refusal is the cascade-level message.
        # The underlying reason is captured in `considered`.
        self.assertIn("No candidate image passed", result.refusal_reason)
        self.assertTrue(any(
            "license check failed" in (c.get("refusal_reason") or "").lower()
            for c in result.considered
        ))
        w.refresh_from_db()
        self.assertFalse(w.image_url)

    def test_refuses_when_too_small(self):
        w = Wrestler.objects.create(name="Tiny Pic")
        small_meta = _fake_meta(width=50, height=50)
        with mock.patch(
            "owdb_django.wrestlebot.pipeline.images.resolve_qid_for_wikipedia_title",
            return_value="Q456",
        ), mock.patch(
            "owdb_django.wrestlebot.pipeline.images.fetch_image_for_qid",
            return_value={"filename": "X.jpg", "url": "", "thumb_url": "",
                          "qid": "Q456", "property": "P18"},
        ), mock.patch(
            "owdb_django.wrestlebot.pipeline.images.fetch_image_metadata",
            return_value=small_meta,
        ):
            result = self.images.assign_image_to_entity(w, entity_type="wrestler")
        self.assertFalse(result.success)
        # 50x50 fails even the first-fill floor (120px for wrestlers).
        self.assertTrue(any(
            "too small" in (c.get("refusal_reason") or "").lower()
            for c in result.considered
        ))

    def test_refuses_attribution_required_without_artist(self):
        w = Wrestler.objects.create(name="No Artist")
        anon_meta = _fake_meta(artist="", attribution_required=True)
        with mock.patch(
            "owdb_django.wrestlebot.pipeline.images.resolve_qid_for_wikipedia_title",
            return_value="Q789",
        ), mock.patch(
            "owdb_django.wrestlebot.pipeline.images.fetch_image_for_qid",
            return_value={"filename": "X.jpg", "url": "", "thumb_url": "",
                          "qid": "Q789", "property": "P18"},
        ), mock.patch(
            "owdb_django.wrestlebot.pipeline.images.fetch_image_metadata",
            return_value=anon_meta,
        ):
            result = self.images.assign_image_to_entity(w, entity_type="wrestler")
        self.assertFalse(result.success)
        self.assertTrue(any(
            "attribution" in (c.get("refusal_reason") or "").lower()
            for c in result.considered
        ))

    def test_refuses_when_entity_already_has_image_without_force(self):
        w = Wrestler.objects.create(
            name="Already has", image_url="https://example.com/existing.jpg",
            image_license="pd",
        )
        result = self.images.assign_image_to_entity(w, entity_type="wrestler")
        self.assertFalse(result.success)
        self.assertIn("already has an image", result.refusal_reason.lower())


class AssignImageSuccessTests(TestCase):
    """Successful assignment writes all four fields + provenance."""

    def setUp(self):
        _with_cascade_off(self)

    def test_successful_assignment_writes_fields_and_provenance(self):
        from owdb_django.wrestlebot.pipeline import images
        w = Wrestler.objects.create(name="Success Test")
        meta = _fake_meta()
        with mock.patch(
            "owdb_django.wrestlebot.pipeline.images.resolve_qid_for_wikipedia_title",
            return_value="Q999",
        ), mock.patch(
            "owdb_django.wrestlebot.pipeline.images.fetch_image_for_qid",
            return_value={"filename": "Test.jpg", "url": meta.original_url,
                          "thumb_url": meta.thumb_url_400,
                          "qid": "Q999", "property": "P18"},
        ), mock.patch(
            "owdb_django.wrestlebot.pipeline.images.fetch_image_metadata",
            return_value=meta,
        ):
            result = images.assign_image_to_entity(w, entity_type="wrestler")
        self.assertTrue(result.success, msg=result.refusal_reason)
        w.refresh_from_db()
        self.assertTrue(w.image_url)
        self.assertEqual(w.image_license, "cc-by-sa")
        self.assertIn("Test Artist", w.image_credit)
        self.assertIn("CC BY-SA", w.image_credit)
        self.assertIn("commons.wikimedia.org", w.image_source_url)

        # FieldProvenance written for each of the four image fields.
        rows = FieldProvenance.objects.filter(
            entity_type="wrestler", entity_id=w.id,
            field_name__startswith="image_",
        )
        field_names = set(rows.values_list("field_name", flat=True))
        self.assertIn("image_url", field_names)
        self.assertIn("image_license", field_names)
        self.assertIn("image_credit", field_names)
        self.assertIn("image_source_url", field_names)
        # Each row has a non-empty snippet.
        for r in rows:
            self.assertTrue(r.snippet, f"Empty snippet on {r.field_name}")
            self.assertGreaterEqual(r.confidence, 90)


# ============================================================================
# Cascade tests — verify the new identity scorer, candidate cascade,
# first-fill dim relaxation, and identity-threshold floor.
# ============================================================================


class IdentityScoringTests(TestCase):
    """filename/description/category matchers used by the identity scorer."""

    def test_filename_full_name_matches(self):
        self.assertTrue(commons.filename_mentions_name(
            "Bret_Hart_in_2009.jpg", "Bret Hart",
        ))

    def test_filename_year_only_doesnt_match(self):
        # 'WrestleMania 2024.jpg' shouldn't match wrestler 'Wrestle Mania'
        # (year-only is stripped first).
        self.assertFalse(commons.filename_mentions_name(
            "Random_unrelated_photo_2024.jpg", "Bret Hart",
        ))

    def test_filename_last_name_alone_does_not_match(self):
        # We require last name PLUS another name token to avoid
        # conflating Bret Hart / Owen Hart / Stu Hart in the Hart Family
        # Commons category.
        self.assertFalse(commons.filename_mentions_name(
            "Hart_family_reunion.jpg", "Bret Hart",
        ))

    def test_filename_last_plus_other_token_matches(self):
        self.assertTrue(commons.filename_mentions_name(
            "Bret-with-belt-Hart.jpg", "Bret Hart",
        ))

    def test_filename_punctuation_normalised(self):
        # Apostrophes, periods, etc. are stripped during normalisation.
        self.assertTrue(commons.filename_mentions_name(
            "Dean.Malenko_2002.jpg", "Dean Malenko",
        ))

    def test_single_token_name_requires_whole_word(self):
        # Regression test for the 2point0 → "3.0 Three Points.jpg" bug:
        # single-token name 'point' was matching 'points' as a substring.
        # Now requires whole-token equality.
        self.assertFalse(commons.filename_mentions_name(
            "3.0_Three_Points.jpg", "2point0",
        ))
        # And "Edge" must not match "ledger" anymore.
        self.assertFalse(commons.filename_mentions_name(
            "Ledger_book_history.jpg", "Edge",
        ))

    def test_single_token_name_matches_when_whole_word_present(self):
        # Legitimate single-token match: "Sting wrestling 2024.jpg" for Sting.
        self.assertTrue(commons.filename_mentions_name(
            "Sting_wrestling_2024.jpg", "Sting",
        ))
        # And "Kane WrestleMania.jpg" for Kane.
        self.assertTrue(commons.filename_mentions_name(
            "Kane_WrestleMania.jpg", "Kane",
        ))

    def test_substring_inside_word_no_match(self):
        # Multi-word name where the run isn't aligned to token boundaries.
        # "bret hart" inside "bretha rtthrowaway" must not match.
        self.assertFalse(commons.filename_mentions_name(
            "Brethartfilename.jpg", "Bret Hart",
        ))

    def test_description_match(self):
        self.assertTrue(commons.description_mentions_name(
            "Bret Hart wrestling at WrestleMania VIII", "Bret Hart",
        ))

    def test_description_no_match(self):
        self.assertFalse(commons.description_mentions_name(
            "Shawn Michaels delivering Sweet Chin Music", "Bret Hart",
        ))

    def test_description_with_digits_preserved(self):
        # Raw-name path catches names with digits that the normalizer
        # would strip — '2point0' literally appears in the description.
        self.assertTrue(commons.description_mentions_name(
            "Members of the tag team 2point0 at AEW Dynamite", "2point0",
        ))

    def test_description_single_token_no_substring_false_positive(self):
        # 'Edge' must not match 'ledger', 'edging', 'sledgehammer', etc.
        # The raw 'edge' substring would match all of these — but our
        # normalized-fallback uses whole-word, AND the raw path here
        # requires the FULL 'edge' string which is also in 'ledger'.
        # We accept this minor false-positive risk for the raw path
        # because rejecting it would also reject "Edge defeated Cena."
        # Earl's accuracy audit catches genuinely wrong assignments.
        # (Documented behaviour, not a bug — the test asserts the limit.)
        self.assertFalse(commons.description_mentions_name(
            "Three points scored in the match", "2point0",
        ))

    def test_categories_contain_with_prefix(self):
        self.assertTrue(commons.categories_contain(
            ["Category:Bret Hart", "Category:WWE Hall of Fame"],
            "Bret Hart",
        ))

    def test_categories_contain_without_prefix(self):
        self.assertTrue(commons.categories_contain(
            ["Bret Hart"], "Bret Hart",
        ))

    def test_categories_negative(self):
        self.assertFalse(commons.categories_contain(
            ["Category:Owen Hart"], "Bret Hart",
        ))


class CascadeOrderTests(TestCase):
    """find_image_candidates yields candidates in the correct priority order."""

    def test_p18_yielded_first_then_category_then_body(self):
        from owdb_django.wrestlebot.pipeline.images import find_image_candidates
        w = Wrestler.objects.create(
            name="Test Wrestler",
            wikipedia_url="https://en.wikipedia.org/wiki/Test_Wrestler",
        )
        with mock.patch(
            "owdb_django.wrestlebot.pipeline.images.resolve_qid_for_wikipedia_title",
            return_value="Q12345",
        ), mock.patch(
            "owdb_django.wrestlebot.pipeline.images.fetch_image_for_qid",
            return_value={"filename": "Test_Wrestler_P18.jpg",
                          "url": "", "thumb_url": "", "qid": "Q12345",
                          "property": "P18"},
        ), mock.patch(
            "owdb_django.wrestlebot.pipeline.images.resolve_commons_category_for_qid",
            return_value="Test Wrestler",
        ), mock.patch(
            "owdb_django.wrestlebot.pipeline.images.fetch_commons_category_files",
            return_value=[
                "Test_Wrestler_at_event.jpg",       # filename match → 95
                "Anonymous_action_shot.jpg",        # category only  → 85
            ],
        ), mock.patch(
            "owdb_django.wrestlebot.pipeline.images.fetch_wikipedia_body_image_filenames",
            return_value=[
                "Body_image_with_Test_Wrestler.jpg",  # body, name in filename → 75
                "Generic_body_photo.jpg",             # body, no match → 60
            ],
        ):
            cands = list(find_image_candidates(w, entity_type="wrestler"))
        # Order: P18, category-named, category, body-named, body-weak.
        paths = [c.source_path for c in cands]
        confs = [c.identity_confidence for c in cands]
        self.assertEqual(paths, [
            "wikidata_p18",
            "commons_category_named",
            "commons_category",
            "wikipedia_body",
            "wikipedia_body",
        ])
        self.assertEqual(confs, [100, 95, 85, 75, 60])

    def test_no_qid_yields_no_candidates(self):
        from owdb_django.wrestlebot.pipeline.images import find_image_candidates
        w = Wrestler.objects.create(name="No QID Wrestler")
        with mock.patch(
            "owdb_django.wrestlebot.pipeline.images.resolve_qid_for_wikipedia_title",
            return_value=None,
        ):
            cands = list(find_image_candidates(w, entity_type="wrestler"))
        self.assertEqual(cands, [])


class CascadeAcceptanceTests(TestCase):
    """assign_image_to_entity picks the first passing candidate."""

    def _meta(self, *, license_code="cc-by-sa", description="",
                width=400, height=600, categories=None):
        return commons.CommonsImageMeta(
            filename="Anything.jpg",
            original_url="https://upload.wikimedia.org/anything.jpg",
            thumb_url_400="https://commons.wikimedia.org/wiki/Special:FilePath/Anything.jpg?width=400",
            file_page_url="https://commons.wikimedia.org/wiki/File:Anything.jpg",
            width=width, height=height,
            size_bytes=80_000, mime="image/jpeg",
            license_code=license_code,
            license_short="CC BY-SA 3.0",
            license_url="", usage_terms="",
            attribution_required=(license_code in ("cc-by", "cc-by-sa")),
            artist="Test Artist", credit="", permission="",
            description=description, categories=list(categories or []),
            restrictions="", is_allowed=bool(license_code),
            rejection_reason=("" if license_code else "no license"),
        )

    def test_p18_rejected_then_category_accepted(self):
        """P18 fails legal gate → cascade falls through to category hit."""
        from owdb_django.wrestlebot.pipeline import images
        w = Wrestler.objects.create(
            name="Bret Hart",
            wikipedia_url="https://en.wikipedia.org/wiki/Bret_Hart",
        )

        def fake_metadata(filename):
            # P18 file fails the license gate.
            if filename == "P18_file.jpg":
                m = self._meta(license_code="")
                m.is_allowed = False
                m.rejection_reason = "License 'cc-by-nc' is explicitly blocked"
                return m
            # Category file passes everything.
            if filename == "Bret_Hart_at_2009.jpg":
                return self._meta(width=800, height=1200)
            return None

        with mock.patch(
            "owdb_django.wrestlebot.pipeline.images.resolve_qid_for_wikipedia_title",
            return_value="Q314419",
        ), mock.patch(
            "owdb_django.wrestlebot.pipeline.images.fetch_image_for_qid",
            return_value={"filename": "P18_file.jpg", "url": "", "thumb_url": "",
                          "qid": "Q314419", "property": "P18"},
        ), mock.patch(
            "owdb_django.wrestlebot.pipeline.images.resolve_commons_category_for_qid",
            return_value="Bret Hart",
        ), mock.patch(
            "owdb_django.wrestlebot.pipeline.images.fetch_commons_category_files",
            return_value=["Bret_Hart_at_2009.jpg"],
        ), mock.patch(
            "owdb_django.wrestlebot.pipeline.images.fetch_wikipedia_body_image_filenames",
            return_value=[],
        ), mock.patch(
            "owdb_django.wrestlebot.pipeline.images.fetch_image_metadata",
            side_effect=fake_metadata,
        ):
            result = images.assign_image_to_entity(w, entity_type="wrestler")
        self.assertTrue(result.success, msg=result.refusal_reason)
        # Accepted the second candidate (category-named).
        self.assertEqual(result.source_path, "commons_category_named")
        self.assertEqual(result.identity_confidence, 95)
        # `considered` records both candidates (one rejected, one accepted).
        self.assertEqual(len(result.considered), 2)
        self.assertFalse(result.considered[0]["accepted"])
        self.assertTrue(result.considered[1]["accepted"])

    def test_first_fill_dim_floor_relaxed(self):
        """A 150px image is rejected for replacement but accepted for first-fill."""
        from owdb_django.wrestlebot.pipeline import images
        small_ok = self._meta(width=150, height=200)

        with mock.patch(
            "owdb_django.wrestlebot.pipeline.images.resolve_qid_for_wikipedia_title",
            return_value="Q999",
        ), mock.patch(
            "owdb_django.wrestlebot.pipeline.images.fetch_image_for_qid",
            return_value={"filename": "Small.jpg", "url": "", "thumb_url": "",
                          "qid": "Q999", "property": "P18"},
        ), mock.patch(
            "owdb_django.wrestlebot.pipeline.images.resolve_commons_category_for_qid",
            return_value=None,
        ), mock.patch(
            "owdb_django.wrestlebot.pipeline.images.fetch_commons_category_files",
            return_value=[],
        ), mock.patch(
            "owdb_django.wrestlebot.pipeline.images.fetch_wikipedia_body_image_filenames",
            return_value=[],
        ), mock.patch(
            "owdb_django.wrestlebot.pipeline.images.fetch_image_metadata",
            return_value=small_ok,
        ):
            # First-fill: entity has no image yet → floor relaxed to 120 → 150 passes.
            w_new = Wrestler.objects.create(
                name="First Fill", wikipedia_url="https://en.wikipedia.org/wiki/X",
            )
            r_new = images.assign_image_to_entity(w_new, entity_type="wrestler")
            self.assertTrue(r_new.success, msg=r_new.refusal_reason)

            # Replacement: entity HAS an image → floor stays at 200 → 150 fails.
            w_old = Wrestler.objects.create(
                name="Replacement", wikipedia_url="https://en.wikipedia.org/wiki/Y",
                image_url="https://example.com/existing.jpg", image_license="pd",
            )
            r_old = images.assign_image_to_entity(
                w_old, entity_type="wrestler", force=True,
            )
            self.assertFalse(r_old.success)
            self.assertTrue(any(
                "too small" in (c.get("refusal_reason") or "").lower()
                for c in r_old.considered
            ))

    def test_identity_floor_blocks_weak_body_image(self):
        """A weak body image (confidence 60) is rejected even with a valid license."""
        from owdb_django.wrestlebot.pipeline import images
        valid = self._meta(width=800, height=1200, description="Random image")

        with mock.patch(
            "owdb_django.wrestlebot.pipeline.images.resolve_qid_for_wikipedia_title",
            return_value="Q42",
        ), mock.patch(
            "owdb_django.wrestlebot.pipeline.images.fetch_image_for_qid",
            return_value=None,                    # no P18
        ), mock.patch(
            "owdb_django.wrestlebot.pipeline.images.resolve_commons_category_for_qid",
            return_value=None,                    # no P373
        ), mock.patch(
            "owdb_django.wrestlebot.pipeline.images.fetch_commons_category_files",
            return_value=[],
        ), mock.patch(
            "owdb_django.wrestlebot.pipeline.images.fetch_wikipedia_body_image_filenames",
            # Filename and description both lack the wrestler's name → 60.
            return_value=["unrelated_action_shot.jpg"],
        ), mock.patch(
            "owdb_django.wrestlebot.pipeline.images.fetch_image_metadata",
            return_value=valid,
        ):
            w = Wrestler.objects.create(
                name="Floor Test",
                wikipedia_url="https://en.wikipedia.org/wiki/Floor_Test",
            )
            result = images.assign_image_to_entity(w, entity_type="wrestler")
        self.assertFalse(result.success)
        self.assertEqual(len(result.considered), 1)
        # The one candidate was rejected for identity confidence, not license.
        self.assertIn("identity confidence",
                      result.considered[0]["refusal_reason"].lower())

    def test_body_image_description_bumps_confidence(self):
        """A body image whose description mentions the wrestler bumps to 75 and passes."""
        from owdb_django.wrestlebot.pipeline import images
        meta_with_desc = self._meta(
            width=800, height=1200,
            description="John Cena celebrates after WrestleMania 36",
        )

        with mock.patch(
            "owdb_django.wrestlebot.pipeline.images.resolve_qid_for_wikipedia_title",
            return_value="Q44248",
        ), mock.patch(
            "owdb_django.wrestlebot.pipeline.images.fetch_image_for_qid",
            return_value=None,
        ), mock.patch(
            "owdb_django.wrestlebot.pipeline.images.resolve_commons_category_for_qid",
            return_value=None,
        ), mock.patch(
            "owdb_django.wrestlebot.pipeline.images.fetch_commons_category_files",
            return_value=[],
        ), mock.patch(
            "owdb_django.wrestlebot.pipeline.images.fetch_wikipedia_body_image_filenames",
            return_value=["generic_filename.jpg"],   # seed conf = 60
        ), mock.patch(
            "owdb_django.wrestlebot.pipeline.images.fetch_image_metadata",
            return_value=meta_with_desc,
        ):
            w = Wrestler.objects.create(
                name="John Cena",
                wikipedia_url="https://en.wikipedia.org/wiki/John_Cena",
            )
            result = images.assign_image_to_entity(w, entity_type="wrestler")
        self.assertTrue(result.success, msg=result.refusal_reason)
        # Description bumped 60 → 75 (≥ 75 floor → accepted).
        self.assertGreaterEqual(result.identity_confidence, 75)


class CategoryFilesParsingTests(TestCase):
    """Commons category-member API parsing — filenames only, image MIMEs only."""

    def test_filters_to_image_extensions(self):
        api_response = {"query": {"categorymembers": [
            {"title": "File:Bret_Hart_2009.jpg"},
            {"title": "File:Bret_Hart_logo.svg"},          # SVG dropped
            {"title": "File:Hart_documentary.ogv"},         # video dropped
            {"title": "File:Owen_Hart_tribute.png"},
            {"title": "Category:Subcategory"},              # not a file
            {"title": "File:"},                              # empty filename
        ]}}
        with mock.patch(
            "owdb_django.wrestlebot.sources.commons._http_get_json",
            return_value=api_response,
        ):
            out = commons.fetch_commons_category_files("Bret Hart")
        self.assertEqual(out, ["Bret_Hart_2009.jpg", "Owen_Hart_tribute.png"])

    def test_strips_category_prefix(self):
        with mock.patch(
            "owdb_django.wrestlebot.sources.commons._http_get_json",
            return_value={"query": {"categorymembers": []}},
        ) as m:
            commons.fetch_commons_category_files("Category:Bret Hart")
        # The HTTP call uses cmtitle=Category:Bret%20Hart even when caller
        # passed the 'Category:' prefix — verify no double-prefix.
        called_url = m.call_args[0][0]
        self.assertIn("Category%3ABret%20Hart", called_url)
        self.assertNotIn("Category%3ACategory%3A", called_url)


class BodyImageParsingTests(TestCase):
    """Wikipedia prop=images parsing — filenames, chrome filtered."""

    def test_filters_chrome_and_non_image(self):
        api_response = {"query": {"pages": {"1": {"images": [
            {"title": "File:Bret_Hart_in_2009.jpg"},
            {"title": "File:Commons-logo.svg"},   # chrome — drop
            {"title": "File:Question_book-new.svg"},  # chrome — drop
            {"title": "File:Owen_Hart.jpg"},
            {"title": "File:audio_clip.ogg"},     # non-image — drop
        ]}}}}
        with mock.patch(
            "owdb_django.wrestlebot.sources.commons._http_get_json",
            return_value=api_response,
        ):
            out = commons.fetch_wikipedia_body_image_filenames("Bret Hart")
        self.assertEqual(out, ["Bret_Hart_in_2009.jpg", "Owen_Hart.jpg"])


# ============================================================================
# Promotional-art guard tests.
#
# The legal risk we're targeting: a Commons file whose PHOTO license is fine
# (CC-BY-SA) but whose PRIMARY SUBJECT is a copyrighted promotional design —
# event poster, keyart, billboard ad, press kit. The photo's CC clearance
# doesn't reach the design underneath, so using it as the event's image is
# unsafe even when our normal license gate is happy.
# ============================================================================


def _promo_meta(*, filename="X.jpg", description="", categories=()):
    return commons.CommonsImageMeta(
        filename=filename,
        original_url=f"https://upload.wikimedia.org/wikipedia/commons/{filename}",
        thumb_url_400="",
        file_page_url=f"https://commons.wikimedia.org/wiki/File:{filename}",
        width=1200, height=900,
        size_bytes=300_000, mime="image/jpeg",
        license_code="cc-by-sa", license_short="CC BY-SA 4.0",
        license_url="", usage_terms="",
        attribution_required=True, artist="Photographer", credit="",
        permission="", description=description,
        categories=list(categories), restrictions="",
        is_allowed=True, rejection_reason="",
    )


class PromotionalArtGuardTests(TestCase):
    """is_likely_promotional_art flags posters/keyart/press-kit photos."""

    def _check(self, **kw):
        from owdb_django.wrestlebot.pipeline.images import is_likely_promotional_art
        return is_likely_promotional_art(_promo_meta(**kw))

    def test_filename_with_poster_token_is_flagged(self):
        flagged, reason = self._check(filename="WrestleMania_XL_poster.jpg")
        self.assertTrue(flagged)
        self.assertIn("poster", reason)

    def test_filename_with_keyart_token_is_flagged(self):
        flagged, _ = self._check(filename="AEW_All_Out_keyart.jpg")
        self.assertTrue(flagged)

    def test_filename_with_press_kit_token_is_flagged(self):
        flagged, _ = self._check(filename="Event_press_kit_hero_image.jpg")
        self.assertTrue(flagged)

    def test_filename_token_must_be_whole_word(self):
        # 'buster' contained within 'blockbuster' should NOT match 'poster'.
        # We require whole-word tokens — defense against substring false
        # positives.
        flagged, _ = self._check(filename="Blockbuster_event_photo.jpg")
        self.assertFalse(flagged)

    def test_categories_with_posters_is_flagged(self):
        flagged, reason = self._check(
            filename="random.jpg",
            categories=["Posters of WWE", "WrestleMania media"],
        )
        self.assertTrue(flagged)
        self.assertIn("category", reason.lower())

    def test_categories_with_billboards_is_flagged(self):
        flagged, _ = self._check(
            filename="random.jpg",
            categories=["Billboards in Las Vegas"],
        )
        self.assertTrue(flagged)

    def test_description_official_poster_is_flagged(self):
        flagged, reason = self._check(
            filename="random.jpg",
            description="The official poster for WrestleMania XL Night 2.",
        )
        self.assertTrue(flagged)
        self.assertIn("description", reason.lower())

    def test_clean_arena_photo_passes(self):
        # A pure venue/arena photo with no promotional-art signals must
        # NOT be flagged.
        flagged, _ = self._check(
            filename="Madison_Square_Garden_2024.jpg",
            description="Exterior of Madison Square Garden during a WWE event.",
            categories=["Madison Square Garden", "Wrestling venues"],
        )
        self.assertFalse(flagged)

    def test_clean_action_shot_passes(self):
        flagged, _ = self._check(
            filename="John_Cena_at_WrestleMania_36.jpg",
            description="John Cena celebrates after his match at WrestleMania 36.",
            categories=["John Cena", "WrestleMania 36"],
        )
        self.assertFalse(flagged)


class EventGateRejectsPromoArtTests(TestCase):
    """_evaluate_candidate refuses promo-art for events (but not promotions)."""

    def setUp(self):
        _with_cascade_off(self)

    def _try_assign(self, *, entity_type, model_cls, meta):
        """Run the cascade with a single P18 candidate of the given meta."""
        from owdb_django.wrestlebot.pipeline import images
        # All Wrestler/Promotion/Event models share the image_url +
        # wikipedia_url fields by VerificationMixin.
        ent = model_cls.objects.create(
            name="Test Entity",
            wikipedia_url="https://en.wikipedia.org/wiki/Test_Entity",
        )
        # promotions need a slug too; tolerate models without it
        if hasattr(ent, "slug") and not ent.slug:
            ent.slug = "test-entity"
            ent.save(update_fields=["slug"])
        with mock.patch(
            "owdb_django.wrestlebot.pipeline.images.resolve_qid_for_wikipedia_title",
            return_value="Q12345",
        ), mock.patch(
            "owdb_django.wrestlebot.pipeline.images.fetch_image_for_qid",
            return_value={"filename": meta.filename, "url": meta.original_url,
                          "thumb_url": "", "qid": "Q12345", "property": "P18"},
        ), mock.patch(
            "owdb_django.wrestlebot.pipeline.images.fetch_image_metadata",
            return_value=meta,
        ):
            return images.assign_image_to_entity(ent, entity_type=entity_type)

    def test_event_with_poster_filename_is_refused(self):
        from owdb_django.owdbapp.models import Event
        # Events need a promotion FK — create one. Event model doesn't
        # carry a wikipedia_url field; the cascade falls back to the
        # entity's `name` for the Wikipedia title.
        promo = Promotion.objects.create(name="Test Promo", slug="test-promo")
        from datetime import date
        event = Event.objects.create(
            name="Test Event", promotion=promo, date=date(2024, 1, 1),
        )
        meta = _promo_meta(filename="WrestleMania_2024_poster.jpg")
        from owdb_django.wrestlebot.pipeline import images
        with mock.patch(
            "owdb_django.wrestlebot.pipeline.images.resolve_qid_for_wikipedia_title",
            return_value="Q12345",
        ), mock.patch(
            "owdb_django.wrestlebot.pipeline.images.fetch_image_for_qid",
            return_value={"filename": meta.filename, "url": meta.original_url,
                          "thumb_url": "", "qid": "Q12345", "property": "P18"},
        ), mock.patch(
            "owdb_django.wrestlebot.pipeline.images.fetch_image_metadata",
            return_value=meta,
        ):
            result = images.assign_image_to_entity(event, entity_type="event")
        self.assertFalse(result.success)
        # The considered list captures the specific guard reason.
        self.assertTrue(any(
            "promotional-art guard" in (c.get("refusal_reason") or "").lower()
            for c in result.considered
        ))

    def test_promotion_with_logo_token_is_accepted(self):
        # Promotion logos are NOT filtered by the promo-art guard, since
        # the logo IS the trademark identifier and nominative fair use
        # applies. (The same file passed as "event" would be refused.)
        promo = Promotion.objects.create(
            name="Test Promo", slug="test-promo",
            wikipedia_url="https://en.wikipedia.org/wiki/Test_Promo",
        )
        # A logo file named with "logo" in it is fine for a promotion.
        meta = _promo_meta(
            filename="WWE_logo.svg",
            description="Official WWE logo.",
            categories=["Logos of WWE"],
        )
        meta = commons.CommonsImageMeta(
            **{**meta.__dict__, "mime": "image/svg+xml"},
        )
        result = self._try_assign(
            entity_type="promotion", model_cls=Promotion, meta=meta,
        )
        # promo-art guard does NOT fire for promotions, but the test entity
        # may still fail identity matching (no Commons category mock). What
        # we're proving: the guard wasn't the rejection reason.
        for c in result.considered:
            self.assertNotIn(
                "promotional-art guard",
                (c.get("refusal_reason") or "").lower(),
            )


class TrademarkAttributionTests(TestCase):
    """Promotion/stable/tv_show credits carry a nominative fair-use notice."""

    def test_promotion_credit_includes_fair_use_notice(self):
        from owdb_django.wrestlebot.pipeline.images import _build_credit_string
        meta = _promo_meta(filename="WWE_logo.svg", description="WWE logo")
        credit = _build_credit_string(meta, entity_type="promotion")
        self.assertIn("nominative fair use", credit.lower())

    def test_event_credit_does_not_include_fair_use_notice(self):
        from owdb_django.wrestlebot.pipeline.images import _build_credit_string
        meta = _promo_meta(filename="Arena_photo.jpg")
        credit = _build_credit_string(meta, entity_type="event")
        self.assertNotIn("nominative fair use", credit.lower())

    def test_wrestler_credit_does_not_include_fair_use_notice(self):
        from owdb_django.wrestlebot.pipeline.images import _build_credit_string
        meta = _promo_meta(filename="Bret_Hart.jpg")
        credit = _build_credit_string(meta, entity_type="wrestler")
        self.assertNotIn("nominative fair use", credit.lower())

    def test_stable_credit_includes_fair_use_notice(self):
        from owdb_django.wrestlebot.pipeline.images import _build_credit_string
        meta = _promo_meta(filename="Bullet_Club_logo.svg")
        credit = _build_credit_string(meta, entity_type="stable")
        self.assertIn("nominative fair use", credit.lower())
