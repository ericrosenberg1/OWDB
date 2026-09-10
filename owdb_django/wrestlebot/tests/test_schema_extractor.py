"""
Tests for the declarative table-extractor framework.

These tests verify the contract the schema-driven framework makes:
  * Specs cleanly extract rows from realistic Wikipedia-style HTML
  * required_fields drops incomplete rows
  * row_filter drops continuation/junk rows
  * Every value comes back wrapped in a FieldSnippet (so the accuracy
    contract has provenance to write)
  * Context resolvers (heading year) work
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

from django.test import TestCase

from owdb_django.wrestlebot.sources._schema import (
    TableExtractorSpec,
    clean_attendance,
    clean_iso_or_natural_date,
    clean_text,
    extract_tables,
    resolve_year_from_preceding_heading,
    wikitable_with_headers,
)
from owdb_django.wrestlebot.sources.base import FieldSnippet


@dataclass
class _Event:
    name: str
    date: Optional[date] = None
    venue_name: str = ""
    attendance: Optional[int] = None
    year_context: Optional[int] = None


_PPV_HTML = """
<html><body>
<h2>2024</h2>
<table class="wikitable">
 <tr><th>Date</th><th>Event</th><th>Venue</th><th>City</th><th>Attendance</th></tr>
 <tr>
   <td>April 6, 2024</td>
   <td>WrestleMania XL Night 1</td>
   <td>Lincoln Financial Field</td>
   <td>Philadelphia, Pennsylvania</td>
   <td>72,755</td>
 </tr>
 <tr>
   <td>April 7, 2024</td>
   <td>WrestleMania XL Night 2</td>
   <td>Lincoln Financial Field</td>
   <td>Philadelphia, Pennsylvania</td>
   <td>72,543</td>
 </tr>
 <!-- a junk row: an Event-column continuation that's really just a location -->
 <tr>
   <td></td>
   <td>Rosemont, Illinois</td>
   <td></td>
   <td></td>
   <td></td>
 </tr>
 <!-- a row missing the date — should be dropped by required_fields -->
 <tr>
   <td></td>
   <td>SummerSlam (date TBA)</td>
   <td>TBD</td>
   <td>TBD</td>
   <td></td>
 </tr>
</table>
<h2>2023</h2>
<table class="wikitable">
 <tr><th>Date</th><th>Event</th><th>Venue</th><th>City</th><th>Attendance</th></tr>
 <tr>
   <td>2023-04-01</td>
   <td>WrestleMania 39 Night 1</td>
   <td>SoFi Stadium</td>
   <td>Inglewood, California</td>
   <td>80,497</td>
 </tr>
