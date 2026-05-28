"""
Discovery stage — produce candidate names to feed the rest of the pipeline.

v3.0 strategy: enumerate Wikipedia category pages. This is a low-cost API call
and gives us names with a strong implicit signal that a Wikipedia page exists
for that wrestler.

Returns a list of candidate dicts; never writes to the DB. The caller decides
which candidates to fetch.
"""

from __future__ import annotations

import logging
from typing import Iterable

from ..sources.wikipedia import WikipediaAdapter

logger = logging.getLogger(__name__)


# Notability-weighted category list. Earlier entries get priority — Hall of
# Fame inductees first (most likely to have rich Wikipedia pages and stable
# careers worth indexing), then nationality-based categories as a long tail.
#
# This ordering is intentional: a fresh DB indexes the *notable* wrestlers
# first instead of alphabetically obscure ones.
HOF_CATEGORIES: tuple[str, ...] = (
    "Category:WWE_Hall_of_Fame_inductees",
    "Category:WCW_Hall_of_Fame_inductees",
    "Category:Professional_Wrestling_Hall_of_Fame_and_Museum_inductees",
    "Category:Wrestling_Observer_Newsletter_Hall_of_Fame_inductees",
    "Category:NWA_Hall_of_Fame_(National_Wrestling_Alliance)_inductees",
    "Category:Impact_Hall_of_Fame_inductees",
)

CHAMPION_CATEGORIES: tuple[str, ...] = (
    "Category:WWE_Champions",
    "Category:WCW_World_Heavyweight_Champions",
    "Category:NWA_World_Heavyweight_Champions",
    "Category:AEW_World_Champions",
    "Category:IWGP_Heavyweight_Champions",
    "Category:WWE_Women's_Champions",
    "Category:WWE_Universal_Champions",
)

NATIONALITY_CATEGORIES: tuple[str, ...] = (
    "Category:American_male_professional_wrestlers",
    "Category:American_female_professional_wrestlers",
    "Category:Canadian_male_professional_wrestlers",
    "Category:Canadian_female_professional_wrestlers",
    "Category:British_male_professional_wrestlers",
    "Category:British_female_professional_wrestlers",
    "Category:Japanese_male_professional_wrestlers",
    "Category:Japanese_female_professional_wrestlers",
    "Category:Mexican_male_professional_wrestlers",
    "Category:Mexican_female_professional_wrestlers",
)


# Full ordered list (notable first). Earlier entries are tried first by the
# discovery loop; per_category_limit caps how deep we go in each.
WRESTLER_CATEGORIES: tuple[str, ...] = (
    *HOF_CATEGORIES,
    *CHAMPION_CATEGORIES,
    *NATIONALITY_CATEGORIES,
)


# Hand-curated seed of "obviously want this in the DB" wrestlers. Wikipedia
# page titles. Used by discover_wrestlers(seed=True) to bootstrap a useful
# initial corpus regardless of what categories return.
NOTABLE_SEED: tuple[str, ...] = (
    # Modern era
    "Roman Reigns",
    "Cody Rhodes",
    "Seth Rollins",
    "Becky Lynch",
    "Bianca Belair",
    "Rhea Ripley",
    "Jey Uso",
    "Jimmy Uso",
    "Sami Zayn",
    "Kevin Owens",
    "Sasha Banks",
    "Charlotte Flair",
    "Drew McIntyre",
    "Bayley",
    "AJ Styles",
    "Finn Bálor",
    # AEW era
    "Kenny Omega",
    "Adam Page",
    "Jon Moxley",
    "MJF",
    "Chris Jericho",
    "Bryan Danielson",
    "Will Ospreay",
    "Toni Storm",
    "Mercedes Moné",
    # Modern Japanese
    "Kazuchika Okada",
    "Hiroshi Tanahashi",
    "Tetsuya Naito",
    # Legends
    "Bret Hart",
    "Shawn Michaels",
    "Hulk Hogan",
    "Stone Cold Steve Austin",
    "The Rock",
    "Ric Flair",
    "Andre the Giant",
    "Triple H",
    "Undertaker",
    "Kane",
    "Eddie Guerrero",
    "Chris Benoit",
    "Owen Hart",
    "Randy Savage",
    "Roddy Piper",
    "Mick Foley",
    "Edge",
    "John Cena",
    "Randy Orton",
    "Batista",
    "Rey Mysterio",
    "Trish Stratus",
    "Lita",
    "Chyna",
    # Classic
    "Lou Thesz",
    "Bruno Sammartino",
    "Verne Gagne",
    "Harley Race",
    "Dusty Rhodes",
    "Terry Funk",
    "Mil Máscaras",
    "El Santo",
    "Antonio Inoki",
    "Giant Baba",
    "Rikidozan",
    # Other notable
    "Abdullah the Butcher",
    "Sting",
    "Goldberg",
    "Tank Abbott",
    "Kurt Angle",
    "Brock Lesnar",
)


