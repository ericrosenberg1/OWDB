"""
wb_al_agent — run one Al Snow session.

Al Snow (named for the real wrestler-turned-trainer who ran OVW and
mentored on Tough Enough) makes existing entries better. He links
wrestlers to the promotions they actually worked for, resolves
mentions, surfaces missing entities through gaps in existing content,
and rotates through the roster to keep it fresh.

Use:
    python manage.py wb_al_agent
    python manage.py wb_al_agent --task "Focus on promotion-linking sweep."
"""

from __future__ import annotations

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Run one Al Snow session (interlinking + graph improvement)."

    def add_arguments(self, parser):
        parser.add_argument("--task", type=str, default="",
                            help="Goal for this session. If empty, uses default.")
        parser.add_argument("--max-tool-calls", type=int, default=40,
                            help="Cap on tool invocations per session (default 40).")
        parser.add_argument("--max-input-tokens", type=int, default=200_000,
                            help="Cap on cumulative input tokens (default 200k).")
        parser.add_argument("--max-iterations", type=int, default=60,
                            help="Cap on model round-trips (default 60).")
        parser.add_argument("--model", type=str, default="",
                            help="Override Claude model (defaults to Sonnet 4.6).")

    def handle(self, *args, **options):
        from owdb_django.wrestlebot.agents.al_agent import run_al

        self.stdout.write(self.style.SUCCESS(
            "\n=== Al Snow — Make every entry better. "
            "Surface every connection. ===\n"
        ))
        result = run_al(
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
