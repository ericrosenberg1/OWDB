"""
Curated catalog of professional-wrestling video games for discovery.

Each entry maps a stable internal slug to a tuple of Wikipedia title
fallbacks. The discovery pipeline (`games_discovery.py`) tries each title
in order until one resolves to a real Wikipedia article, then runs the
standard fetch → extract → persist pipeline (same accuracy contract every
other entity type uses).

Coverage philosophy
-------------------
Like `TITLE_HISTORY_PAGES`, this is a SEED list, not an exhaustive
catalogue. Any game whose Wikipedia article isn't found just gets skipped
— the safer behaviour is "miss a game" than "fabricate metadata".

Eras grouped roughly chronologically. Each entry's primary fallback is
the page title that exists as of the registry's last edit; secondary
fallbacks cover Wikipedia rename events. Many platforms ship the SAME
game under different titles by region (e.g. *WWF Royal Rumble* on Genesis
vs. SNES was the same game with different roster art) — those collapse
into one entry whose `wrestlers` M2M then expands across the union.

Skipping anything is harmless: a missing seed never fakes a row.
"""

from __future__ import annotations


# Each value: ordered tuple of Wikipedia page title fallbacks. The
# discovery code calls `_first_existing(titles)` (same helper the
# title-history extractor uses).
WRESTLING_GAME_SEEDS: dict[str, tuple[str, ...]] = {
    # =======================================================================
    # PRE-1990 — the arcade + early home era
    # =======================================================================
    "champion_wrestler":          ("Champion Wrestler",
                                   "Champion Pro Wrestling"),
    "ring_king":                  ("Ring King",),
    "tag_team_wrestling":         ("Tag Team Wrestling (video game)",
                                   "Tag Team Wrestling"),
    "appoooh":                    ("Appoooh",),
    "pro_wrestling_nes":          ("Pro Wrestling (NES video game)",
                                   "Pro Wrestling (NES)",),
    "mat_mania":                  ("Mat Mania",),
    "mat_mania_challenge":        ("Mat Mania Challenge",),
    "the_main_event":             ("The Main Event (arcade game)",
                                   "The Main Event (1988 video game)"),
    "mania_challenge":            ("Mania Challenge",),
    "wrestlefest":                ("WWF WrestleFest",
                                   "WrestleFest"),
    "wrestlemania_1989":          ("WWF WrestleMania (1989 video game)",
                                   "WWF WrestleMania (video game)"),

    # =======================================================================
    # 16-bit era (Genesis / SNES / Game Boy) — the WWF heyday
    # =======================================================================
    "wwf_super_wrestlemania":     ("WWF Super WrestleMania",),
    "wwf_royal_rumble":           ("WWF Royal Rumble (video game)",
                                   "WWF Royal Rumble (1993 video game)"),
    "wwf_raw_1994":               ("WWF Raw (1994 video game)",
                                   "WWF Raw (video game)"),
    "wwf_king_of_the_ring":       ("WWF King of the Ring (video game)",
                                   "WWF King of the Ring (1993 video game)"),
    "wcw_world_championship_wrestling": (
        "WCW World Championship Wrestling (video game)",
        "WCW World Championship Wrestling (1989 video game)",
    ),
    "wcw_super_brawl":            ("WCW Super Brawl Wrestling",),
    "wcw_wrestling":              ("WCW Wrestling",),
    "ringside_angel":             ("Ringside Angel",),
    "natsume_championship_wrestling": ("Natsume Championship Wrestling",),
    "saturday_night_slammasters": ("Saturday Night Slam Masters",),
    "muscle_bomber":              ("Muscle Bomber",
                                   "Muscle Bomber Duo"),

    # =======================================================================
    # PS1 / N64 — AKI Corporation revolution + WCW vs. WWF
    # =======================================================================
    "wcw_vs_the_world":           ("WCW vs. the World",),
    "wcw_nwo_world_tour":         ("WCW/nWo World Tour",
                                   "WCW vs. nWo: World Tour"),
    "wcw_vs_nwo_revenge":         ("WCW/nWo Revenge",
                                   "WCW vs. nWo: Revenge"),
    "wcw_mayhem":                 ("WCW Mayhem",),
    "wcw_backstage_assault":      ("WCW Backstage Assault",),
    "wcw_thunder":                ("WCW Thunder (video game)",
                                   "WCW Thunder"),
    "wcw_nitro":                  ("WCW Nitro (video game)",
                                   "WCW Nitro"),
    "wwf_in_your_house":          ("WWF In Your House (video game)",
                                   "WWF In Your House"),
    "wwf_warzone":                ("WWF War Zone",
                                   "WWF Warzone"),
    "wwf_attitude":               ("WWF Attitude",),
    "wwf_wrestlemania_2000":      ("WWF WrestleMania 2000",),
    "wwf_no_mercy":               ("WWF No Mercy",),
    "wwf_smackdown":              ("WWF SmackDown!",
                                   "WWF SmackDown! (video game)"),
    "wwf_smackdown_2":            ("WWF SmackDown! 2: Know Your Role",),
    "ecw_hardcore_revolution":    ("ECW Hardcore Revolution",),
    "ecw_anarchy_rulz":           ("ECW Anarchy Rulz",
                                   "ECW Anarchy Rulz!"),
    "wwf_betrayal":               ("WWF Betrayal",),
    "wwf_road_to_wrestlemania":   ("WWF Road to WrestleMania",),

    # =======================================================================
    # 6th gen (PS2 / Xbox / GameCube / GBA) — SmackDown! series + Day of Reckoning
    # =======================================================================
    "wwf_smackdown_just_bring_it": ("WWF SmackDown! Just Bring It",),
    "wwe_smackdown_shut_your_mouth": ("WWE SmackDown! Shut Your Mouth",),
    "wwe_smackdown_here_comes_the_pain": (
        "WWE SmackDown! Here Comes the Pain",
    ),
    "wwe_smackdown_vs_raw":       ("WWE SmackDown! vs. Raw",
                                   "WWE SmackDown vs. Raw"),
    "wwe_smackdown_vs_raw_2006":  ("WWE SmackDown! vs. Raw 2006",
                                   "WWE SmackDown vs. Raw 2006"),
    "wwe_smackdown_vs_raw_2007":  ("WWE SmackDown vs. Raw 2007",),
    "wwe_smackdown_vs_raw_2008":  ("WWE SmackDown vs. Raw 2008",),
    "wwe_smackdown_vs_raw_2009":  ("WWE SmackDown vs. Raw 2009",),
    "wwe_smackdown_vs_raw_2010":  ("WWE SmackDown vs. Raw 2010",),
    "wwe_smackdown_vs_raw_2011":  ("WWE SmackDown vs. Raw 2011",),
    "wwe_wrestlemania_x8":        ("WWE WrestleMania X8",),
    "wwe_wrestlemania_xix":       ("WWE WrestleMania XIX",),
    "wwe_day_of_reckoning":       ("WWE Day of Reckoning",),
    "wwe_day_of_reckoning_2":     ("WWE Day of Reckoning 2",),
    "wwe_crush_hour":             ("WWE Crush Hour",),
    "wwf_raw_2002":               ("WWF Raw (2002 video game)",
                                   "WWE Raw (video game)"),
    "wwe_raw_2":                  ("WWE Raw 2",),
    "wwe_aftershock":             ("WWE Aftershock",),
    "showdown_legends":           ("Showdown: Legends of Wrestling",),
    "legends_of_wrestling":       ("Legends of Wrestling",),
    "legends_of_wrestling_ii":    ("Legends of Wrestling II",),
    "ultimate_wrestling_legends": ("Ultimate Pro Wrestling",),  # alt
    "rumble_roses":               ("Rumble Roses",),
    "rumble_roses_xx":            ("Rumble Roses XX",),
    "backyard_wrestling":         ("Backyard Wrestling: Don't Try This at Home",),
    "backyard_wrestling_2":       ("Backyard Wrestling 2: There Goes the Neighborhood",),
    "tna_impact":                 ("TNA Impact!",
                                   "TNA Impact! (video game)"),
    "tna_impact_cross_the_line":  ("TNA Impact: Cross the Line",),

    # =======================================================================
    # 7th gen onward (PS3 / Xbox 360 / PS4 / PS5 / Switch) — WWE 2K era
    # =======================================================================
    "wwe_legends_of_wrestlemania": ("WWE Legends of WrestleMania",),
    "wwe_smackdown_vs_raw_2009b": ("WWE SmackDown vs. Raw 2009",),  # dup-safe
    "wwe_all_stars":              ("WWE All Stars",),
    "wwe_12":                     ("WWE '12",),
    "wwe_13":                     ("WWE '13",),
    "wwe_2k14":                   ("WWE 2K14",),
    "wwe_2k15":                   ("WWE 2K15",),
    "wwe_2k16":                   ("WWE 2K16",),
    "wwe_2k17":                   ("WWE 2K17",),
    "wwe_2k18":                   ("WWE 2K18",),
    "wwe_2k19":                   ("WWE 2K19",),
    "wwe_2k20":                   ("WWE 2K20",),
    "wwe_2k_battlegrounds":       ("WWE 2K Battlegrounds",),
    "wwe_2k22":                   ("WWE 2K22",),
    "wwe_2k23":                   ("WWE 2K23",),
    "wwe_2k24":                   ("WWE 2K24",),
    "wwe_2k25":                   ("WWE 2K25",),
    "wwe_2k_mobile":              ("WWE Mayhem",
                                   "WWE SuperCard",
                                   "WWE Champions"),
    "aew_fight_forever":          ("AEW: Fight Forever",
                                   "AEW Fight Forever"),
    "tna_wrestling":              ("TNA Wrestling (video game)",),
    "lucha_libre_aaa":            ("Lucha Libre AAA: Héroes del Ring",
                                   "Lucha Libre AAA"),

    # =======================================================================
    # Series-level / multi-installment Wikipedia hub articles (these list
    # every entry in a franchise and are a goldmine of cross-references)
    # =======================================================================
    "wwe_2k_series":              ("WWE 2K",
                                   "WWE 2K (series)"),
    "wwf_wcw_smackdown_series":   ("List of WWE video games",
                                   "WWF/WWE video games"),
    "fire_pro_wrestling_series":  ("Fire Pro Wrestling",
                                   "Fire Pro Wrestling (series)",
                                   "Fire Pro Wrestling World"),
    "wrestle_kingdom_series":     ("Wrestle Kingdom (video game series)",
                                   "Wrestle Kingdom"),
    "njpw_world_pro_wrestling":   ("New Japan Pro-Wrestling World",
                                   "World Pro Wrestling (TV series)"),
    "kings_of_wrestling_series":  ("MDickie",  # the WrestleMaster / WR series creator
                                   "WrestleMaster"),
    "wrestling_revolution_3d":    ("Wrestling Revolution 3D",
                                   "Wrestling Revolution"),

    # =======================================================================
    # Indie / experimental / mobile that DO have notability
    # =======================================================================
    "kayfabe_mgmt":               ("Kayfabe (video game)",
                                   "Wrestling Empire"),
    "wwe_wrestlefest_2012":       ("WWE WrestleFest",),
    "wwe_super_card":             ("WWE SuperCard",),
    "wwe_champions":              ("WWE Champions (video game)",
                                   "WWE Champions"),
    "wwe_mayhem":                 ("WWE Mayhem",),

    # =======================================================================
    # List articles — Wikipedia hub pages that list dozens of games
    # =======================================================================
    "list_wwe_video_games":       ("List of WWE video games",),
    "list_professional_wrestling_video_games": (
        "List of professional wrestling video games",
    ),
}


def all_slugs() -> tuple[str, ...]:
    """Stable iteration order of every seed slug."""
    return tuple(WRESTLING_GAME_SEEDS.keys())