</table>
</body></html>
"""


def _skip_location_continuation(ctx: dict) -> bool:
    """Drop rows whose 'name' cell looks like a 'City, State' continuation."""
    name = (ctx.get("name") or "").strip()
    if not name:
        return False  # blank name = drop
    if "," in name and len(name) < 80:
        suffix = name.split(",")[-1].strip()
        if (
            suffix
            and suffix[0].isupper()
            and len(suffix) <= 30
            and suffix.replace(" ", "").isalpha()
        ):
            return False
    return True


class TableExtractorTests(TestCase):
    def _spec(self) -> TableExtractorSpec:
        return TableExtractorSpec(
            result_dataclass=_Event,
            table_filter=wikitable_with_headers("date", "event", "venue"),
            columns={
                "date": ("date",),
                "name": ("event",),
                "venue_name": ("venue",),
                "attendance": ("attendance",),
                "year_context": ("__heading_year__",),
            },
            cleaners={
                "date": clean_iso_or_natural_date,
                "name": clean_text,
                "venue_name": clean_text,
                "attendance": clean_attendance,
            },
            row_filter=_skip_location_continuation,
            context_resolvers={
                "year_context": resolve_year_from_preceding_heading,
            },
            required_fields=("date", "name"),
        )

    def test_extracts_three_well_formed_rows(self):
        rows = extract_tables(_PPV_HTML, self._spec())
        self.assertEqual(
            [e.name for (e, _) in rows],
            [
                "WrestleMania XL Night 1",
                "WrestleMania XL Night 2",
                "WrestleMania 39 Night 1",
            ],
        )

    def test_dates_parsed_to_date_objects(self):
        rows = extract_tables(_PPV_HTML, self._spec())
        dates = [e.date for (e, _) in rows]
        self.assertEqual(dates[0], date(2024, 4, 6))
        self.assertEqual(dates[1], date(2024, 4, 7))
        self.assertEqual(dates[2], date(2023, 4, 1))

    def test_attendance_parsed_with_comma_separator(self):
        rows = extract_tables(_PPV_HTML, self._spec())
        self.assertEqual(rows[0][0].attendance, 72_755)
        self.assertEqual(rows[2][0].attendance, 80_497)

    def test_required_fields_drops_dateless_row(self):
        # The "SummerSlam (date TBA)" row has no parseable date → dropped.
        rows = extract_tables(_PPV_HTML, self._spec())
        for inst, _snippets in rows:
            self.assertIsNotNone(inst.date, f"row leaked through: {inst!r}")
        self.assertNotIn(
            "SummerSlam (date TBA)",
            [inst.name for inst, _ in rows],
        )

    def test_row_filter_drops_location_continuation(self):
        rows = extract_tables(_PPV_HTML, self._spec())
        names = [inst.name for inst, _ in rows]
        # The 'Rosemont, Illinois' continuation row would otherwise pass
        # the required-field check (name is non-empty) but row_filter
        # catches it.
        self.assertNotIn("Rosemont, Illinois", names)

    def test_heading_year_context_resolves(self):
        rows = extract_tables(_PPV_HTML, self._spec())
        years = [inst.year_context for inst, _ in rows]
        # First two rows under <h2>2024</h2>; last under <h2>2023</h2>.
        self.assertEqual(years, [2024, 2024, 2023])

    def test_every_value_carries_a_field_snippet(self):
        rows = extract_tables(_PPV_HTML, self._spec())
        for inst, snippets in rows:
            # Each populated dataclass field has a corresponding snippet.
            for field_name in ("date", "name", "venue_name", "attendance"):
                value = getattr(inst, field_name)
                if value not in (None, "", 0):
                    self.assertIn(
                        field_name, snippets, f"missing snippet for {field_name!r} in row {inst!r}"
                    )
                    self.assertIsInstance(snippets[field_name], FieldSnippet)
                    # Snippet text must be non-empty so the contract can quote it.
                    self.assertTrue(snippets[field_name].snippet)


# ---------------------------------------------------------------------------
# rowspan / colspan grid expansion
# ---------------------------------------------------------------------------
#
# Wikipedia writes a venue once and spans it down over a whole residency,
# and spans an episode number down over a two-night taping. Reading each
# `<tr>` positionally lines those rows up one or two columns to the left,
# which put main-event text into the city field on 69 AEW Dynamite episodes
# and dropped five AEW Collision episodes outright before this was fixed.


_ROWSPAN_HTML = """
<html><body>
<h2>2021</h2>
<table class="wikitable">
 <tr><th>Date</th><th>Event</th><th>Venue</th><th>City</th><th>Attendance</th></tr>
 <tr>
   <td>April 6, 2021</td>
   <td>Spanned Venue Night 1</td>
   <td rowspan="3">Daily's Place</td>
   <td rowspan="3">Jacksonville, Florida</td>
   <td>1,000</td>
 </tr>
 <tr>
   <td>April 7, 2021</td>
   <td>Spanned Venue Night 2</td>
   <td>1,100</td>
 </tr>
 <tr>
   <td>April 8, 2021</td>
   <td>Spanned Venue Night 3</td>
   <td>1,200</td>
 </tr>
