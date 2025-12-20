"""
Additional events seeding - more WrestleManias, SummerSlams, Royal Rumbles, and more.
"""
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from datetime import date
from owdb_django.owdbapp.models import (
    Wrestler, Promotion, Event, Match, Title, Venue
)


class Command(BaseCommand):
    help = 'Seed more historic wrestling events'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n=== Seeding More Events ===\n'))

        wwe = Promotion.objects.filter(abbreviation='WWE').first()
        wcw = Promotion.objects.filter(abbreviation='WCW').first()
        aew = Promotion.objects.filter(abbreviation='AEW').first()

        if wwe:
            self.seed_more_wwe(wwe)
        if wcw:
            self.seed_more_wcw(wcw)
        if aew:
            self.seed_more_aew(aew)

        self.stdout.write(self.style.SUCCESS('\n=== Done ===\n'))
        self.stdout.write(f'Total Events: {Event.objects.count()}')
        self.stdout.write(f'Total Matches: {Match.objects.count()}')

    def get_or_create_wrestler(self, name):
        slug = slugify(name)
        wrestler = Wrestler.objects.filter(slug=slug).first()
        if wrestler:
            return wrestler
        wrestler = Wrestler.objects.filter(name__iexact=name).first()
        if wrestler:
            return wrestler
        wrestler, _ = Wrestler.objects.get_or_create(name=name, defaults={'slug': slug})
        return wrestler

    def get_or_create_venue(self, name, location=None):
        slug = slugify(name)
        venue = Venue.objects.filter(slug=slug).first()
        if venue:
            return venue
        venue, _ = Venue.objects.get_or_create(name=name, defaults={'slug': slug, 'location': location or ''})
        return venue

    def get_title(self, title_name, promotion):
        title = Title.objects.filter(name__iexact=title_name).first()
        if not title:
            title = Title.objects.filter(name__icontains=title_name.replace('Championship', '').strip()).first()
        return title

    def create_event_with_matches(self, promotion, event_data, matches_data):
        event_date = event_data['date']
        slug = slugify(f"{event_data['name']}-{event_date.year}")

        event = Event.objects.filter(slug=slug).first()
        if event:
            return event, False

        venue = None
        if event_data.get('venue'):
            venue = self.get_or_create_venue(event_data['venue'], event_data.get('location'))

        event = Event.objects.create(
            name=event_data['name'],
            slug=slug,
            promotion=promotion,
            venue=venue,
            date=event_date,
            attendance=event_data.get('attendance'),
            about=event_data.get('about', '')
        )

        for i, match_data in enumerate(matches_data):
            self.create_match(event, match_data, i + 1, promotion)

        return event, True

    def create_match(self, event, match_data, order, promotion):
        wrestlers = []
        for name in match_data.get('wrestlers', []):
            wrestler = self.get_or_create_wrestler(name)
            if wrestler:
                wrestlers.append(wrestler)

        winner = None
        if match_data.get('winner'):
            winner = self.get_or_create_wrestler(match_data['winner'])

        title = None
        if match_data.get('title'):
            title = self.get_title(match_data['title'], promotion)

        match = Match.objects.create(
            event=event,
            match_text=match_data.get('match_text', ' vs '.join(match_data.get('wrestlers', []))),
            result=match_data.get('result', ''),
            winner=winner,
            match_type=match_data.get('match_type', ''),
            title=title,
            match_order=order,
            about=match_data.get('about', '')
        )

        for wrestler in wrestlers:
            match.wrestlers.add(wrestler)

        return match

    def seed_more_wwe(self, wwe):
        self.stdout.write('\n--- More WWE Events ---\n')
        events_added = 0

        # WrestleMania II (1986)
        e, c = self.create_event_with_matches(wwe, {
            'name': 'WrestleMania 2',
            'date': date(1986, 4, 7),
            'venue': 'Nassau Coliseum / Rosemont Horizon / Los Angeles Sports Arena',
            'attendance': 40000,
            'about': 'First WrestleMania held in multiple venues simultaneously.'
        }, [
            {'wrestlers': ['Mr. T', 'Roddy Piper'], 'winner': 'Mr. T', 'match_type': 'Boxing Match'},
            {'wrestlers': ['Randy Savage', 'George Steele'], 'winner': 'Randy Savage', 'title': 'WWF Intercontinental Championship', 'match_type': 'IC Title Match'},
            {'wrestlers': ['Dream Team', 'British Bulldogs'], 'winner': 'British Bulldogs', 'title': 'WWF Tag Team Championship', 'match_type': 'Tag Title Match'},
            {'wrestlers': ['Hulk Hogan', 'King Kong Bundy'], 'winner': 'Hulk Hogan', 'title': 'WWF Championship', 'match_type': 'Steel Cage Match'},
        ])
        if c:
            self.stdout.write(f'  + WrestleMania 2')
            events_added += 1

        # WrestleMania IV (1988)
        e, c = self.create_event_with_matches(wwe, {
            'name': 'WrestleMania IV',
            'date': date(1988, 3, 27),
            'venue': 'Trump Plaza',
            'location': 'Atlantic City, New Jersey',
            'attendance': 18165,
            'about': 'WWF Championship tournament won by Randy Savage.'
        }, [
            {'wrestlers': ['Randy Savage', 'Ted DiBiase'], 'winner': 'Randy Savage', 'title': 'WWF Championship', 'match_type': 'Tournament Final', 'about': 'Savage won the vacant WWF Championship with help from Hulk Hogan.'},
            {'wrestlers': ['Ultimate Warrior', 'Hercules'], 'winner': 'Ultimate Warrior', 'match_type': 'Singles Match'},
            {'wrestlers': ['Demolition', 'Strike Force'], 'winner': 'Demolition', 'title': 'WWF Tag Team Championship', 'match_type': 'Tag Title Match'},
        ])
        if c:
            self.stdout.write(f'  + WrestleMania IV')
            events_added += 1

        # WrestleMania V (1989)
        e, c = self.create_event_with_matches(wwe, {
            'name': 'WrestleMania V',
            'date': date(1989, 4, 2),
            'venue': 'Trump Plaza',
            'location': 'Atlantic City, New Jersey',
            'attendance': 18946,
            'about': 'The Mega Powers Explode - Hulk Hogan vs Randy Savage.'
        }, [
            {'wrestlers': ['Hulk Hogan', 'Randy Savage'], 'winner': 'Hulk Hogan', 'title': 'WWF Championship', 'match_type': 'WWF Championship', 'about': 'The Mega Powers explode. Hogan won the WWF Title from Savage.'},
            {'wrestlers': ['Ultimate Warrior', 'Rick Rude'], 'winner': 'Rick Rude', 'title': 'WWF Intercontinental Championship', 'match_type': 'IC Title Match'},
            {'wrestlers': ['Demolition', 'Powers of Pain'], 'winner': 'Demolition', 'title': 'WWF Tag Team Championship', 'match_type': 'Tag Title Match'},
        ])
        if c:
            self.stdout.write(f'  + WrestleMania V')
            events_added += 1

        # WrestleMania VII (1991)
        e, c = self.create_event_with_matches(wwe, {
            'name': 'WrestleMania VII',
            'date': date(1991, 3, 24),
            'venue': 'Los Angeles Memorial Sports Arena',
            'location': 'Los Angeles, California',
            'attendance': 16158,
            'about': 'Featured the retirement match of Ultimate Warrior vs Randy Savage.'
        }, [
            {'wrestlers': ['Hulk Hogan', 'Sgt. Slaughter'], 'winner': 'Hulk Hogan', 'title': 'WWF Championship', 'match_type': 'WWF Championship'},
            {'wrestlers': ['Ultimate Warrior', 'Randy Savage'], 'winner': 'Ultimate Warrior', 'match_type': 'Retirement Match', 'about': 'Savage retired after losing. Elizabeth reunited with Savage.'},
            {'wrestlers': ['Undertaker', 'Jimmy Snuka'], 'winner': 'Undertaker', 'match_type': 'Singles Match'},
        ])
        if c:
            self.stdout.write(f'  + WrestleMania VII')
            events_added += 1

        # WrestleMania VIII (1992)
        e, c = self.create_event_with_matches(wwe, {
            'name': 'WrestleMania VIII',
            'date': date(1992, 4, 5),
            'venue': 'Hoosier Dome',
            'location': 'Indianapolis, Indiana',
            'attendance': 62167,
            'about': 'Featured Ric Flair vs Randy Savage and Hulk Hogan vs Sid Justice.'
        }, [
            {'wrestlers': ['Randy Savage', 'Ric Flair'], 'winner': 'Randy Savage', 'title': 'WWF Championship', 'match_type': 'WWF Championship', 'about': 'Savage won his second WWF Championship.'},
            {'wrestlers': ['Hulk Hogan', 'Sid Justice'], 'winner': 'Hulk Hogan', 'result': 'Disqualification', 'match_type': 'Singles Match'},
            {'wrestlers': ['Bret Hart', 'Roddy Piper'], 'winner': 'Bret Hart', 'title': 'WWF Intercontinental Championship', 'match_type': 'IC Title Match'},
            {'wrestlers': ['Undertaker', 'Jake Roberts'], 'winner': 'Undertaker', 'match_type': 'Singles Match'},
        ])
        if c:
            self.stdout.write(f'  + WrestleMania VIII')
            events_added += 1

        # WrestleMania IX (1993)
        e, c = self.create_event_with_matches(wwe, {
            'name': 'WrestleMania IX',
            'date': date(1993, 4, 4),
            'venue': 'Caesars Palace',
            'location': 'Las Vegas, Nevada',
            'attendance': 16891,
            'about': 'Roman-themed outdoor event. Hulk Hogan won the WWF Title in controversial fashion.'
        }, [
            {'wrestlers': ['Bret Hart', 'Yokozuna'], 'winner': 'Yokozuna', 'title': 'WWF Championship', 'match_type': 'WWF Championship'},
            {'wrestlers': ['Yokozuna', 'Hulk Hogan'], 'winner': 'Hulk Hogan', 'title': 'WWF Championship', 'match_type': 'WWF Championship', 'about': 'Hogan challenged Yokozuna immediately after his win and took the title.'},
            {'wrestlers': ['Shawn Michaels', 'Tatanka'], 'winner': 'Shawn Michaels', 'result': 'Countout', 'title': 'WWF Intercontinental Championship', 'match_type': 'IC Title Match'},
            {'wrestlers': ['Undertaker', 'Giant Gonzalez'], 'winner': 'Undertaker', 'result': 'Disqualification', 'match_type': 'Singles Match'},
        ])
        if c:
            self.stdout.write(f'  + WrestleMania IX')
            events_added += 1

        # WrestleMania XI (1995)
        e, c = self.create_event_with_matches(wwe, {
            'name': 'WrestleMania XI',
            'date': date(1995, 4, 2),
            'venue': 'Hartford Civic Center',
            'location': 'Hartford, Connecticut',
            'attendance': 16305,
            'about': 'Featured LT vs Bam Bam Bigelow in the main event.'
        }, [
            {'wrestlers': ['Diesel', 'Shawn Michaels'], 'winner': 'Diesel', 'title': 'WWF Championship', 'match_type': 'WWF Championship'},
            {'wrestlers': ['Bret Hart', 'Bob Backlund'], 'winner': 'Bret Hart', 'match_type': 'I Quit Match'},
            {'wrestlers': ['Lawrence Taylor', 'Bam Bam Bigelow'], 'winner': 'Lawrence Taylor', 'match_type': 'Singles Match', 'about': 'NFL star LT defeated Bigelow in the main event.'},
            {'wrestlers': ['Undertaker', 'King Kong Bundy'], 'winner': 'Undertaker', 'match_type': 'Singles Match'},
        ])
        if c:
            self.stdout.write(f'  + WrestleMania XI')
            events_added += 1

        # WrestleMania XII (1996)
        e, c = self.create_event_with_matches(wwe, {
            'name': 'WrestleMania XII',
            'date': date(1996, 3, 31),
            'venue': 'Arrowhead Pond',
            'location': 'Anaheim, California',
            'attendance': 18853,
            'about': 'Featured the 60-minute Iron Man Match between Shawn Michaels and Bret Hart.'
        }, [
            {'wrestlers': ['Shawn Michaels', 'Bret Hart'], 'winner': 'Shawn Michaels', 'title': 'WWF Championship', 'match_type': '60-Minute Iron Man Match', 'about': 'Michaels won his first WWF Championship in overtime. The boyhood dream has come true.'},
            {'wrestlers': ['Ultimate Warrior', 'Triple H'], 'winner': 'Ultimate Warrior', 'match_type': 'Singles Match'},
            {'wrestlers': ['Undertaker', 'Diesel'], 'winner': 'Undertaker', 'match_type': 'Singles Match'},
        ])
        if c:
            self.stdout.write(f'  + WrestleMania XII')
            events_added += 1

        # WrestleMania XIII (1997)
        e, c = self.create_event_with_matches(wwe, {
            'name': 'WrestleMania 13',
            'date': date(1997, 3, 23),
            'venue': 'Rosemont Horizon',
            'location': 'Rosemont, Illinois',
            'attendance': 18197,
            'about': 'Featured the double-turn in Austin vs Bret Hart submission match.'
        }, [
            {'wrestlers': ['Stone Cold Steve Austin', 'Bret Hart'], 'winner': 'Bret Hart', 'result': 'Submission', 'match_type': 'Submission Match', 'about': 'The double-turn. Austin passed out in the Sharpshooter but never quit. Austin became the top babyface, Hart became a heel.'},
            {'wrestlers': ['Undertaker', 'Sid'], 'winner': 'Undertaker', 'title': 'WWF Championship', 'match_type': 'WWF Championship', 'about': 'Undertaker won his second WWF Championship.'},
            {'wrestlers': ['Triple H', 'Goldust'], 'winner': 'Triple H', 'title': 'WWF Intercontinental Championship', 'match_type': 'IC Title Match'},
        ])
        if c:
            self.stdout.write(f'  + WrestleMania 13')
            events_added += 1

        # WrestleMania XIV (1998)
        e, c = self.create_event_with_matches(wwe, {
            'name': 'WrestleMania XIV',
            'date': date(1998, 3, 29),
            'venue': 'Fleet Center',
            'location': 'Boston, Massachusetts',
            'attendance': 19028,
            'about': 'Austin 3:16 era began. Stone Cold defeated Shawn Michaels for the WWF Title.'
        }, [
            {'wrestlers': ['Stone Cold Steve Austin', 'Shawn Michaels'], 'winner': 'Stone Cold Steve Austin', 'title': 'WWF Championship', 'match_type': 'WWF Championship', 'about': 'Austin won his first WWF Championship. Mike Tyson knocked out Michaels.'},
            {'wrestlers': ['Undertaker', 'Kane'], 'winner': 'Undertaker', 'match_type': 'Singles Match', 'about': 'First WrestleMania match between the Brothers of Destruction.'},
            {'wrestlers': ['Triple H', 'Owen Hart'], 'winner': 'Triple H', 'title': 'WWF European Championship', 'match_type': 'European Title Match'},
            {'wrestlers': ['The Rock', 'Ken Shamrock'], 'winner': 'Ken Shamrock', 'result': 'Disqualification', 'title': 'WWF Intercontinental Championship', 'match_type': 'IC Title Match'},
        ])
        if c:
            self.stdout.write(f'  + WrestleMania XIV')
            events_added += 1

        # WrestleMania XV (1999)
        e, c = self.create_event_with_matches(wwe, {
            'name': 'WrestleMania XV',
            'date': date(1999, 3, 28),
            'venue': 'First Union Center',
            'location': 'Philadelphia, Pennsylvania',
            'attendance': 20276,
            'about': 'Featured Stone Cold Steve Austin vs The Rock for the WWF Championship.'
        }, [
            {'wrestlers': ['Stone Cold Steve Austin', 'The Rock'], 'winner': 'Stone Cold Steve Austin', 'title': 'WWF Championship', 'match_type': 'No DQ Match', 'about': 'Austin defeated The Rock to win his third WWF Championship.'},
            {'wrestlers': ['Mankind', 'Paul Wight'], 'winner': 'Mankind', 'title': 'WWF Championship', 'match_type': 'Referee: Stone Cold', 'about': 'This match happened earlier on the card.'},
            {'wrestlers': ['Triple H', 'Kane'], 'winner': 'Kane', 'match_type': 'Singles Match'},
            {'wrestlers': ['Undertaker', 'Big Boss Man'], 'winner': 'Undertaker', 'match_type': 'Hell in a Cell'},
        ])
        if c:
            self.stdout.write(f'  + WrestleMania XV')
            events_added += 1

        # WrestleMania 2000 (XVI)
        e, c = self.create_event_with_matches(wwe, {
            'name': 'WrestleMania 2000',
            'date': date(2000, 4, 2),
            'venue': 'Arrowhead Pond',
            'location': 'Anaheim, California',
            'attendance': 19776,
            'about': 'First WrestleMania without a traditional main event babyface win.'
        }, [
            {'wrestlers': ['Triple H', 'The Rock', 'Big Show', 'Mick Foley'], 'winner': 'Triple H', 'title': 'WWF Championship', 'match_type': 'Fatal Four-Way Elimination', 'about': 'Triple H retained with help from Vince and Stephanie McMahon.'},
            {'wrestlers': ['Edge', 'Christian', 'Hardys', 'Dudleys'], 'winner': 'Edge and Christian', 'title': 'WWF Tag Team Championship', 'match_type': 'Triangle Ladder Match', 'about': 'First TLC-style match at WrestleMania.'},
            {'wrestlers': ['Chris Benoit', 'Kurt Angle', 'Chris Jericho'], 'winner': 'Chris Benoit', 'title': 'WWF Intercontinental Championship', 'match_type': 'Two-Fall Triple Threat'},
            {'wrestlers': ['Kat', 'Terri'], 'winner': 'Kat', 'match_type': 'Catfight'},
        ])
        if c:
            self.stdout.write(f'  + WrestleMania 2000')
            events_added += 1

        # WrestleMania X8 (2002)
        e, c = self.create_event_with_matches(wwe, {
            'name': 'WrestleMania X8',
            'date': date(2002, 3, 17),
            'venue': 'SkyDome',
            'location': 'Toronto, Ontario, Canada',
            'attendance': 68237,
            'about': 'Icon vs Icon - Hulk Hogan vs The Rock.'
        }, [
            {'wrestlers': ['Triple H', 'Chris Jericho'], 'winner': 'Triple H', 'title': 'WWF Undisputed Championship', 'match_type': 'Undisputed Championship', 'about': 'Triple H won his fifth world championship.'},
            {'wrestlers': ['Hulk Hogan', 'The Rock'], 'winner': 'The Rock', 'match_type': 'Icon vs Icon', 'about': 'One of the most electric matches in WrestleMania history.'},
            {'wrestlers': ['Stone Cold Steve Austin', 'Scott Hall'], 'winner': 'Stone Cold Steve Austin', 'match_type': 'Singles Match'},
            {'wrestlers': ['Undertaker', 'Ric Flair'], 'winner': 'Undertaker', 'match_type': 'No DQ Match', 'about': 'Undertaker went 10-0 at WrestleMania.'},
            {'wrestlers': ['Edge', 'Booker T'], 'winner': 'Edge', 'title': 'WWF Intercontinental Championship', 'match_type': 'IC Title Match'},
        ])
        if c:
            self.stdout.write(f'  + WrestleMania X8')
            events_added += 1

        # WrestleMania XX (2004)
        e, c = self.create_event_with_matches(wwe, {
            'name': 'WrestleMania XX',
            'date': date(2004, 3, 14),
            'venue': 'Madison Square Garden',
            'location': 'New York City, New York',
            'attendance': 20000,
            'about': 'Where It All Begins Again. Return to Madison Square Garden.'
        }, [
            {'wrestlers': ['Chris Benoit', 'Triple H', 'Shawn Michaels'], 'winner': 'Chris Benoit', 'title': 'World Heavyweight Championship', 'match_type': 'Triple Threat', 'about': 'Benoit won the World Heavyweight Championship. Eddie Guerrero celebrated with him.'},
            {'wrestlers': ['Eddie Guerrero', 'Kurt Angle'], 'winner': 'Eddie Guerrero', 'title': 'WWE Championship', 'match_type': 'WWE Championship'},
            {'wrestlers': ['Undertaker', 'Kane'], 'winner': 'Undertaker', 'match_type': 'Singles Match', 'about': 'The Deadman returned with his classic gimmick. 12-0.'},
            {'wrestlers': ['Brock Lesnar', 'Goldberg'], 'winner': 'Goldberg', 'match_type': 'Special Referee: Austin'},
            {'wrestlers': ['John Cena', 'Big Show'], 'winner': 'John Cena', 'title': 'United States Championship', 'match_type': 'US Title Match'},
        ])
        if c:
            self.stdout.write(f'  + WrestleMania XX')
            events_added += 1

        # WrestleMania 21 (2005)
        e, c = self.create_event_with_matches(wwe, {
            'name': 'WrestleMania 21',
            'date': date(2005, 4, 3),
            'venue': 'Staples Center',
            'location': 'Los Angeles, California',
            'attendance': 20193,
            'about': 'WrestleMania Goes Hollywood. Batista and John Cena won world titles.'
        }, [
            {'wrestlers': ['Batista', 'Triple H'], 'winner': 'Batista', 'title': 'World Heavyweight Championship', 'match_type': 'World Title Match', 'about': 'Batista won his first world championship.'},
            {'wrestlers': ['John Cena', 'JBL'], 'winner': 'John Cena', 'title': 'WWE Championship', 'match_type': 'WWE Championship', 'about': 'Cena won his first WWE Championship.'},
            {'wrestlers': ['Undertaker', 'Randy Orton'], 'winner': 'Undertaker', 'match_type': 'Legend vs Legend Killer', 'about': 'The Legend Killer could not end the streak. 13-0.'},
            {'wrestlers': ['Shawn Michaels', 'Kurt Angle'], 'winner': 'Kurt Angle', 'result': 'Submission', 'match_type': 'Singles Match'},
            {'wrestlers': ['Edge', 'Chris Benoit', 'Chris Jericho', 'Christian', 'Kane', 'Shelton Benjamin'], 'winner': 'Edge', 'match_type': 'Money in the Bank Ladder Match', 'about': 'First ever Money in the Bank Ladder Match.'},
        ])
        if c:
            self.stdout.write(f'  + WrestleMania 21')
            events_added += 1

        # WrestleMania 24 (2008)
        e, c = self.create_event_with_matches(wwe, {
            'name': 'WrestleMania XXIV',
            'date': date(2008, 3, 30),
            'venue': 'Citrus Bowl',
            'location': 'Orlando, Florida',
            'attendance': 74635,
            'about': 'Ric Flair retired. Edge vs Undertaker for the World Title.'
        }, [
            {'wrestlers': ['Undertaker', 'Edge'], 'winner': 'Undertaker', 'title': 'World Heavyweight Championship', 'match_type': 'World Title Match', 'about': 'Undertaker went 16-0.'},
            {'wrestlers': ['Randy Orton', 'Triple H', 'John Cena'], 'winner': 'Randy Orton', 'title': 'WWE Championship', 'match_type': 'Triple Threat'},
            {'wrestlers': ['Ric Flair', 'Shawn Michaels'], 'winner': 'Shawn Michaels', 'match_type': 'Career Threatening Match', 'about': 'I am sorry. I love you. Flair retired after this loss.'},
            {'wrestlers': ['Big Show', 'Floyd Mayweather'], 'winner': 'Floyd Mayweather', 'match_type': 'No DQ Match'},
        ])
        if c:
            self.stdout.write(f'  + WrestleMania XXIV')
            events_added += 1

        # WrestleMania 26 (2010)
        e, c = self.create_event_with_matches(wwe, {
            'name': 'WrestleMania XXVI',
            'date': date(2010, 3, 28),
            'venue': 'University of Phoenix Stadium',
            'location': 'Glendale, Arizona',
            'attendance': 72219,
            'about': 'Shawn Michaels retirement match. Undertaker vs HBK II.'
        }, [
            {'wrestlers': ['Undertaker', 'Shawn Michaels'], 'winner': 'Undertaker', 'match_type': 'Streak vs Career', 'about': 'HBK put his career on the line. Taker went 18-0. HBK retired.'},
            {'wrestlers': ['John Cena', 'Batista'], 'winner': 'John Cena', 'title': 'WWE Championship', 'match_type': 'WWE Championship'},
            {'wrestlers': ['Chris Jericho', 'Edge'], 'winner': 'Chris Jericho', 'title': 'World Heavyweight Championship', 'match_type': 'World Title Match'},
            {'wrestlers': ['Bret Hart', 'Vince McMahon'], 'winner': 'Bret Hart', 'match_type': 'No Holds Barred'},
            {'wrestlers': ['Triple H', 'Sheamus'], 'winner': 'Triple H', 'match_type': 'Singles Match'},
        ])
        if c:
            self.stdout.write(f'  + WrestleMania XXVI')
            events_added += 1

        # WrestleMania 28 (2012)
        e, c = self.create_event_with_matches(wwe, {
            'name': 'WrestleMania XXVIII',
            'date': date(2012, 4, 1),
            'venue': 'Sun Life Stadium',
            'location': 'Miami, Florida',
            'attendance': 78363,
            'about': 'Once in a Lifetime - The Rock vs John Cena.'
        }, [
            {'wrestlers': ['The Rock', 'John Cena'], 'winner': 'The Rock', 'match_type': 'Once in a Lifetime', 'about': 'The Rock defeated Cena in the main event.'},
            {'wrestlers': ['Undertaker', 'Triple H'], 'winner': 'Undertaker', 'match_type': 'Hell in a Cell - End of an Era', 'about': 'Shawn Michaels was special referee. Taker went 20-0.'},
            {'wrestlers': ['CM Punk', 'Chris Jericho'], 'winner': 'CM Punk', 'title': 'WWE Championship', 'match_type': 'WWE Championship'},
            {'wrestlers': ['Daniel Bryan', 'Sheamus'], 'winner': 'Sheamus', 'result': 'Pinfall (18 seconds)', 'title': 'World Heavyweight Championship', 'match_type': 'World Title Match'},
            {'wrestlers': ['Team Johnny', 'Team Teddy'], 'winner': 'Team Johnny', 'match_type': '12-Man Tag Team Match'},
        ])
        if c:
            self.stdout.write(f'  + WrestleMania XXVIII')
            events_added += 1

        # WrestleMania 29 (2013)
        e, c = self.create_event_with_matches(wwe, {
            'name': 'WrestleMania 29',
            'date': date(2013, 4, 7),
            'venue': 'MetLife Stadium',
            'location': 'East Rutherford, New Jersey',
            'attendance': 80676,
            'about': 'Twice in a Lifetime - The Rock vs John Cena II.'
        }, [
            {'wrestlers': ['John Cena', 'The Rock'], 'winner': 'John Cena', 'title': 'WWE Championship', 'match_type': 'WWE Championship', 'about': 'Cena beat Rock to become 11-time WWE Champion.'},
            {'wrestlers': ['Undertaker', 'CM Punk'], 'winner': 'Undertaker', 'match_type': 'Singles Match', 'about': 'Taker went 21-0.'},
            {'wrestlers': ['Triple H', 'Brock Lesnar'], 'winner': 'Triple H', 'match_type': 'No Holds Barred'},
            {'wrestlers': ['Alberto Del Rio', 'Jack Swagger'], 'winner': 'Alberto Del Rio', 'title': 'World Heavyweight Championship', 'match_type': 'World Title Match'},
        ])
        if c:
            self.stdout.write(f'  + WrestleMania 29')
            events_added += 1

        # WrestleMania 31 (2015)
        e, c = self.create_event_with_matches(wwe, {
            'name': 'WrestleMania 31',
            'date': date(2015, 3, 29),
            'venue': 'Levi\'s Stadium',
            'location': 'Santa Clara, California',
            'attendance': 76976,
            'about': 'Seth Rollins cashed in during the main event.'
        }, [
            {'wrestlers': ['Brock Lesnar', 'Roman Reigns', 'Seth Rollins'], 'winner': 'Seth Rollins', 'title': 'WWE World Heavyweight Championship', 'match_type': 'Triple Threat', 'about': 'Rollins cashed in his Money in the Bank briefcase mid-match.'},
            {'wrestlers': ['Undertaker', 'Bray Wyatt'], 'winner': 'Undertaker', 'match_type': 'Singles Match', 'about': 'Taker went 22-1.'},
            {'wrestlers': ['Triple H', 'Sting'], 'winner': 'Triple H', 'match_type': 'No DQ Match'},
            {'wrestlers': ['John Cena', 'Rusev'], 'winner': 'John Cena', 'title': 'United States Championship', 'match_type': 'US Title Match'},
            {'wrestlers': ['Daniel Bryan', 'Dolph Ziggler', 'Dean Ambrose', 'R-Truth', 'Stardust', 'Luke Harper', 'Bad News Barrett'], 'winner': 'Daniel Bryan', 'title': 'Intercontinental Championship', 'match_type': 'Ladder Match'},
        ])
        if c:
            self.stdout.write(f'  + WrestleMania 31')
            events_added += 1

        # SummerSlam 1998
        e, c = self.create_event_with_matches(wwe, {
            'name': 'SummerSlam 1998',
            'date': date(1998, 8, 30),
            'venue': 'Madison Square Garden',
            'location': 'New York City, New York',
            'attendance': 21588,
            'about': 'Highway to Hell. Austin vs Undertaker for the WWF Title.'
        }, [
            {'wrestlers': ['Stone Cold Steve Austin', 'Undertaker'], 'winner': 'Stone Cold Steve Austin', 'title': 'WWF Championship', 'match_type': 'WWF Championship'},
            {'wrestlers': ['The Rock', 'Triple H'], 'winner': 'The Rock', 'title': 'WWF Intercontinental Championship', 'match_type': 'Ladder Match'},
            {'wrestlers': ['Mankind', 'New Age Outlaws'], 'winner': 'Mankind and Kane', 'title': 'WWF Tag Team Championship', 'match_type': 'Tag Title Match'},
            {'wrestlers': ['X-Pac', 'Jeff Jarrett'], 'winner': 'X-Pac', 'match_type': 'Hair vs Hair Match'},
        ])
        if c:
            self.stdout.write(f'  + SummerSlam 1998')
            events_added += 1

        # SummerSlam 2002
        e, c = self.create_event_with_matches(wwe, {
            'name': 'SummerSlam 2002',
            'date': date(2002, 8, 25),
            'venue': 'Nassau Coliseum',
            'location': 'Uniondale, New York',
            'attendance': 14797,
            'about': 'Brock Lesnar vs The Rock for the Undisputed Championship.'
        }, [
            {'wrestlers': ['Brock Lesnar', 'The Rock'], 'winner': 'Brock Lesnar', 'title': 'WWE Undisputed Championship', 'match_type': 'WWE Championship', 'about': 'Lesnar became the youngest WWE Champion at 25.'},
            {'wrestlers': ['Shawn Michaels', 'Triple H'], 'winner': 'Shawn Michaels', 'match_type': 'Unsanctioned Street Fight', 'about': 'HBK returned from a 4-year retirement and won.'},
            {'wrestlers': ['Kurt Angle', 'Rey Mysterio'], 'winner': 'Kurt Angle', 'match_type': 'Singles Match'},
            {'wrestlers': ['Undertaker', 'Test'], 'winner': 'Undertaker', 'match_type': 'Singles Match'},
        ])
        if c:
            self.stdout.write(f'  + SummerSlam 2002')
            events_added += 1

        # Royal Rumble 2000
        e, c = self.create_event_with_matches(wwe, {
            'name': 'Royal Rumble 2000',
            'date': date(2000, 1, 23),
            'venue': 'Madison Square Garden',
            'location': 'New York City, New York',
            'attendance': 19231,
            'about': 'The Rock won the Royal Rumble match.'
        }, [
            {'wrestlers': ['Royal Rumble participants'], 'winner': 'The Rock', 'match_type': 'Royal Rumble Match', 'about': 'The Rock won by last eliminating Big Show.'},
            {'wrestlers': ['Triple H', 'Cactus Jack'], 'winner': 'Triple H', 'title': 'WWF Championship', 'match_type': 'Street Fight'},
            {'wrestlers': ['New Age Outlaws', 'Acolytes'], 'winner': 'New Age Outlaws', 'title': 'WWF Tag Team Championship', 'match_type': 'Tag Title Match'},
            {'wrestlers': ['Chris Jericho', 'Chyna', 'Hardcore Holly'], 'winner': 'Chris Jericho', 'title': 'WWF Intercontinental Championship', 'match_type': 'Triple Threat'},
        ])
        if c:
            self.stdout.write(f'  + Royal Rumble 2000')
            events_added += 1

        # Royal Rumble 2001
        e, c = self.create_event_with_matches(wwe, {
            'name': 'Royal Rumble 2001',
            'date': date(2001, 1, 21),
            'venue': 'New Orleans Arena',
            'location': 'New Orleans, Louisiana',
            'attendance': 17218,
            'about': 'Stone Cold Steve Austin won the Royal Rumble.'
        }, [
            {'wrestlers': ['Royal Rumble participants'], 'winner': 'Stone Cold Steve Austin', 'match_type': 'Royal Rumble Match', 'about': 'Austin won by last eliminating Kane.'},
            {'wrestlers': ['Kurt Angle', 'Triple H'], 'winner': 'Kurt Angle', 'title': 'WWF Championship', 'match_type': 'WWF Championship'},
            {'wrestlers': ['Chris Benoit', 'Chris Jericho'], 'winner': 'Chris Benoit', 'title': 'WWF Intercontinental Championship', 'match_type': 'Ladder Match'},
        ])
        if c:
            self.stdout.write(f'  + Royal Rumble 2001')
            events_added += 1

        self.stdout.write(f'\nAdded {events_added} more WWE events')

    def seed_more_wcw(self, wcw):
        self.stdout.write('\n--- More WCW Events ---\n')
        events_added = 0

        # Starrcade 1985
        e, c = self.create_event_with_matches(wcw, {
            'name': 'Starrcade 1985',
            'date': date(1985, 11, 28),
            'venue': 'Greensboro Coliseum',
            'location': 'Greensboro, North Carolina',
            'attendance': 16000,
            'about': 'The Gathering. Featured Ric Flair vs Dusty Rhodes.'
        }, [
            {'wrestlers': ['Ric Flair', 'Dusty Rhodes'], 'winner': 'Ric Flair', 'title': 'NWA World Heavyweight Championship', 'match_type': 'NWA Championship'},
            {'wrestlers': ['Magnum TA', 'Tully Blanchard'], 'winner': 'Magnum TA', 'title': 'NWA United States Championship', 'match_type': 'I Quit Steel Cage Match', 'about': 'One of the most brutal matches in wrestling history.'},
            {'wrestlers': ['Road Warriors', 'Ivan Koloff', 'Krusher Khruschev'], 'winner': 'Road Warriors', 'match_type': 'Tag Team Match'},
        ])
        if c:
            self.stdout.write(f'  + Starrcade 1985')
            events_added += 1

        # Starrcade 1988
        e, c = self.create_event_with_matches(wcw, {
            'name': 'Starrcade 1988',
            'date': date(1988, 12, 26),
            'venue': 'Norfolk Scope',
            'location': 'Norfolk, Virginia',
            'attendance': 10000,
            'about': 'True Gritt. Ric Flair returned to win the NWA Title.'
        }, [
            {'wrestlers': ['Ric Flair', 'Lex Luger'], 'winner': 'Ric Flair', 'title': 'NWA World Heavyweight Championship', 'match_type': 'NWA Championship'},
            {'wrestlers': ['Road Warriors', 'Varsity Club'], 'winner': 'Road Warriors', 'match_type': 'Tag Team Match'},
        ])
        if c:
            self.stdout.write(f'  + Starrcade 1988')
            events_added += 1

        # Great American Bash 1989
        e, c = self.create_event_with_matches(wcw, {
            'name': 'Great American Bash 1989',
            'date': date(1989, 7, 23),
            'venue': 'Baltimore Arena',
            'location': 'Baltimore, Maryland',
            'attendance': 13200,
            'about': 'Glory Days. Featured Ric Flair vs Terry Funk.'
        }, [
            {'wrestlers': ['Ric Flair', 'Terry Funk'], 'winner': 'Ric Flair', 'title': 'NWA World Heavyweight Championship', 'match_type': 'NWA Championship'},
            {'wrestlers': ['Lex Luger', 'Ricky Steamboat'], 'winner': 'Lex Luger', 'title': 'NWA United States Championship', 'match_type': 'US Title Match'},
        ])
        if c:
            self.stdout.write(f'  + Great American Bash 1989')
            events_added += 1

        # SuperBrawl 1991
        e, c = self.create_event_with_matches(wcw, {
            'name': 'SuperBrawl 1991',
            'date': date(1991, 5, 19),
            'venue': 'Bayfront Center',
            'location': 'St. Petersburg, Florida',
            'attendance': 6000,
            'about': 'First SuperBrawl event. Flair vs Fujinami.'
        }, [
            {'wrestlers': ['Ric Flair', 'Tatsumi Fujinami'], 'winner': 'Ric Flair', 'title': 'NWA World Heavyweight Championship', 'match_type': 'NWA Championship'},
            {'wrestlers': ['Sting', 'Nikita Koloff'], 'winner': 'Sting', 'match_type': 'Singles Match'},
        ])
        if c:
            self.stdout.write(f'  + SuperBrawl 1991')
            events_added += 1

        # Starrcade 1996
        e, c = self.create_event_with_matches(wcw, {
            'name': 'Starrcade 1996',
            'date': date(1996, 12, 29),
            'venue': 'Nashville Municipal Auditorium',
            'location': 'Nashville, Tennessee',
            'attendance': 10000,
            'about': 'nWo runs wild. Hogan vs Piper for the WCW Championship.'
        }, [
            {'wrestlers': ['Hollywood Hogan', 'Roddy Piper'], 'winner': 'Roddy Piper', 'result': 'Submission', 'match_type': 'WCW Championship non-title', 'about': 'Piper made Hogan submit but the title was not on the line.'},
            {'wrestlers': ['Lex Luger', 'Giant'], 'winner': 'Lex Luger', 'result': 'Disqualification', 'match_type': 'Singles Match'},
            {'wrestlers': ['Eddie Guerrero', 'Diamond Dallas Page'], 'winner': 'Eddie Guerrero', 'title': 'WCW United States Championship', 'match_type': 'US Title Match'},
        ])
        if c:
            self.stdout.write(f'  + Starrcade 1996')
            events_added += 1

        # Spring Stampede 1999
        e, c = self.create_event_with_matches(wcw, {
            'name': 'Spring Stampede 1999',
            'date': date(1999, 4, 11),
            'venue': 'Tacoma Dome',
            'location': 'Tacoma, Washington',
            'attendance': 17214,
            'about': 'Diamond Dallas Page won the WCW Championship.'
        }, [
            {'wrestlers': ['Diamond Dallas Page', 'Ric Flair', 'Hulk Hogan', 'Sting'], 'winner': 'Diamond Dallas Page', 'title': 'WCW World Heavyweight Championship', 'match_type': 'Fatal Four-Way', 'about': 'DDP won his third WCW World Championship.'},
            {'wrestlers': ['Goldberg', 'Kevin Nash'], 'winner': 'Goldberg', 'match_type': 'Singles Match'},
            {'wrestlers': ['Chris Benoit', 'Dean Malenko'], 'winner': 'Chris Benoit', 'match_type': 'Singles Match'},
        ])
        if c:
            self.stdout.write(f'  + Spring Stampede 1999')
            events_added += 1

        self.stdout.write(f'\nAdded {events_added} more WCW events')

    def seed_more_aew(self, aew):
        self.stdout.write('\n--- More AEW Events ---\n')
        events_added = 0

        # All Out 2019
        e, c = self.create_event_with_matches(aew, {
            'name': 'All Out 2019',
            'date': date(2019, 8, 31),
            'venue': 'Sears Centre',
            'location': 'Hoffman Estates, Illinois',
            'attendance': 10036,
            'about': 'Chris Jericho won the first AEW World Championship.'
        }, [
            {'wrestlers': ['Chris Jericho', 'Hangman Adam Page'], 'winner': 'Chris Jericho', 'title': 'AEW World Championship', 'match_type': 'AEW World Championship', 'about': 'Jericho became the first AEW World Champion.'},
            {'wrestlers': ['Cody', 'Shawn Spears'], 'winner': 'Cody', 'match_type': 'Singles Match'},
            {'wrestlers': ['Lucha Brothers', 'Young Bucks'], 'winner': 'Lucha Brothers', 'title': 'AAA World Tag Team Championship', 'match_type': 'Ladder Match'},
            {'wrestlers': ['PAC', 'Kenny Omega'], 'winner': 'PAC', 'match_type': 'Singles Match'},
        ])
        if c:
            self.stdout.write(f'  + All Out 2019')
            events_added += 1

        # Full Gear 2019
        e, c = self.create_event_with_matches(aew, {
            'name': 'Full Gear 2019',
            'date': date(2019, 11, 9),
            'venue': 'Royal Farms Arena',
            'location': 'Baltimore, Maryland',
            'attendance': 9070,
            'about': 'First Full Gear event. Cody vs Jericho for the AEW Title.'
        }, [
            {'wrestlers': ['Chris Jericho', 'Cody'], 'winner': 'Chris Jericho', 'title': 'AEW World Championship', 'match_type': 'AEW Championship'},
            {'wrestlers': ['Jon Moxley', 'Kenny Omega'], 'winner': 'Jon Moxley', 'match_type': 'Lights Out Unsanctioned Match'},
            {'wrestlers': ['Hangman Adam Page', 'PAC'], 'winner': 'Draw', 'match_type': 'Singles Match'},
            {'wrestlers': ['SCU', 'Lucha Brothers', 'Private Party'], 'winner': 'SCU', 'title': 'AEW World Tag Team Championship', 'match_type': 'Triple Threat'},
        ])
        if c:
            self.stdout.write(f'  + Full Gear 2019')
            events_added += 1

        # Revolution 2020
        e, c = self.create_event_with_matches(aew, {
            'name': 'Revolution 2020',
            'date': date(2020, 2, 29),
            'venue': 'Wintrust Arena',
            'location': 'Chicago, Illinois',
            'attendance': 8494,
            'about': 'First Revolution event. Moxley vs Jericho.'
        }, [
            {'wrestlers': ['Jon Moxley', 'Chris Jericho'], 'winner': 'Jon Moxley', 'title': 'AEW World Championship', 'match_type': 'AEW Championship', 'about': 'Moxley won his first AEW World Championship.'},
            {'wrestlers': ['Kenny Omega', 'Hangman Adam Page', 'Young Bucks'], 'winner': 'Kenny Omega and Hangman Page', 'title': 'AEW World Tag Team Championship', 'match_type': 'Tag Team Championship'},
            {'wrestlers': ['Cody', 'MJF'], 'winner': 'Cody', 'match_type': 'Singles Match'},
            {'wrestlers': ['PAC', 'Orange Cassidy'], 'winner': 'PAC', 'match_type': 'Singles Match'},
        ])
        if c:
            self.stdout.write(f'  + Revolution 2020')
            events_added += 1

        # Full Gear 2021
        e, c = self.create_event_with_matches(aew, {
            'name': 'Full Gear 2021',
            'date': date(2021, 11, 13),
            'venue': 'Target Center',
            'location': 'Minneapolis, Minnesota',
            'attendance': 10082,
            'about': 'Hangman Adam Page won the AEW World Championship.'
        }, [
            {'wrestlers': ['Hangman Adam Page', 'Kenny Omega'], 'winner': 'Hangman Adam Page', 'title': 'AEW World Championship', 'match_type': 'AEW Championship', 'about': 'Hangman finally captured the AEW World Championship.'},
            {'wrestlers': ['CM Punk', 'Eddie Kingston'], 'winner': 'CM Punk', 'match_type': 'Singles Match'},
            {'wrestlers': ['MJF', 'Darby Allin'], 'winner': 'MJF', 'match_type': 'Singles Match'},
            {'wrestlers': ['Britt Baker', 'Tay Conti'], 'winner': 'Britt Baker', 'title': 'AEW Women\'s World Championship', 'match_type': 'Women\'s Championship'},
            {'wrestlers': ['Lucha Brothers', 'FTR'], 'winner': 'Lucha Brothers', 'title': 'AEW World Tag Team Championship', 'match_type': 'Tag Team Championship'},
        ])
        if c:
            self.stdout.write(f'  + Full Gear 2021')
            events_added += 1

        self.stdout.write(f'\nAdded {events_added} more AEW events')