# ---------------------------------------------------------------- events

EVENT_CATEGORIES: tuple[str, ...] = (
    # Modern majors
    "Category:WWE_pay-per-view_events",
    "Category:WWE_in_the_United_States",
    "Category:AEW_pay-per-view_events",
    "Category:NXT_(WWE_brand)_pay-per-view_events",
    "Category:Impact_Wrestling_pay-per-view_events",
    "Category:Ring_of_Honor_pay-per-view_events",
    # Historic majors
    "Category:WCW_pay-per-view_events",
    "Category:ECW_pay-per-view_events",
    # Japan
    "Category:NJPW_pay-per-view_events",
    "Category:All_Japan_Pro_Wrestling_pay-per-view_events",
    "Category:Pro_Wrestling_Noah_events",
    "Category:Dragon_Gate_(promotion)_events",
    # Lucha
    "Category:Lucha_Libre_AAA_Worldwide_pay-per-view_events",
    "Category:CMLL_pay-per-view_events",
    # Indie / smaller
    "Category:Game_Changer_Wrestling_pay-per-view_events",
    "Category:Major_League_Wrestling_pay-per-view_events",
    "Category:National_Wrestling_Alliance_pay-per-view_events",
    # WWE marquee event series
    "Category:Royal_Rumble",
    "Category:SummerSlam",
    "Category:Survivor_Series",
    "Category:WrestleMania",
    "Category:Money_in_the_Bank_(ladder_match)",
    "Category:Hell_in_a_Cell",
    "Category:Elimination_Chamber",
    "Category:NXT_TakeOver_events",
)


# ---------------------------------------------------------------- promotions

# Wikipedia categories that surface promotion pages. Ordered by likely
# notability so the discovery loop seeds well-known promotions first.
PROMOTION_CATEGORIES: tuple[str, ...] = (
    "Category:WWE",
    "Category:All_Elite_Wrestling",
    "Category:Total_Nonstop_Action_Wrestling",
    "Category:Ring_of_Honor",
    "Category:World_Championship_Wrestling",
    "Category:Extreme_Championship_Wrestling",
    "Category:New_Japan_Pro-Wrestling",
    "Category:All_Japan_Pro_Wrestling",
    "Category:Pro_Wrestling_Noah",
    "Category:Lucha_Libre_AAA_Worldwide",
    "Category:Consejo_Mundial_de_Lucha_Libre",
    "Category:American_professional_wrestling_promotions",
    "Category:British_professional_wrestling_promotions",
    "Category:Mexican_professional_wrestling_promotions",
    "Category:Japanese_professional_wrestling_promotions",
    "Category:Defunct_professional_wrestling_promotions_in_the_United_States",
    "Category:Independent_professional_wrestling_promotions_in_the_United_States",
)


# Hand-curated seed of promotions we want first-class entries for. Wikipedia
# page titles. Spans WWE subsidiaries (NXT brand, AAA partnership), modern
# majors, historic majors, Japan, lucha, and key independents.
NOTABLE_PROMOTION_SEED: tuple[str, ...] = (
    # WWE family
    "WWE",
    "WWE NXT",
    "WWE Raw",
    "WWE SmackDown",
    "WWE ID",  # WWE's new indie partnership
    "Lucha Libre AAA Worldwide",  # WWE partner / acquisition
    # Major modern
    "All Elite Wrestling",
    "Ring of Honor",
    "Total Nonstop Action Wrestling",  # current TNA / Impact
    "Impact Wrestling",
    "New Japan Pro-Wrestling",
    "All Japan Pro Wrestling",
    "Pro Wrestling Noah",
    "Dragon Gate (promotion)",
    "Stardom (puroresu)",
    "Pro Wrestling Zero1",
    "DDT Pro-Wrestling",
    # Lucha
    "Consejo Mundial de Lucha Libre",
    "International Wrestling Revolution Group",
    # American indies / smaller national
    "Game Changer Wrestling",
    "Major League Wrestling",
    "National Wrestling Alliance",
    "Combat Zone Wrestling",
    "Pro Wrestling Guerrilla",
    "Beyond Wrestling",
    "House of Glory",
    "Black Label Pro",
    "Wrestling Revolver",
    "Maple Leaf Pro Wrestling",
    # Developmental / regional
    "Ohio Valley Wrestling",  # OVW
    "Florida Championship Wrestling",
    "Deep South Wrestling",
    # Historic majors
    "World Championship Wrestling",
    "Extreme Championship Wrestling",
    "American Wrestling Association",
    "World Class Championship Wrestling",
    "Jim Crockett Promotions",
    "Stampede Wrestling",
    "Memphis Wrestling",
    # UK / Europe
    "Progress Wrestling",
    "Revolution Pro Wrestling",
    "wXw (German wrestling promotion)",
    "Insane Championship Wrestling",
    # Women-focused
    "Shimmer Women Athletes",
    "Shine Wrestling",
    "World Wonder Ring Stardom",
)

