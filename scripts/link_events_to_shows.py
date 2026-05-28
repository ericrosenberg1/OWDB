"""
Link Event records to TVShow records based on name patterns.
"""

import re
import django
import os
import sys

# Setup Django
sys.path.insert(0, "/Users/eric/Code/wrestlingdb")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "owdb_django.settings")
django.setup()

from owdb_django.owdbapp.models import TVShow, Event

# Mapping from TVShow names to regex patterns that match event names
SHOW_PATTERNS = {
    # WWE Weekly Shows
    "WWE Raw": [r"WWE Raw", r"WWF Raw", r"Raw is War", r"Monday Night Raw"],
    "WWE SmackDown": [r"WWE SmackDown", r"SmackDown", r"WWF SmackDown"],
    "WWE NXT": [r"WWE NXT", r"NXT #", r"NXT 2\.0"],
    "WWE Main Event": [r"WWE Main Event", r"Main Event #"],
    "WWE Superstars": [
        r"WWE Superstars",
        r"WWF Superstars",
        r"WWF Wrestling Challenge",
        r"WWF Prime Time",
    ],
    "Saturday Night's Main Event": [r"Saturday Night.?s Main Event", r"SNME"],
    # WWE PPVs
    "WWE WrestleMania": [r"WrestleMania"],
    "WWE Royal Rumble": [r"Royal Rumble"],
    "WWE SummerSlam": [r"SummerSlam"],
    "WWE Survivor Series": [r"Survivor Series"],
    "WWE Money in the Bank": [r"Money in the Bank"],
    "WWE Elimination Chamber": [r"Elimination Chamber"],
    "WWE Hell in a Cell": [r"Hell in a Cell"],
    "WWE Backlash": [r"Backlash"],
    "WWE Extreme Rules": [r"Extreme Rules"],
    "WWE No Mercy": [r"No Mercy"],
    "WWE Clash of Champions": [r"Clash of Champions"],
    "WWE Crown Jewel": [r"Crown Jewel"],
    "WWE TLC": [r"TLC:?\s", r"Tables.?Ladders.?Chairs"],
    "WWE Fastlane": [r"Fastlane"],
    "WWE Payback": [r"Payback"],
    "WWE Night of Champions": [r"Night of Champions"],
    "WWE King of the Ring": [r"King of the Ring"],
    "WWE In Your House": [r"In Your House"],
    "WWE Bad Blood": [r"Bad Blood"],
    "WWE Armageddon": [r"Armageddon"],
    "WWE Vengeance": [r"Vengeance"],
    "WWE Judgement Day": [r"Judgement Day", r"Judgment Day"],
    "WWE Unforgiven": [r"Unforgiven"],
    "WWE No Way Out": [r"No Way Out"],
    "WWE Taboo Tuesday": [r"Taboo Tuesday"],
    "WWE Cyber Sunday": [r"Cyber Sunday"],
    "WWE The Great American Bash": [r"Great American Bash"],
    "WWE One Night Stand": [r"One Night Stand"],
    "WWE December to Dismember": [r"December to Dismember"],
    "WWE Breaking Point": [r"Breaking Point"],
    "WWE Over the Limit": [r"Over the Limit"],
    "WWE Capitol Punishment": [r"Capitol Punishment"],
    "WWE Fatal 4-Way": [r"Fatal.?4.?Way"],
    "WWE Bragging Rights": [r"Bragging Rights"],
    "WWE Day 1": [r"Day 1(?!\d)"],
    "WWE Clash at the Castle": [r"Clash at the Castle"],
    # WCW Shows
    "WCW Monday Nitro": [r"WCW Monday Nitro", r"Monday Nitro", r"Nitro #"],
    "WCW Thunder": [r"WCW Thunder", r"Thunder #"],
    "WCW Saturday Night": [r"WCW Saturday Night"],
    "WCW Starrcade": [r"Starrcade"],
    "WCW Halloween Havoc": [r"Halloween Havoc"],
    "WCW Bash at the Beach": [r"Bash at the Beach"],
    "WCW Superbrawl": [r"SuperBrawl", r"Superbrawl"],
    "WCW Uncensored": [r"Uncensored"],
    "WCW Spring Stampede": [r"Spring Stampede"],
    "WCW Slamboree": [r"Slamboree"],
    "WCW Great American Bash": [r"Great American Bash"],
    "WCW Road Wild": [r"Road Wild", r"Hog Wild"],
    "WCW Fall Brawl": [r"Fall Brawl"],
    "WCW World War 3": [r"World War 3", r"World War III"],
    "WCW Souled Out": [r"Souled Out"],
    "WCW New Blood Rising": [r"New Blood Rising"],
    "WCW Mayhem": [r"Mayhem(?!\s+in)"],
    "WCW Greed": [r"Greed"],
    "WCW Sin": [r"WCW Sin\b"],
    "WCW Clash of the Champions": [r"Clash of the Champions"],
    "WCW Power Hour": [r"Power Hour"],
    "WCW Main Event": [r"WCW Main Event"],
    "WCW Pro": [r"WCW Pro"],
    "WCW Worldwide": [r"WCW Worldwide", r"Worldwide"],
    # ECW Shows
    "ECW Hardcore TV": [r"ECW Hardcore", r"Hardcore TV"],
    "ECW on TNN": [r"ECW on TNN"],
    "ECW Barely Legal": [r"Barely Legal"],
    "ECW November to Remember": [r"November to Remember"],
    "ECW Heat Wave": [r"Heat ?Wave", r"Heatwave"],
    "ECW Living Dangerously": [r"Living Dangerously"],
    "ECW Guilty as Charged": [r"Guilty as Charged"],
    "ECW Anarchy Rulz": [r"Anarchy Rulz"],
    "ECW Cyberslam": [r"Cyberslam"],
    # AEW Shows
    "AEW Dynamite": [r"AEW Dynamite", r"Dynamite #"],
    "AEW Rampage": [r"AEW Rampage", r"Rampage #"],
    "AEW Collision": [r"AEW Collision", r"Collision #"],
    "AEW Dark": [r"AEW Dark(?!:)"],
    "AEW Dark: Elevation": [r"AEW Dark: Elevation", r"Elevation #"],
    "AEW Double or Nothing": [r"Double or Nothing"],
    "AEW All Out": [r"All Out"],
    "AEW Full Gear": [r"Full Gear"],
    "AEW Revolution": [r"Revolution"],
    "AEW Dynasty": [r"Dynasty"],
    "AEW Forbidden Door": [r"Forbidden Door"],
    "AEW All In": [r"All In"],
    "AEW Worlds End": [r"World'?s End"],
    "AEW Grand Slam": [r"Grand Slam"],
    # TNA/Impact Shows
    "Impact Wrestling": [r"Impact Wrestling", r"TNA Impact", r"IMPACT!", r"iMPACT!"],
    "TNA Xplosion": [r"Xplosion"],
    "TNA Bound for Glory": [r"Bound for Glory"],
    "TNA Slammiversary": [r"Slammiversary"],
    "TNA Lockdown": [r"Lockdown"],
    "TNA Genesis": [r"Genesis"],
    "TNA Final Resolution": [r"Final Resolution"],
    "TNA Turning Point": [r"Turning Point"],
    "TNA No Surrender": [r"No Surrender"],
    "TNA Victory Road": [r"Victory Road"],
    "TNA Against All Odds": [r"Against All Odds"],
    "TNA Sacrifice": [r"Sacrifice"],
    "TNA Destination X": [r"Destination X"],
    "TNA Hard Justice": [r"Hard Justice"],
    "TNA Hardcore Justice": [r"Hardcore Justice"],
    # ROH Shows
    "ROH TV": [r"ROH TV", r"Ring of Honor TV"],
    "ROH Final Battle": [r"Final Battle"],
    "ROH Supercard of Honor": [r"Supercard of Honor"],
    # NJPW Shows
    "NJPW Wrestle Kingdom": [r"Wrestle Kingdom"],
    "NJPW G1 Climax": [r"G1 Climax"],
    "NJPW World Tag League": [r"World Tag League"],
}


