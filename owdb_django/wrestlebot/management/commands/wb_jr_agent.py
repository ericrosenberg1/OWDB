"""
wb_jr_agent — run one Good Ol' JR session.

Good Ol' JR (named for Jim Ross, the encyclopedic voice of pro
wrestling) is the data-adding agent. His mission is to build the most
comprehensive wrestling database ever assembled, one verified entity
at a time. Every accuracy guard wired into the pipeline still applies.

Use:
    python manage.py wb_jr_agent                       # default goal
    python manage.py wb_jr_agent --task "..."          # custom task
    python manage.py wb_jr_agent --max-tool-calls 60   # bigger budget
"""

from __future__ import annotations

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Run one Good Ol' JR session (data-adding agent, Jim Ross)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--task", type=str, default="", help="Goal for this session. If empty, uses default."
        )
        parser.add_argument(
            "--max-tool-calls",
            type=int,
            default=40,
            help="Cap on tool invocations per session (default 40).",
        )
        parser.add_argument(
            "--max-input-tokens",
            type=int,
            default=200_000,
            help="Cap on cumulative input tokens (default 200k).",
        )
        parser.add_argument(
            "--max-iterations", type=int, default=60, help="Cap on model round-trips (default 60)."
        )
        parser.add_argument(
            "--model", type=str, default="", help="Override Claude model (defaults to Sonnet 4.6)."
        )

    def handle(self, *args, **options):
        from owdb_django.wrestlebot.agents.jr_agent import run_jr

        self.stdout.write(
            self.style.SUCCESS(
                "\n=== Good Ol' JR — Jim Ross — Building the most "
                "comprehensive wrestling database ever assembled ===\n"
            )
        )
        result = run_jr(
            task=options["task"] or None,
            max_tool_calls=options["max_tool_calls"],
            max_input_tokens=options["max_input_tokens"],
            max_iterations=options["max_iterations"],
            model=options["model"] or None,
        )
        self.stdout.write("\nResults:")
        self.stdout.write(f"  session_id           {result.session_id}")
        self.stdout.write(f"  outcome              {result.outcome}")
        self.stdout.write(f"  tool_calls_used      {result.tool_calls_used}")
        self.stdout.write(f"  input_tokens_used    {result.input_tokens_used}")
        self.stdout.write(f"  output_tokens_used   {result.output_tokens_used}")
        self.stdout.write("")
        self.stdout.write(self.style.HTTP_INFO("Final summary:"))
        for line in (result.final_summary or "").splitlines():
            self.stdout.write(f"  {line}")