NOTABLE_EVENT_SEED: tuple[str, ...] = (
    # Foundational WWE PPVs (most have rich Wikipedia infoboxes)
    "WrestleMania I",
    "WrestleMania III",
    "WrestleMania VI",
    "WrestleMania X",
    "WrestleMania X-Seven",
    "WrestleMania XX",
    "WrestleMania 30",
    "WrestleMania 40",
    "SummerSlam (1988)",
    "SummerSlam (1992)",
    "SummerSlam (2002)",
    "Royal Rumble (1992)",
    "Royal Rumble (2000)",
    "Royal Rumble (2007)",
    "Survivor Series (1987)",
    "Survivor Series (1990)",
    "Survivor Series (1996)",
    "King of the Ring (1996)",
    "King of the Ring (1998)",
    # WCW
    "Starrcade (1983)",
    "Starrcade (1989)",
    "Starrcade (1997)",
    "Bash at the Beach (1996)",
    # ECW
    "ECW November to Remember (1994)",
    "ECW Heat Wave (1998)",
    # AEW
    "All Out (2019)",
    "Double or Nothing (2019)",
    "Revolution (2020)",
    "Full Gear (2020)",
    "AEW All In",
    "Forbidden Door (2022)",
    # NJPW
    "Wrestle Kingdom 9",
    "Wrestle Kingdom 13",
)


# ---------------------------------------------------------------- venues

VENUE_CATEGORIES: tuple[str, ...] = ("Category:Indoor_arenas_in_the_United_States",)

NOTABLE_VENUE_SEED: tuple[str, ...] = (
    "Madison Square Garden",
    "T-Mobile Arena",
    "AT&T Stadium",
    "MetLife Stadium",
    "Allstate Arena",
    "Staples Center",
    "Mercedes-Benz Superdome",
    "Tokyo Dome",
    "Wembley Stadium",
    "Greensboro Coliseum",
    "Caesars Superdome",
    "Toyota Center",
    "American Airlines Center",
    "Daily's Place",
)


def discover_events(
    per_category_limit: int = 10,
    total_limit: int = 30,
    include_seed: bool = True,
) -> list[str]:
    """Notability-ordered list of candidate event titles."""
    adapter = WikipediaAdapter()
    seen: set[str] = set()
    out: list[str] = []

    if include_seed:
        for title in NOTABLE_EVENT_SEED:
            if len(out) >= total_limit:
                return out
            if title in seen:
                continue
            seen.add(title)
            out.append(title)

    for cat in EVENT_CATEGORIES:
        if len(out) >= total_limit:
            break
        try:
            members = adapter.list_category_members(cat, limit=per_category_limit)
        except Exception as e:
            logger.warning("Event discovery failed for %s: %s", cat, e)
            continue
        for title in members:
            if len(out) >= total_limit:
                break
            if title.lower().startswith(("list of", "category:")):
                continue
            if title in seen:
                continue
            seen.add(title)
            out.append(title)

    logger.info("Discovered %d unique event candidates", len(out))
    return out


# ---------------------------------------------------------------- podcasts

# Wrestling podcasts are a high-leverage data source: each episode's show
# notes typically reference 5-50 wrestlers, titles, events, and feuds —
# so seeding the podcast graph indirectly grows everything else through
# mention-driven discovery.
PODCAST_CATEGORIES: tuple[str, ...] = (
    "Category:Professional_wrestling_podcasts",
    "Category:Sports_podcasts",  # very broad — small per_category_limit
)

NOTABLE_PODCAST_SEED: tuple[str, ...] = (
    # Conrad Thompson universe (huge mention surface)
    "Something to Wrestle with Bruce Prichard",
    "83 Weeks (podcast)",
    "Grilling JR",
    "Arn (podcast)",
    "What Happened When",
    "Strictly Business with Eric Bischoff",
    # Wrestler-hosted
    "Talk Is Jericho",
    "The Steve Austin Show",
    "The Stone Cold Podcast",
    "The Kurt Angle Show",
    "Foley Is Pod",
    "The Mark Henry Show",
    "Killing the Town with Storm and Cyrus",
    "The Two Man Power Trip of Wrestling",
    "Out of Character with Ryan Satin",
    # News / opinion
    "Wrestling Observer Radio",
    "Wade Keller Pro Wrestling Podcast",
    "Busted Open Radio",
    "The Pat McAfee Show",
    "Insight with Chris Van Vliet",
    "Notsam Wrestling",
    "The Bump (podcast)",
    "AEW Unrestricted",
    # Classic / archival
    "6:05 Superpodcast",
    "The Bischoff On Wrestling Podcast",
    "Prime Time with Sean Mooney",
    "MLW Radio",
)