def main():
    # Build TVShow lookup
    show_lookup = {}
    for show in TVShow.objects.all():
        show_lookup[show.name] = show

    print(f"Found {len(show_lookup)} TV shows")

    linked_count = 0
    not_linked = []

    events = Event.objects.filter(tv_show__isnull=True).select_related("promotion")
    total = events.count()
    print(f"Processing {total} unlinked events...")

    for i, event in enumerate(events):
        matched = False
        for show_name, patterns in SHOW_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, event.name, re.IGNORECASE):
                    if show_name in show_lookup:
                        event.tv_show = show_lookup[show_name]
                        event.save(update_fields=["tv_show"])
                        linked_count += 1
                        matched = True
                        break
            if matched:
                break

        if not matched and event.name:
            not_linked.append(event.name)

        if (i + 1) % 1000 == 0:
            print(f"  Processed {i + 1}/{total} events, linked {linked_count}...")

    print("\n=== Results ===")
    print(f"Events linked to TV shows: {linked_count}")
    print(f"Events not linked: {len(not_linked)}")

    print("\nEvents not linked (sample):")
    from collections import Counter

    unlinked_counter = Counter(not_linked)
    for name, count in unlinked_counter.most_common(30):
        print(f"  {count}x: {name[:70]}")


if __name__ == "__main__":
    main()
