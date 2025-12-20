"""
Seed historic ECW TV episodes with matches and significant moments.

Usage:
    python manage.py seed_ecw_tv
"""
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from datetime import date
from owdb_django.owdbapp.models import (
    Event, Match, Wrestler, Promotion, Title, Venue
)


class Command(BaseCommand):
    help = 'Seed historic ECW Hardcore TV episodes'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n=== Seeding ECW TV Episodes ===\n'))

        ecw = Promotion.objects.filter(abbreviation='ECW').first()
        if not ecw:
            ecw = Promotion.objects.create(
                name='Extreme Championship Wrestling',
                abbreviation='ECW',
                founded_year=1992
            )
            self.stdout.write('  + Created ECW promotion')

        self.seed_ecw_1994(ecw)
        self.seed_ecw_1995(ecw)
        self.seed_ecw_1996(ecw)
        self.seed_ecw_1997(ecw)
        self.seed_ecw_1998(ecw)
        self.seed_ecw_1999(ecw)
        self.seed_ecw_2000(ecw)

        self.stdout.write(self.style.SUCCESS('\n=== ECW TV Seeding Complete ==='))
        self.stdout.write(f'Total Events: {Event.objects.count()}')
        self.stdout.write(f'Total Matches: {Match.objects.count()}')

    def get_or_create_wrestler(self, name):
        """Get or create a wrestler by name."""
        wrestler = Wrestler.objects.filter(name__iexact=name).first()
        if not wrestler:
            slug = slugify(name)
            wrestler = Wrestler.objects.filter(slug=slug).first()
        if not wrestler:
            wrestler = Wrestler.objects.create(name=name)
            self.stdout.write(f'  + Created wrestler: {name}')
        return wrestler

    def get_or_create_venue(self, name, location=None):
        """Get or create a venue."""
        venue = Venue.objects.filter(name__iexact=name).first()
        if not venue:
            venue = Venue.objects.create(name=name, location=location)
        return venue

    def get_or_create_title(self, name, promotion):
        """Get or create a title."""
        title = Title.objects.filter(name__iexact=name).first()
        if not title:
            title = Title.objects.create(name=name, promotion=promotion)
            self.stdout.write(f'  + Created title: {name}')
        return title

    def create_episode_with_matches(self, promotion, episode_data, matches_data):
        """Create a TV episode with its matches."""
        episode_date = episode_data['date']
        slug = slugify(f"{episode_data['name']}-{episode_date}")

        event = Event.objects.filter(slug=slug).first()
        if event:
            return event, False

        venue = None
        if 'venue' in episode_data:
            venue = self.get_or_create_venue(
                episode_data['venue'],
                episode_data.get('location')
            )

        event = Event.objects.create(
            name=episode_data['name'],
            slug=slug,
            date=episode_date,
            promotion=promotion,
            venue=venue,
            event_type='TV',
            about=episode_data.get('about', '')
        )

        for i, match_data in enumerate(matches_data, 1):
            self.create_match(event, match_data, i, promotion)

        self.stdout.write(self.style.SUCCESS(
            f'  Created: {episode_data["name"]} ({episode_date}) - {len(matches_data)} matches'
        ))
        return event, True

    def create_match(self, event, match_data, order, promotion):
        """Create a match for an event."""
        wrestlers = []
        for wrestler_name in match_data.get('wrestlers', []):
            wrestler = self.get_or_create_wrestler(wrestler_name)
            wrestlers.append(wrestler)

        winner = None
        if match_data.get('winner'):
            winner = self.get_or_create_wrestler(match_data['winner'])

        title = None
        if match_data.get('title'):
            title = self.get_or_create_title(match_data['title'], promotion)

        match = Match.objects.create(
            event=event,
            match_type=match_data.get('match_type', 'Singles'),
            winner=winner,
            title=title,
            order=order,
            title_changed=match_data.get('title_changed', False),
            about=match_data.get('about', '')
        )
        match.wrestlers.set(wrestlers)
        return match

    def seed_ecw_1994(self, ecw):
        """Seed ECW Hardcore TV episodes from 1994."""
        self.stdout.write('\n--- 1994: The Revolution Begins ---\n')

        # Shane Douglas Throws Down the NWA Title
        self.create_episode_with_matches(ecw, {
            'name': 'ECW Hardcore TV',
            'date': date(1994, 8, 27),
            'venue': 'ECW Arena',
            'location': 'Philadelphia, PA',
            'about': 'Shane Douglas threw down the NWA World Heavyweight Championship and declared himself ECW World Heavyweight Champion. The birth of Extreme Championship Wrestling.'
        }, [
            {'wrestlers': ['Shane Douglas', 'Too Cold Scorpio', 'Sabu'], 'winner': 'Shane Douglas',
             'match_type': 'Triple Threat', 'title': 'NWA World Heavyweight Championship', 'title_changed': True,
             'about': 'Shane Douglas threw down the NWA title and declared himself ECW World Champion. "This is the dawning of a new era!"'},
            {'wrestlers': ['The Public Enemy', 'The Bruise Brothers'], 'winner': 'The Public Enemy',
             'match_type': 'Tag Team', 'about': 'Public Enemy brought their hardcore style.'},
        ])

        # Cactus Jack Anti-Hardcore Promo
        self.create_episode_with_matches(ecw, {
            'name': 'ECW Hardcore TV',
            'date': date(1994, 10, 1),
            'venue': 'ECW Arena',
            'location': 'Philadelphia, PA',
            'about': 'Cactus Jack cut his famous anti-hardcore promo, turning heel on the ECW faithful.'
        }, [
            {'wrestlers': ['Cactus Jack', 'The Sandman'], 'winner': 'Cactus Jack',
             'match_type': 'Hardcore', 'about': 'Cactus Jack called ECW fans mutants in his legendary promo.'},
            {'wrestlers': ['Sabu', 'Chad Austin'], 'winner': 'Sabu',
             'match_type': 'Singles', 'about': 'Sabu destroyed his opponent.'},
        ])

    def seed_ecw_1995(self, ecw):
        """Seed ECW Hardcore TV episodes from 1995."""
        self.stdout.write('\n--- 1995: ECW Grows ---\n')

        # Dreamer vs Raven Begins
        self.create_episode_with_matches(ecw, {
            'name': 'ECW Hardcore TV',
            'date': date(1995, 1, 7),
            'venue': 'ECW Arena',
            'location': 'Philadelphia, PA',
            'about': 'The legendary Dreamer vs Raven feud begins.'
        }, [
            {'wrestlers': ['Raven', 'Tommy Dreamer'], 'winner': 'Raven',
             'match_type': 'Singles', 'about': 'Raven debuted and immediately targeted Tommy Dreamer.'},
            {'wrestlers': ['Sabu', 'Taz'], 'winner': 'No Contest',
             'match_type': 'Hardcore', 'about': 'Two ECW icons collided.'},
        ])

        # Sandman Becomes Icon
        self.create_episode_with_matches(ecw, {
            'name': 'ECW Hardcore TV',
            'date': date(1995, 4, 8),
            'venue': 'ECW Arena',
            'location': 'Philadelphia, PA',
            'about': 'The Sandman continued to develop his iconic beer-drinking, Singapore cane persona.'
        }, [
            {'wrestlers': ['The Sandman', 'Cactus Jack'], 'winner': 'The Sandman',
             'match_type': 'Singapore Cane', 'title': 'ECW World Heavyweight Championship',
             'about': 'Sandman defended with his signature weapon.'},
            {'wrestlers': ['Public Enemy', 'Rocco Rock', 'Johnny Grunge'], 'winner': 'Public Enemy',
             'match_type': 'Segment', 'about': 'Public Enemy antics.'},
        ])

        # Sabu vs Taz Feud
        self.create_episode_with_matches(ecw, {
            'name': 'ECW Hardcore TV',
            'date': date(1995, 6, 17),
            'venue': 'ECW Arena',
            'location': 'Philadelphia, PA',
            'about': 'The Sabu vs Taz feud intensified.'
        }, [
            {'wrestlers': ['Sabu', 'Too Cold Scorpio'], 'winner': 'Sabu',
             'match_type': 'Singles', 'about': 'High-flying action.'},
            {'wrestlers': ['Taz', 'Hack Myers'], 'winner': 'Taz',
             'match_type': 'Singles', 'about': 'Taz showed his suplex mastery.'},
        ])

        # Steve Austin Cuts "Toughest SOB" Promo
        self.create_episode_with_matches(ecw, {
            'name': 'ECW Hardcore TV',
            'date': date(1995, 12, 9),
            'venue': 'ECW Arena',
            'location': 'Philadelphia, PA',
            'about': 'Steve Austin cut promos in ECW after leaving WCW, developing his Stone Cold persona.'
        }, [
            {'wrestlers': ['Steve Austin', 'Mikey Whipwreck'], 'winner': 'Steve Austin',
             'match_type': 'Singles', 'about': 'Austin showcased his developing character. "I am the toughest SOB."'},
            {'wrestlers': ['The Gangstas', 'Public Enemy'], 'winner': 'No Contest',
             'match_type': 'Tag Team', 'about': 'Extreme tag team warfare.'},
        ])

    def seed_ecw_1996(self, ecw):
        """Seed ECW Hardcore TV episodes from 1996."""
        self.stdout.write('\n--- 1996: National Exposure ---\n')

        # RVD and Sabu
        self.create_episode_with_matches(ecw, {
            'name': 'ECW Hardcore TV',
            'date': date(1996, 5, 4),
            'venue': 'ECW Arena',
            'location': 'Philadelphia, PA',
            'about': 'Rob Van Dam continued his rise in ECW.'
        }, [
            {'wrestlers': ['Rob Van Dam', 'Axl Rotten'], 'winner': 'Rob Van Dam',
             'match_type': 'Singles', 'about': 'Mr. Monday Night showed off his unique style.'},
            {'wrestlers': ['Sabu', 'Taz'], 'winner': 'No Contest',
             'match_type': 'Hardcore', 'about': 'Their intense rivalry continued.'},
        ])

        # ECW Invades Raw - Summer 1996
        self.create_episode_with_matches(ecw, {
            'name': 'ECW Hardcore TV',
            'date': date(1996, 6, 29),
            'venue': 'ECW Arena',
            'location': 'Philadelphia, PA',
            'about': 'ECW addressed their invasion of WWF Monday Night Raw.'
        }, [
            {'wrestlers': ['Tommy Dreamer', 'Brian Lee'], 'winner': 'Tommy Dreamer',
             'match_type': 'Hardcore', 'about': 'Dreamer in hardcore action.'},
            {'wrestlers': ['The Sandman', 'Stevie Richards'], 'winner': 'The Sandman',
             'match_type': 'Singapore Cane', 'about': 'Sandman with his signature weapon.'},
        ])

        # Taz Becomes Human Suplex Machine
        self.create_episode_with_matches(ecw, {
            'name': 'ECW Hardcore TV',
            'date': date(1996, 9, 7),
            'venue': 'ECW Arena',
            'location': 'Philadelphia, PA',
            'about': 'Taz established himself as the Human Suplex Machine.'
        }, [
            {'wrestlers': ['Taz', 'Mikey Whipwreck'], 'winner': 'Taz',
             'match_type': 'Singles', 'about': 'Taz threw Mikey around with devastating suplexes.'},
            {'wrestlers': ['Rob Van Dam', 'Sabu'], 'winner': 'Draw',
             'match_type': 'Singles', 'about': 'RVD and Sabu formed their legendary partnership.'},
        ])

    def seed_ecw_1997(self, ecw):
        """Seed ECW Hardcore TV episodes from 1997."""
        self.stdout.write('\n--- 1997: Peak ECW ---\n')

        # Terry Funk ECW Champion
        self.create_episode_with_matches(ecw, {
            'name': 'ECW Hardcore TV',
            'date': date(1997, 4, 19),
            'venue': 'ECW Arena',
            'location': 'Philadelphia, PA',
            'about': 'Terry Funk as ECW World Champion.'
        }, [
            {'wrestlers': ['Terry Funk', 'Brian Lee'], 'winner': 'Terry Funk',
             'match_type': 'Hardcore', 'title': 'ECW World Heavyweight Championship',
             'about': 'The Funker defended the ECW World Title.'},
            {'wrestlers': ['Rob Van Dam', 'Jerry Lynn'], 'winner': 'Rob Van Dam',
             'match_type': 'Singles', 'about': 'A classic ECW matchup.'},
        ])

        # Taz Wins ECW TV Title
        self.create_episode_with_matches(ecw, {
            'name': 'ECW Hardcore TV',
            'date': date(1997, 6, 14),
            'venue': 'ECW Arena',
            'location': 'Philadelphia, PA',
            'about': 'Taz captured the ECW Television Championship.'
        }, [
            {'wrestlers': ['Taz', 'Pit Bull #2'], 'winner': 'Taz',
             'match_type': 'Singles', 'title': 'ECW Television Championship', 'title_changed': True,
             'about': 'Taz won the TV Title with the Tazmission.'},
            {'wrestlers': ['Tommy Dreamer', 'Raven'], 'winner': 'Tommy Dreamer',
             'match_type': 'Hardcore', 'about': 'Their eternal feud continued.'},
        ])

        # Barely Legal Fallout
        self.create_episode_with_matches(ecw, {
            'name': 'ECW Hardcore TV',
            'date': date(1997, 4, 26),
            'venue': 'ECW Arena',
            'location': 'Philadelphia, PA',
            'about': 'Fallout from ECW\'s first PPV, Barely Legal.'
        }, [
            {'wrestlers': ['Terry Funk', 'The Sandman'], 'winner': 'Terry Funk',
             'match_type': 'Singles', 'about': 'The new ECW World Champion in action.'},
            {'wrestlers': ['Rob Van Dam', 'Chris Candido'], 'winner': 'Rob Van Dam',
             'match_type': 'Singles', 'about': 'RVD showcased his aerial abilities.'},
        ])

    def seed_ecw_1998(self, ecw):
        """Seed ECW Hardcore TV episodes from 1998."""
        self.stdout.write('\n--- 1998: National TV Era ---\n')

        # TNN Era Begins
        self.create_episode_with_matches(ecw, {
            'name': 'ECW on TNN',
            'date': date(1999, 8, 27),
            'venue': 'Toledo Sports Arena',
            'location': 'Toledo, OH',
            'about': 'ECW debuts on TNN (The Nashville Network), gaining national television.'
        }, [
            {'wrestlers': ['Rob Van Dam', 'Jerry Lynn'], 'winner': 'Rob Van Dam',
             'match_type': 'Singles', 'title': 'ECW Television Championship',
             'about': 'RVD defended the TV Title in the TNN debut.'},
            {'wrestlers': ['Taz', 'Yoshihiro Tajiri'], 'winner': 'Taz',
             'match_type': 'Singles', 'about': 'Taz in action on national TV.'},
        ])

        # RVD vs Sabu Classic
        self.create_episode_with_matches(ecw, {
            'name': 'ECW Hardcore TV',
            'date': date(1998, 2, 7),
            'venue': 'ECW Arena',
            'location': 'Philadelphia, PA',
            'about': 'Rob Van Dam and Sabu showcased their incredible tag team chemistry.'
        }, [
            {'wrestlers': ['Rob Van Dam', 'Sabu', 'Eliminators'], 'winner': 'RVD and Sabu',
             'match_type': 'Tag Team', 'about': 'RVD and Sabu as the ultimate tag team.'},
            {'wrestlers': ['The Sandman', 'Justin Credible'], 'winner': 'The Sandman',
             'match_type': 'Singapore Cane', 'about': 'Sandman with his signature weapon.'},
        ])

        # Taz Dominates
        self.create_episode_with_matches(ecw, {
            'name': 'ECW Hardcore TV',
            'date': date(1998, 7, 11),
            'venue': 'ECW Arena',
            'location': 'Philadelphia, PA',
            'about': 'Taz continued his undefeated streak and dominance.'
        }, [
            {'wrestlers': ['Taz', 'Bam Bam Bigelow'], 'winner': 'Taz',
             'match_type': 'Singles', 'about': 'Taz faced the Beast from the East.'},
            {'wrestlers': ['Tommy Dreamer', 'Sabu'], 'winner': 'Tommy Dreamer',
             'match_type': 'Hardcore', 'about': 'ECW originals collided.'},
        ])

    def seed_ecw_1999(self, ecw):
        """Seed ECW Hardcore TV episodes from 1999."""
        self.stdout.write('\n--- 1999: TNN Era ---\n')

        # Taz Wins World Title
        self.create_episode_with_matches(ecw, {
            'name': 'ECW Hardcore TV',
            'date': date(1999, 1, 16),
            'venue': 'ECW Arena',
            'location': 'Philadelphia, PA',
            'about': 'Post Guilty as Charged. Taz is ECW World Heavyweight Champion.'
        }, [
            {'wrestlers': ['Taz', 'Chris Candido'], 'winner': 'Taz',
             'match_type': 'Singles', 'title': 'ECW World Heavyweight Championship',
             'about': 'New champion Taz defended his title.'},
            {'wrestlers': ['Rob Van Dam', 'Jerry Lynn'], 'winner': 'Rob Van Dam',
             'match_type': 'Singles', 'title': 'ECW Television Championship',
             'about': 'Classic RVD vs Lynn matchup.'},
        ])

        # Mike Awesome Era
        self.create_episode_with_matches(ecw, {
            'name': 'ECW on TNN',
            'date': date(1999, 10, 1),
            'venue': 'Odeum',
            'location': 'Villa Park, IL',
            'about': 'Mike Awesome established himself as ECW World Champion.'
        }, [
            {'wrestlers': ['Mike Awesome', 'Masato Tanaka'], 'winner': 'Mike Awesome',
             'match_type': 'Singles', 'title': 'ECW World Heavyweight Championship',
             'about': 'Brutal main event between two hardcore warriors.'},
            {'wrestlers': ['Rob Van Dam', 'Super Crazy'], 'winner': 'Rob Van Dam',
             'match_type': 'Singles', 'about': 'High-flying action.'},
        ])

    def seed_ecw_2000(self, ecw):
        """Seed ECW Hardcore TV episodes from 2000."""
        self.stdout.write('\n--- 2000: The Final Year ---\n')

        # Justin Credible Era
        self.create_episode_with_matches(ecw, {
            'name': 'ECW on TNN',
            'date': date(2000, 5, 12),
            'venue': 'ECW Arena',
            'location': 'Philadelphia, PA',
            'about': 'Justin Credible as ECW World Heavyweight Champion.'
        }, [
            {'wrestlers': ['Justin Credible', 'Tommy Dreamer'], 'winner': 'Justin Credible',
             'match_type': 'Singles', 'title': 'ECW World Heavyweight Championship',
             'about': 'Justin Credible defended against the heart of ECW.'},
            {'wrestlers': ['Rob Van Dam', 'Scotty Anton'], 'winner': 'Rob Van Dam',
             'match_type': 'Singles', 'title': 'ECW Television Championship',
             'about': 'RVD\'s historic TV title reign continued.'},
        ])

        # Final TNN Episode
        self.create_episode_with_matches(ecw, {
            'name': 'ECW on TNN',
            'date': date(2000, 10, 6),
            'venue': 'Nashville Municipal Auditorium',
            'location': 'Nashville, TN',
            'about': 'The final ECW episode on TNN before their cancellation.'
        }, [
            {'wrestlers': ['Jerry Lynn', 'Steve Corino'], 'winner': 'Jerry Lynn',
             'match_type': 'Singles', 'title': 'ECW World Heavyweight Championship',
             'about': 'Jerry Lynn as ECW World Champion.'},
            {'wrestlers': ['Rob Van Dam', 'Rhino'], 'winner': 'Rob Van Dam',
             'match_type': 'Singles', 'title': 'ECW Television Championship',
             'about': 'RVD defended his legendary TV title reign.'},
        ])

        # ECW Closes - January 2001
        self.create_episode_with_matches(ecw, {
            'name': 'ECW Hardcore TV',
            'date': date(2001, 1, 13),
            'venue': 'ECW Arena',
            'location': 'Philadelphia, PA',
            'about': 'One of the final ECW shows before the company closed. The end of an era.'
        }, [
            {'wrestlers': ['Rhino', 'The Sandman'], 'winner': 'Rhino',
             'match_type': 'Singles', 'title': 'ECW World Heavyweight Championship',
             'about': 'Rhino as the final ECW World Champion.'},
            {'wrestlers': ['Rob Van Dam', 'Jerry Lynn'], 'winner': 'Rob Van Dam',
             'match_type': 'Singles', 'about': 'One final classic between the two rivals.'},
            {'wrestlers': ['Tommy Dreamer', 'Justin Credible'], 'winner': 'Tommy Dreamer',
             'match_type': 'Hardcore', 'about': 'The heart and soul of ECW in his home arena one final time.'},
        ])