def discover_podcasts(
    per_category_limit: int = 10,
    total_limit: int = 50,
    include_seed: bool = True,
) -> list[str]:
    """Notability-ordered list of candidate podcast titles."""
    adapter = WikipediaAdapter()
    seen: set[str] = set()
    out: list[str] = []

    if include_seed:
        for title in NOTABLE_PODCAST_SEED:
            if len(out) >= total_limit:
                return out
            if title in seen:
                continue
            seen.add(title)
            out.append(title)

    for cat in PODCAST_CATEGORIES:
        if len(out) >= total_limit:
            break
        try:
            members = adapter.list_category_members(cat, limit=per_category_limit)
        except Exception as e:
            logger.warning("Podcast discovery failed for %s: %s", cat, e)
            continue
        for title in members:
            if len(out) >= total_limit:
                break
            if title.lower().startswith(("list of", "category:")):
                continue
            if title in seen:
                continue
            seen.add(title)
            out.append(title)

    logger.info("Discovered %d unique podcast candidates", len(out))
    return out


def discover_promotions(
    per_category_limit: int = 10,
    total_limit: int = 40,
    include_seed: bool = True,
) -> list[str]:
    """Notability-ordered list of candidate promotion titles."""
    adapter = WikipediaAdapter()
    seen: set[str] = set()
    out: list[str] = []

    if include_seed:
        for title in NOTABLE_PROMOTION_SEED:
            if len(out) >= total_limit:
                return out
            if title in seen:
                continue
            seen.add(title)
            out.append(title)

    for cat in PROMOTION_CATEGORIES:
        if len(out) >= total_limit:
            break
        try:
            members = adapter.list_category_members(cat, limit=per_category_limit)
        except Exception as e:
            logger.warning("Promotion discovery failed for %s: %s", cat, e)
            continue
        for title in members:
            if len(out) >= total_limit:
                break
            if title.lower().startswith(("list of", "category:")):
                continue
            if title in seen:
                continue
            seen.add(title)
            out.append(title)

    logger.info("Discovered %d unique promotion candidates", len(out))
    return out


def discover_venues(
    per_category_limit: int = 10,
    total_limit: int = 20,
    include_seed: bool = True,
) -> list[str]:
    """Notability-ordered list of candidate venue titles."""
    adapter = WikipediaAdapter()
    seen: set[str] = set()
    out: list[str] = []

    if include_seed:
        for title in NOTABLE_VENUE_SEED:
            if len(out) >= total_limit:
                return out
            if title in seen:
                continue
            seen.add(title)
            out.append(title)

    for cat in VENUE_CATEGORIES:
        if len(out) >= total_limit:
            break
        try:
            members = adapter.list_category_members(cat, limit=per_category_limit)
        except Exception as e:
            logger.warning("Venue discovery failed for %s: %s", cat, e)
            continue
        for title in members:
            if len(out) >= total_limit:
                break
            if title.lower().startswith(("list of", "category:")):
                continue
            if title in seen:
                continue
            seen.add(title)
            out.append(title)

    logger.info("Discovered %d unique venue candidates", len(out))
    return out


def discover_wrestlers(
    categories: Iterable[str] = WRESTLER_CATEGORIES,
    per_category_limit: int = 10,
    total_limit: int = 50,
    include_seed: bool = True,
) -> list[str]:
    """
    Return a deduplicated list of candidate wrestler page titles, ordered
    by notability (HOF -> champions -> nationality).

    When include_seed=True (default), the curated NOTABLE_SEED list comes
    first, so a fresh DB starts with the wrestlers most likely to need
    indexing rather than alphabetically obscure ones.
    """
    adapter = WikipediaAdapter()
    seen: set[str] = set()
    out: list[str] = []

    if include_seed:
        for title in NOTABLE_SEED:
            if len(out) >= total_limit:
                return out
            if title in seen:
                continue
            seen.add(title)
            out.append(title)

    for cat in categories:
        if len(out) >= total_limit:
            break
        try:
            members = adapter.list_category_members(cat, limit=per_category_limit)
        except Exception as e:
            logger.warning("Discovery failed for %s: %s", cat, e)
            continue

        for title in members:
            if len(out) >= total_limit:
                break
            # Filter out non-wrestler subpages (e.g., "List of...", subcategories)
            if title.lower().startswith(("list of", "category:")):
                continue
            if title in seen:
                continue
            seen.add(title)
            out.append(title)

    logger.info("Discovered %d unique wrestler candidates", len(out))
    return out
