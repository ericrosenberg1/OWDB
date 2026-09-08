"""
Tests for owdb_django/owdbapp/tasks.py (Celery task definitions).

No Celery worker runs in production today (docker-compose.nuc.yml pins celery
to zero replicas), so these tasks are dormant. Still worth testing: they were
never exercised by any prior test, and the two chain() workflows below had a
real, confirmed bug that would have crashed (or silently corrupted arguments
through) every task in the chain the moment a worker was ever brought back.

Nothing here needs a real Celery worker or broker: task functions decorated
with @shared_task can be called directly as plain Python functions (Celery
only intercepts calls made through .delay()/.apply_async()), and
`chain(...).apply_async()` is mocked out so building the workflow never tries
to reach Redis.
"""

from unittest.mock import patch

from django.test import SimpleTestCase

from .. import tasks


def _run_and_capture_chain(task_callable):
    """Call `task_callable()` with chain.apply_async mocked out; return the
    celery.canvas._chain instance that was built, without ever submitting it.
    """
    captured = {}

    def fake_apply_async(self, *args, **kwargs):
        captured["chain"] = self
        return None

    with patch("celery.canvas._chain.apply_async", fake_apply_async):
        result = task_callable()
    return result, captured["chain"]


class RunFullImportChainTest(SimpleTestCase):
    """Regression for the owdbapp bug-fix sweep, item 5 (beyond-scope audit):
    run_full_import()'s chain(run_all_scrapers.s(), run_all_apis.s()) used a
    mutable signature (.s()) for run_all_apis, a task that takes zero
    arguments. Celery chains prepend each task's return value to the next
    task's args, so run_all_scrapers's `{"status": "started"}` return value
    would have been forwarded into run_all_apis(), raising "run_all_apis()
    takes 0 positional arguments but 1 was given" the moment a worker ran it.
    """

    def test_run_all_apis_link_is_immutable(self):
        result, chain_obj = _run_and_capture_chain(tasks.run_full_import)
        self.assertEqual(result, {"status": "started"})
        task_names = [sig.task for sig in chain_obj.tasks]
        self.assertEqual(
            task_names,
            [
                "owdb_django.owdbapp.tasks.run_all_scrapers",
                "owdb_django.owdbapp.tasks.run_all_apis",
            ],
        )
        run_all_apis_sig = chain_obj.tasks[1]
        self.assertTrue(
            run_all_apis_sig.immutable,
            "run_all_apis must be an immutable signature (.si()): it takes no "
            "arguments, but a mutable .s() signature would receive "
            "run_all_scrapers's dict return value as an unexpected positional "
            "argument and crash with a TypeError as soon as a worker ran it.",
        )


class RunAllImageFetchesChainTest(SimpleTestCase):
    """Regression for the same bug pattern in run_all_image_fetches(), where
    it was worse: every one of the 5 chained image-fetch tasks takes a real
    positional `batch_size` argument, so a mutable .s() signature wouldn't
    raise a clean "unexpected argument" error. It would silently misassign
    the previous task's dict result to `batch_size` and shift the intended
    batch_size into `refresh_old`, then crash on `queryset[:batch_size]`
    ('<' not supported between 'dict' and 'int') on the second task, and
    likewise for every task after it.
    """

    def test_every_link_is_immutable_with_its_own_batch_size(self):
        result, chain_obj = _run_and_capture_chain(tasks.run_all_image_fetches)
        self.assertEqual(result, {"status": "started"})
        expected = [
            ("owdb_django.owdbapp.tasks.fetch_wrestler_images", (20,)),
            ("owdb_django.owdbapp.tasks.fetch_promotion_images", (10,)),
            ("owdb_django.owdbapp.tasks.fetch_venue_images", (10,)),
            ("owdb_django.owdbapp.tasks.fetch_title_images", (10,)),
            ("owdb_django.owdbapp.tasks.fetch_event_images", (15,)),
        ]
        actual = [(sig.task, tuple(sig.args)) for sig in chain_obj.tasks]
        self.assertEqual(actual, expected)
        for sig in chain_obj.tasks:
            self.assertTrue(
                sig.immutable,
                f"{sig.task} must be an immutable signature (.si()): every "
                "image-fetch task in this chain is independent and takes its "
                "own batch_size, so a mutable .s() signature would receive "
                "the previous task's dict result as an extra leading "
                "positional argument, misassigning batch_size and "
                "refresh_old for every task after the first.",
            )


class RunAllScrapersAndApisGroupTest(SimpleTestCase):
    """run_all_scrapers/run_all_apis use group(), not chain(). Tasks run in
    parallel and never see each other's return values, so the argument-
    forwarding bug that hit run_full_import/run_all_image_fetches structurally
    cannot apply here. Pinned so a future refactor to chain() would be caught
    by the tests above rather than silently losing this property.
    """

    def test_run_all_scrapers_uses_a_group_not_a_chain(self):
        captured = {}

        def fake_apply_async(self, *args, **kwargs):
            captured["group"] = self
            return None

        with (
            patch("celery.canvas._chord.apply_async", fake_apply_async),
            patch("celery.canvas.group.apply_async", fake_apply_async),
        ):
            result = tasks.run_all_scrapers()
        self.assertEqual(result, {"status": "started"})
        self.assertIn("group", captured)
        task_names = {sig.task for sig in captured["group"].tasks}
        self.assertEqual(
            task_names,
            {
                "owdb_django.owdbapp.tasks.scrape_wikipedia_wrestlers",
                "owdb_django.owdbapp.tasks.scrape_wikipedia_promotions",
                "owdb_django.owdbapp.tasks.scrape_wikipedia_events",
                "owdb_django.owdbapp.tasks.scrape_cagematch_wrestlers",
                "owdb_django.owdbapp.tasks.scrape_cagematch_events",
                "owdb_django.owdbapp.tasks.scrape_profightdb_wrestlers",
                "owdb_django.owdbapp.tasks.scrape_profightdb_events",
            },
        )
