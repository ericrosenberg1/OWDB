"""
Major Promotions Coverage Seeder.

Ensures comprehensive coverage for AAA, NJPW, and other major promotions.

Usage:
    python manage.py seed_major_promotions
"""
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from datetime import date, timedelta
from owdb_django.owdbapp.models import (
    Wrestler, Promotion, Event, Title, Venue, Stable
)


class Command(BaseCommand):
    help = 'Ensure comprehensive coverage for major international promotions'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n=== MAJOR PROMOTIONS COVERAGE ===\n'))

        # AAA (Mexico)
        created = self.seed_aaa()
        self.stdout.write(f'--- AAA: {created} items added')

        # NJPW (Japan)
        created = self.seed_njpw()
        self.stdout.write(f'--- NJPW: {created} items added')

        # CMLL (Mexico)
        created = self.seed_cmll()
        self.stdout.write(f'--- CMLL: {created} items added')

        # NOAH (Japan)
        created = self.seed_noah()
        self.stdout.write(f'--- NOAH: {created} items added')

        # All Japan
        created = self.seed_ajpw()
        self.stdout.write(f'--- AJPW: {created} items added')

        # Dragon Gate
        created = self.seed_dragongate()
        self.stdout.write(f'--- Dragon Gate: {created} items added')

        # ROH
        created = self.seed_roh()
        self.stdout.write(f'--- ROH: {created} items added')

        # Impact/TNA
        created = self.seed_impact()
        self.stdout.write(f'--- Impact: {created} items added')

        # Database summary
        self.stdout.write(self.style.SUCCESS('\n=== DATABASE SUMMARY ==='))
        self.stdout.write(f'  Events: {Event.objects.count():,}')
        self.stdout.write(f'  Wrestlers: {Wrestler.objects.count():,}')
        self.stdout.write(f'  Titles: {Title.objects.count():,}')
        self.stdout.write(f'  Promotions: {Promotion.objects.count():,}')
        self.stdout.write(f'  Stables: {Stable.objects.count():,}')

    def get_or_create_promotion(self, name, slug=None):
        slug = slug or slugify(name)
        promo, _ = Promotion.objects.get_or_create(
            slug=slug,
            defaults={'name': name}
        )
        return promo

    def get_or_create_wrestler(self, name):
        wrestler = Wrestler.objects.filter(name__iexact=name).first()
        if not wrestler:
            slug = slugify(name)
            wrestler = Wrestler.objects.filter(slug=slug).first()
            if not wrestler:
                wrestler = Wrestler.objects.create(name=name, slug=slug)
        return wrestler

    def get_or_create_title(self, name, promotion):
        slug = slugify(f"{name}-{promotion.slug}")
        title, created = Title.objects.get_or_create(
            slug=slug,
            defaults={'name': name, 'promotion': promotion}
        )
        return title, created

    def get_or_create_stable(self, name, promotion, members=None):
        slug = slugify(name)
        stable, created = Stable.objects.get_or_create(
            slug=slug,
            defaults={'name': name, 'promotion': promotion}
        )
        if created and members:
            for member_name in members:
                wrestler = self.get_or_create_wrestler(member_name)
                stable.members.add(wrestler)
        return stable, created

    def seed_aaa(self):
        """Seed AAA (Lucha Libre AAA Worldwide) content."""
        created = 0
        aaa = self.get_or_create_promotion('Lucha Libre AAA Worldwide', 'aaa')

        # AAA Titles
        aaa_titles = [
            'AAA Mega Championship',
            'AAA Latin American Championship',
            'AAA World Tag Team Championship',
            'AAA World Mixed Tag Team Championship',
            'AAA World Cruiserweight Championship',
            'AAA World Trios Championship',
            'AAA Reina de Reinas Championship',
        ]
        for title_name in aaa_titles:
            _, c = self.get_or_create_title(title_name, aaa)
            if c: created += 1

        # AAA Wrestlers
        aaa_wrestlers = [
            'El Hijo del Vikingo', 'Psycho Clown', 'Pentagon Jr', 'Rey Fenix',
            'Pagano', 'Laredo Kid', 'Taurus', 'Daga', 'Drago', 'Aerostar',
            'Myzteziz Jr', 'Octagon Jr', 'Komander', 'Bandido', 'Flamita',
            'Puma King', 'Negro Casas', 'Blue Demon Jr', 'Dr. Wagner Jr',
            'LA Park', 'Chessman', 'Monster Clown', 'Murder Clown',
            'Konnan', 'Vampiro', 'Cibernetico', 'Heavy Metal', 'Electroshock',
            'Lady Shani', 'Faby Apache', 'La Hiedra', 'Flammer', 'Sexy Star',
        ]
        for name in aaa_wrestlers:
            w = self.get_or_create_wrestler(name)
            if w.pk: created += 1

        # AAA Stables
        stables_data = [
            ('Los Mercenarios', ['El Hijo del Vikingo', 'Taurus', 'Laredo Kid']),
            ('Los Jinetes del Aire', ['Pentagon Jr', 'Rey Fenix', 'Laredo Kid']),
            ('Los Vipers', ['Pagano', 'Chessman', 'Monster Clown']),
            ('Los Hell Brothers', ['Pentagon Jr', 'Rey Fenix']),
        ]
        for name, members in stables_data:
            _, c = self.get_or_create_stable(name, aaa, members)
            if c: created += 1

        # AAA Major Events (Triplemania)
        for year in range(1993, 2025):
            slug = slugify(f'triplemania-{year}')
            event, c = Event.objects.get_or_create(
                slug=slug,
                defaults={
                    'name': f'Triplemania {year}',
                    'date': date(year, 8, 15),  # Approximate
                    'promotion': aaa,
                }
            )
            if c: created += 1

        return created

    def seed_njpw(self):
        """Seed NJPW (New Japan Pro Wrestling) content."""
        created = 0
        njpw = self.get_or_create_promotion('New Japan Pro Wrestling', 'njpw')

        # NJPW Titles
        njpw_titles = [
            'IWGP World Heavyweight Championship',
            'IWGP Heavyweight Championship',
            'IWGP Intercontinental Championship',
            'IWGP United States Heavyweight Championship',
            'IWGP Tag Team Championship',
            'IWGP Junior Heavyweight Championship',
            'IWGP Junior Heavyweight Tag Team Championship',
            'NEVER Openweight Championship',
            'NEVER Openweight 6-Man Tag Team Championship',
            'STRONG Openweight Championship',
            'King of Pro-Wrestling',
        ]
        for title_name in njpw_titles:
            _, c = self.get_or_create_title(title_name, njpw)
            if c: created += 1

        # NJPW Wrestlers
        njpw_wrestlers = [
            'Kazuchika Okada', 'Hiroshi Tanahashi', 'Tetsuya Naito', 'Will Ospreay',
            'SANADA', 'Shingo Takagi', 'Kota Ibushi', 'Jay White', 'EVIL',
            'Tomohiro Ishii', 'Hirooki Goto', 'YOSHI-HASHI', 'Zack Sabre Jr',
            'Minoru Suzuki', 'Taichi', 'El Desperado', 'DOUKI', 'TAKA Michinoku',
            'Hiromu Takahashi', 'BUSHI', 'Titan', 'Robbie Eagles', 'TJP',
            'Jeff Cobb', 'Great-O-Khan', 'Aaron Henare', 'Ren Narita',
            'Shota Umino', 'Yota Tsuji', 'Master Wato', 'Ryusuke Taguchi',
            'Toru Yano', 'Tomoaki Honma', 'Juice Robinson', 'David Finlay',
            'Tama Tonga', 'Tanga Loa', 'Jado', 'Gedo', 'Chase Owens',
            'Bad Luck Fale', 'Hikuleo', 'El Phantasmo', 'KENTA',
        ]
        for name in njpw_wrestlers:
            w = self.get_or_create_wrestler(name)
            if w.pk: created += 1

        # NJPW Stables
        stables_data = [
            ('Los Ingobernables de Japon', ['Tetsuya Naito', 'SANADA', 'Shingo Takagi', 'EVIL', 'BUSHI', 'Hiromu Takahashi', 'Titan']),
            ('Bullet Club', ['Jay White', 'Tama Tonga', 'Tanga Loa', 'Bad Luck Fale', 'El Phantasmo', 'KENTA', 'Chase Owens', 'Gedo']),
            ('CHAOS', ['Kazuchika Okada', 'Tomohiro Ishii', 'YOSHI-HASHI', 'Hirooki Goto', 'Toru Yano', 'Robbie Eagles']),
            ('Suzuki-gun', ['Minoru Suzuki', 'Taichi', 'Zack Sabre Jr', 'El Desperado', 'DOUKI']),
            ('United Empire', ['Will Ospreay', 'Jeff Cobb', 'Great-O-Khan', 'Aaron Henare', 'TJP', 'Francesco Akira']),
            ('TMDK', ['Zack Sabre Jr', 'Kosei Fujita', 'Robbie Eagles', 'Shane Haste', 'Mikey Nicholls']),
            ('House of Torture', ['EVIL', 'Dick Togo', 'Sho', 'Yujiro Takahashi']),
        ]
        for name, members in stables_data:
            _, c = self.get_or_create_stable(name, njpw, members)
            if c: created += 1

        # NJPW Major Events
        major_events = [
            ('Wrestle Kingdom', 1, 4),  # January
            ('New Beginning', 2, 11),  # February
            ('Anniversary Show', 3, 6),  # March
            ('Sakura Genesis', 4, 9),  # April
            ('Wrestling Dontaku', 5, 3),  # May
            ('Dominion', 6, 9),  # June
            ('G1 Climax Finals', 8, 18),  # August
            ('Destruction', 9, 24),  # September
            ('King of Pro-Wrestling', 10, 14),  # October
            ('Power Struggle', 11, 5),  # November
            ('World Tag League Finals', 12, 11),  # December
        ]

        for year in range(2000, 2025):
            for event_name, month, day in major_events:
                event_full = f'{event_name} {year}'
                slug = slugify(f'{event_name}-{year}')
                try:
                    event, c = Event.objects.get_or_create(
                        slug=slug,
                        defaults={
                            'name': event_full,
                            'date': date(year, month, day),
                            'promotion': njpw,
                        }
                    )
                    if c: created += 1
                except:
                    pass

        return created

    def seed_cmll(self):
        """Seed CMLL (Consejo Mundial de Lucha Libre) content."""
        created = 0
        cmll = self.get_or_create_promotion('Consejo Mundial de Lucha Libre', 'cmll')

        # CMLL Titles
        cmll_titles = [
            'CMLL World Heavyweight Championship',
            'CMLL World Light Heavyweight Championship',
            'CMLL World Welterweight Championship',
            'CMLL World Middleweight Championship',
            'CMLL World Lightweight Championship',
            'CMLL World Super Lightweight Championship',
            'CMLL World Mini-Estrella Championship',
            'CMLL World Tag Team Championship',
            'CMLL World Trios Championship',
            'CMLL World Womens Championship',
            'Mexican National Heavyweight Championship',
            'Mexican National Light Heavyweight Championship',
            'Mexican National Welterweight Championship',
            'Mexican National Trios Championship',
        ]
        for title_name in cmll_titles:
            _, c = self.get_or_create_title(title_name, cmll)
            if c: created += 1

        # CMLL Wrestlers
        cmll_wrestlers = [
            'Mistico', 'Atlantis', 'Ultimo Guerrero', 'Negro Casas', 'Volador Jr',
            'Caristico', 'Dragon Lee', 'Angel de Oro', 'Niebla Roja', 'Titan',
            'Soberano Jr', 'Templario', 'Euforia', 'Gran Guerrero', 'Stuka Jr',
            'Valiente', 'Diamante Azul', 'Rush', 'Terrible', 'Mascara Dorada',
            'La Sombra', 'Mephisto', 'Averno', 'Hechicero', 'Cuatrero',
            'Sanson', 'Forastero', 'Principe Aereo', 'Dulce Gardenia',
            'Star Jr', 'Fugaz', 'El Desperado', 'Guerrero Maya Jr',
        ]
        for name in cmll_wrestlers:
            w = self.get_or_create_wrestler(name)
            if w.pk: created += 1

        # CMLL Major Events
        for year in range(1990, 2025):
            slug = slugify(f'cmll-anniversary-{year}')
            event, c = Event.objects.get_or_create(
                slug=slug,
                defaults={
                    'name': f'CMLL Anniversary Show {year}',
                    'date': date(year, 9, 16),
                    'promotion': cmll,
                }
            )
            if c: created += 1

        return created

    def seed_noah(self):
        """Seed Pro Wrestling NOAH content."""
        created = 0
        noah = self.get_or_create_promotion('Pro Wrestling NOAH', 'noah')

        # NOAH Titles
        noah_titles = [
            'GHC Heavyweight Championship',
            'GHC National Championship',
            'GHC Tag Team Championship',
            'GHC Junior Heavyweight Championship',
            'GHC Junior Heavyweight Tag Team Championship',
        ]
        for title_name in noah_titles:
            _, c = self.get_or_create_title(title_name, noah)
            if c: created += 1

        # NOAH Wrestlers
        noah_wrestlers = [
            'Mitsuharu Misawa', 'Kenta Kobashi', 'Jun Akiyama', 'Naomichi Marufuji',
            'KENTA', 'Go Shiozaki', 'Takeshi Morishima', 'Akitoshi Saito',
            'Yoshinari Ogawa', 'Masao Inoue', 'Kotaro Suzuki', 'Atsushi Aoki',
            'Taiji Ishimori', 'Hajime Ohara', 'Kenou', 'Kaito Kiyomiya',
            'Masa Kitamiya', 'Takashi Sugiura', 'Shuhei Taniguchi', 'Satoshi Kojima',
        ]
        for name in noah_wrestlers:
            w = self.get_or_create_wrestler(name)
            if w.pk: created += 1

        # NOAH Major Events
        major_events = ['Departure', 'Great Voyage', 'The Great Voyage', 'Navigation', 'Destiny']
        for year in range(2000, 2025):
            for event in major_events[:2]:  # Just first two events per year
                slug = slugify(f'noah-{event}-{year}')
                event_obj, c = Event.objects.get_or_create(
                    slug=slug,
                    defaults={
                        'name': f'NOAH {event} {year}',
                        'date': date(year, 7, 15),
                        'promotion': noah,
                    }
                )
                if c: created += 1

        return created

    def seed_ajpw(self):
        """Seed All Japan Pro Wrestling content."""
        created = 0
        ajpw = self.get_or_create_promotion('All Japan Pro Wrestling', 'ajpw')

        # AJPW Titles
        ajpw_titles = [
            'Triple Crown Heavyweight Championship',
            'AJPW World Tag Team Championship',
            'AJPW World Junior Heavyweight Championship',
            'AJPW All Asia Tag Team Championship',
        ]
        for title_name in ajpw_titles:
            _, c = self.get_or_create_title(title_name, ajpw)
            if c: created += 1

        # AJPW Wrestlers
        ajpw_wrestlers = [
            'Giant Baba', 'Jumbo Tsuruta', 'Mitsuharu Misawa', 'Toshiaki Kawada',
            'Kenta Kobashi', 'Akira Taue', 'Stan Hansen', 'Terry Gordy',
            'Steve Williams', 'Jun Akiyama', 'Genichiro Tenryu', 'Satoshi Kojima',
            'Keiji Mutoh', 'Suwama', 'Joe Doering', 'Zeus', 'Kento Miyahara',
            'Jake Lee', 'Yuma Aoyagi', 'Shuji Ishikawa', 'Ryuki Honda',
        ]
        for name in ajpw_wrestlers:
            w = self.get_or_create_wrestler(name)
            if w.pk: created += 1

        # AJPW Champions Carnival
        for year in range(1973, 2025):
            slug = slugify(f'ajpw-champions-carnival-{year}')
            event, c = Event.objects.get_or_create(
                slug=slug,
                defaults={
                    'name': f'AJPW Champions Carnival {year}',
                    'date': date(year, 4, 20),
                    'promotion': ajpw,
                }
            )
            if c: created += 1

        return created

    def seed_dragongate(self):
        """Seed Dragon Gate content."""
        created = 0
        dg = self.get_or_create_promotion('Dragon Gate', 'dragongate')

        # Dragon Gate Titles
        dg_titles = [
            'Open The Dream Gate Championship',
            'Open The Twin Gate Championship',
            'Open The Triangle Gate Championship',
            'Open The Brave Gate Championship',
            'Open The Owarai Gate Championship',
        ]
        for title_name in dg_titles:
            _, c = self.get_or_create_title(title_name, dg)
            if c: created += 1

        # Dragon Gate Wrestlers
        dg_wrestlers = [
            'CIMA', 'Dragon Kid', 'Masaaki Mochizuki', 'Don Fujii', 'Genki Horiguchi',
            'Ryo Saito', 'Susumu Yokosuka', 'Naruki Doi', 'Shingo Takagi', 'BxB Hulk',
            'Masato Yoshino', 'PAC', 'Ricochet', 'Akira Tozawa', 'Yamato', 'Shun Skywalker',
            'Kzy', 'Ben-K', 'Eita', 'Kaito Ishida', 'SB Kento', 'Yuki Yoshioka',
        ]
        for name in dg_wrestlers:
            w = self.get_or_create_wrestler(name)
            if w.pk: created += 1

        return created

    def seed_roh(self):
        """Seed Ring of Honor content."""
        created = 0
        roh = self.get_or_create_promotion('Ring of Honor', 'roh')

        # ROH Titles
        roh_titles = [
            'ROH World Championship',
            'ROH World Television Championship',
            'ROH World Tag Team Championship',
            'ROH Pure Championship',
            'ROH World Six-Man Tag Team Championship',
            'ROH Womens World Championship',
        ]
        for title_name in roh_titles:
            _, c = self.get_or_create_title(title_name, roh)
            if c: created += 1

        # ROH Wrestlers
        roh_wrestlers = [
            'Bryan Danielson', 'Samoa Joe', 'CM Punk', 'Nigel McGuinness', 'Austin Aries',
            'Tyler Black', 'Roderick Strong', 'Kevin Steen', 'El Generico', 'Adam Cole',
            'Jay Lethal', 'The Briscoe Brothers', 'Christopher Daniels', 'Frankie Kazarian',
            'AJ Styles', 'Low Ki', 'Homicide', 'Colt Cabana', 'Claudio Castagnoli',
            'Matt Sydal', 'Delirious', 'Eddie Edwards', 'Davey Richards', 'Kyle OReilly',
            'Bobby Fish', 'The Young Bucks', 'Kenny Omega', 'Marty Scurll', 'Dalton Castle',
        ]
        for name in roh_wrestlers:
            w = self.get_or_create_wrestler(name)
            if w.pk: created += 1

        # ROH Major PPVs
        major_events = [
            'Final Battle',
            'Supercard of Honor',
            'Death Before Dishonor',
            'Best in the World',
        ]
        for year in range(2003, 2025):
            for event in major_events:
                slug = slugify(f'roh-{event}-{year}')
                try:
                    event_obj, c = Event.objects.get_or_create(
                        slug=slug,
                        defaults={
                            'name': f'ROH {event} {year}',
                            'date': date(year, 12, 15) if event == 'Final Battle' else date(year, 6, 1),
                            'promotion': roh,
                        }
                    )
                    if c: created += 1
                except:
                    pass

        return created

    def seed_impact(self):
        """Seed Impact Wrestling / TNA content."""
        created = 0
        impact = self.get_or_create_promotion('Impact Wrestling', 'impact')
        tna = self.get_or_create_promotion('Total Nonstop Action Wrestling', 'tna')

        # Impact/TNA Titles
        impact_titles = [
            'TNA World Heavyweight Championship',
            'Impact World Championship',
            'TNA X Division Championship',
            'Impact X Division Championship',
            'TNA World Tag Team Championship',
            'Impact World Tag Team Championship',
            'TNA Knockouts Championship',
            'Impact Knockouts Championship',
            'TNA Television Championship',
            'Impact Digital Media Championship',
        ]
        for title_name in impact_titles:
            _, c = self.get_or_create_title(title_name, impact)
            if c: created += 1

        # Impact Wrestlers
        impact_wrestlers = [
            'AJ Styles', 'Samoa Joe', 'Christopher Daniels', 'Kurt Angle', 'Sting',
            'Jeff Jarrett', 'Abyss', 'James Storm', 'Bobby Roode', 'Austin Aries',
            'Magnus', 'EC3', 'Lashley', 'Drew McIntyre', 'Jeff Hardy', 'Matt Hardy',
            'The Dudley Boyz', 'Team 3D', 'Christian Cage', 'Rhino', 'Raven',
            'Scott Steiner', 'Kevin Nash', 'Hulk Hogan', 'Ric Flair', 'Mick Foley',
            'Gail Kim', 'Awesome Kong', 'ODB', 'Velvet Sky', 'Angelina Love',
            'Frankie Kazarian', 'Chris Sabin', 'Alex Shelley', 'Jay Lethal',
            'Motor City Machine Guns', 'Beer Money', 'LAX', 'Petey Williams',
            'Eric Young', 'Moose', 'Eddie Edwards', 'Trey Miguel', 'Josh Alexander',
        ]
        for name in impact_wrestlers:
            w = self.get_or_create_wrestler(name)
            if w.pk: created += 1

        # Impact/TNA Major Events
        major_events = [
            'Bound for Glory',
            'Lockdown',
            'Slammiversary',
            'No Surrender',
            'Turning Point',
            'Genesis',
            'Hard Justice',
            'Sacrifice',
        ]
        for year in range(2004, 2025):
            for event in major_events[:4]:  # Top 4 events per year
                slug = slugify(f'tna-{event}-{year}')
                try:
                    event_obj, c = Event.objects.get_or_create(
                        slug=slug,
                        defaults={
                            'name': f'TNA {event} {year}',
                            'date': date(year, 10, 15) if event == 'Bound for Glory' else date(year, 6, 15),
                            'promotion': impact,
                        }
                    )
                    if c: created += 1
                except:
                    pass

        return created
