"""
wb_replay_session — re-dispatch every recorded tool call from an
AgentSession against the current rules + data.

Use cases:
  * Earl found 100 entities the contract now considers wrong. Replay
    the JR session(s) that created them with `--dry-run` to see which
    calls would behave differently under tightened rules.
  * A bug fix landed in `wiki_fetch` and you suspect old sessions
    re-ingested correctly. Replay one to confirm.
  * Investigate divergence between original-run results and current
    DB state.

Typical use:
    python manage.py wb_replay_session --session-id 1234
    python manage.py wb_replay_session --session-id 1234 --apply
    python manage.py wb_replay_session --session-id 1234 --json
"""

from __future__ import annotations

import json

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Replay an AgentSession by re-dispatching its recorded tool calls."

    def add_arguments(self, parser):
        parser.add_argument(
            "--session-id", type=int, required=True,
            help="AgentSession PK to replay.",
        )
        parser.add_argument(
            "--apply", action="store_true",
            help=(
                "Actually re-apply the calls (no rollback). Defaults to "
                "dry-run mode, which rolls back at the end of the replay."
            ),
        )
        parser.add_argument(
            "--include-done", action="store_true",
            help="Also re-dispatch the terminal `done` call (default: skip).",
        )
        parser.add_argument(
            "--json", action="store_true",
            help="Emit the result as JSON (for piping into jq / scripts).",
        )
        parser.add_argument(
            "--show-diverged-only", action="store_true",
            help="Only print calls whose result diverged.",
        )

    def handle(self, *args, **options):
        from owdb_django.wrestlebot.agents.replay import replay_session

        sid = options["session_id"]
        dry_run = not options["apply"]
        skip_done = not options["include_done"]

        self.stdout.write(self.style.HTTP_INFO(
            f"\n=== Replay AgentSession #{sid} "
            f"({'dry-run' if dry_run else 'APPLY'}) ===\n"
        ))

        try:
            result = replay_session(
                sid, dry_run=dry_run, skip_done=skip_done,
            )
        except Exception as e:
            self.stderr.write(self.style.ERROR(
                f"Replay failed: {type(e).__name__}: {e}"
            ))
            return

        if options["json"]:
            self.stdout.write(json.dumps(result.to_dict(), default=str, indent=2))
            return

        self.stdout.write(
            f"  bot              {result.bot}\n"
            f"  total_calls      {result.total_calls}\n"
            f"  diverged         {result.diverged}\n"
            f"  new_errors       {result.new_errors}  (previously OK, now fail)\n"
            f"  fixed_errors     {result.fixed_errors}  (previously failed, now OK)\n"
        )

        if not result.calls:
            self.stdout.write("  (no calls to replay)")
            return

        self.stdout.write("\nCall-by-call:")
        for c in result.calls:
            if options["show_diverged_only"] and not c.diverged:
                continue
            marker = "  "
            if c.diverged and c.new_error and not c.original_error:
                marker = "✗ "
            elif c.original_error and not c.new_error:
                marker = "✓ "
            elif c.diverged:
                marker = "∆ "
            self.stdout.write(
                f"{marker}#{c.sequence:>3}  {c.tool_name:<32}  "
                f"({c.duration_ms} ms)"
            )
            if c.diverged or c.new_error:
                args_compact = json.dumps(c.arguments, default=str)[:120]
                self.stdout.write(f"        args: {args_compact}")
                if c.original_error or c.new_error:
                    self.stdout.write(
                        f"        old_err: {c.original_error[:160] or '(ok)'}\n"
                        f"        new_err: {c.new_error[:160] or '(ok)'}"
                    )
                else:
                    self.stdout.write(
                        f"        old: {c.original_summary[:120]}\n"
                        f"        new: {c.new_summary[:120]}"
                    )

        self.stdout.write("")
        if dry_run:
            self.stdout.write(self.style.SUCCESS(
                "Dry-run complete. No DB changes. "
                "Pass --apply to re-execute for real."
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                "Replay applied. Session's final_summary now records the replay."
            ))