</table>
</body></html>
"""


_COLSPAN_HTML = """
<html><body>
<h2>2022</h2>
<table class="wikitable">
 <tr><th>Date</th><th colspan="2">Event</th><th>Venue</th><th>City</th></tr>
 <tr>
   <td>May 1, 2022</td>
   <td>Colspan Header Show</td>
   <td>(subtitle)</td>
   <td>Arena One</td>
   <td>Tampa, Florida</td>
 </tr>
</table>
</body></html>
"""


class GridExpansionTests(TestCase):
    """`expand_table_grid` must hand every consumer a rectangular table."""

    def _spec(self):
        return TableExtractorSpec(
            result_dataclass=_Event,
            table_filter=wikitable_with_headers("date", "event"),
            columns={
                "date": ("date",),
                "name": ("event",),
                "venue_name": ("venue",),
                "attendance": ("attendance",),
            },
            cleaners={
                "date": clean_iso_or_natural_date,
                "name": clean_text,
                "venue_name": clean_text,
                "attendance": clean_attendance,
            },
            required_fields=("name",),
        )

    def test_spanned_cell_repeats_down_every_row_it_covers(self):
        from owdb_django.wrestlebot.sources._schema import expand_table_grid

        from bs4 import BeautifulSoup

        table = BeautifulSoup(_ROWSPAN_HTML, "lxml").find("table")
        grid = expand_table_grid(table)
        self.assertEqual([len(r) for r in grid], [5, 5, 5, 5])
        venues = [r[2].get_text(" ", strip=True) for r in grid[1:]]
        self.assertEqual(venues, ["Daily's Place"] * 3)

    def test_rows_under_a_spanned_venue_keep_their_own_columns(self):
        rows = extract_tables(_ROWSPAN_HTML, self._spec())
        self.assertEqual(
            [(i.name, i.venue_name, i.attendance) for i, _ in rows],
            [
                ("Spanned Venue Night 1", "Daily's Place", 1000),
                ("Spanned Venue Night 2", "Daily's Place", 1100),
                ("Spanned Venue Night 3", "Daily's Place", 1200),
            ],
        )

    def test_attendance_is_not_read_from_the_venue_column(self):
        """The regression itself: without expansion, row 2's 1,100 landed in
        the venue slot and the real venue vanished."""
        rows = extract_tables(_ROWSPAN_HTML, self._spec())
        for inst, _ in rows:
            self.assertEqual(inst.venue_name, "Daily's Place")
            self.assertIsNotNone(inst.attendance)

    def test_colspan_header_widens_the_grid_so_later_columns_align(self):
        from owdb_django.wrestlebot.sources._schema import expand_table_grid

        from bs4 import BeautifulSoup

        table = BeautifulSoup(_COLSPAN_HTML, "lxml").find("table")
        grid = expand_table_grid(table)
        headers = [c.get_text(" ", strip=True).lower() for c in grid[0]]
        self.assertEqual(headers, ["date", "event", "event", "venue", "city"])
        rows = extract_tables(_COLSPAN_HTML, self._spec())
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0].venue_name, "Arena One")

    def test_short_row_is_padded_not_shifted(self):
        """A row with fewer cells than the header pads on the right, so a
        consumer indexing positionally never reads a neighbour's value."""
        from owdb_django.wrestlebot.sources._schema import expand_table_grid

        from bs4 import BeautifulSoup

        html = """
        <table class="wikitable">
         <tr><th>A</th><th>B</th><th>C</th><th>D</th></tr>
         <tr><td>a1</td><td>b1</td></tr>
        </table>
        """
        table = BeautifulSoup(html, "lxml").find("table")
        grid = expand_table_grid(table)
        self.assertEqual(len(grid[1]), 4)
        self.assertEqual(
            [c.get_text(" ", strip=True) for c in grid[1]],
            ["a1", "b1", "", ""],
        )
