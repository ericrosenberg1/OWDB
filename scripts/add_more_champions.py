#!/usr/bin/env python
"""Add more missing champions to the database."""
import os
import sys
import django
import uuid

# Setup Django
sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'owdb_django.settings')
django.setup()

from owdb_django.owdbapp.models import Wrestler
from django.utils.text import slugify

# More notable missing champions
wrestlers_to_add = [
    # NWA/JCP/WCW era
    {
        'name': 'Dick the Bruiser',
        'real_name': 'William Richard Afflis',
        'about': 'Dick the Bruiser was one of the toughest wrestlers in history. A former NFL player, he competed from 1954 to 1985 and was a promoter in Indianapolis. Multiple-time AWA and WWA World Champion, he was known for his brawling style.',
        'hometown': 'Indianapolis, Indiana',
        'nationality': 'United States',
        'debut_year': 1954,
        'retirement_year': 1985,
    },
    {
        'name': 'The Crusher',
        'real_name': 'Reginald Lisowski',
        'about': 'The Crusher was a legendary tag team partner of Dick the Bruiser and a multiple-time AWA World Champion. Known for his blue-collar persona and stomping finishing move, he was one of the most popular wrestlers in the Midwest.',
        'hometown': 'Milwaukee, Wisconsin',
        'nationality': 'United States',
        'debut_year': 1949,
        'retirement_year': 1990,
    },
    {
        'name': 'Fritz Von Erich',
        'real_name': 'Jack Barton Adkisson',
        'about': 'Fritz Von Erich was a legendary wrestler and patriarch of the Von Erich wrestling family. He was the promoter of World Class Championship Wrestling in Dallas and father of Kevin, David, Kerry, Mike, and Chris Von Erich.',
        'hometown': 'Jewett, Texas',
        'nationality': 'United States',
        'debut_year': 1953,
        'retirement_year': 1982,
    },
    {
        'name': 'David Von Erich',
        'real_name': 'David Alan Adkisson',
        'about': 'David Von Erich was considered the most talented of the Von Erich brothers before his tragic death in 1984. He was WCCW World Champion and was being groomed for a run as NWA World Champion.',
        'hometown': 'Dallas, Texas',
        'nationality': 'United States',
        'debut_year': 1977,
        'retirement_year': 1984,
    },
    {
        'name': 'Mike Von Erich',
        'real_name': 'Michael Brett Adkisson',
        'about': 'Mike Von Erich was one of the Von Erich brothers who competed in WCCW. He held the WCWA World Championship before his tragic death in 1987.',
        'hometown': 'Dallas, Texas',
        'nationality': 'United States',
        'debut_year': 1983,
        'retirement_year': 1987,
    },
    {
        'name': 'Baron Von Raschke',
        'real_name': 'James Donald Raschke',
        'about': 'Baron Von Raschke was a legendary heel wrestler known for his German villain gimmick and the feared Brain Claw submission hold. He was AWA World Tag Team Champion and competed across the territories.',
        'hometown': 'Omaha, Nebraska',
        'nationality': 'United States',
        'debut_year': 1966,
        'retirement_year': 1995,
    },
    {
        'name': 'Wahoo McDaniel',
        'real_name': 'Edward Wahoo McDaniel',
        'about': 'Wahoo McDaniel was a Native American professional wrestler and former NFL linebacker. A legendary mid-card champion, he held multiple NWA United States and Mid-Atlantic championships. His chops were legendary.',
        'hometown': 'Bernice, Oklahoma',
        'nationality': 'United States',
        'debut_year': 1961,
        'retirement_year': 1996,
    },
    {
        'name': 'Magnum T.A.',
        'real_name': 'Terry Wayne Allen',
        'about': 'Magnum T.A. was one of the hottest rising stars in wrestling before a car accident ended his career in 1986. His feuds with Nikita Koloff and Tully Blanchard, including the famous I Quit match, are legendary.',
        'hometown': 'Norfolk, Virginia',
        'nationality': 'United States',
        'debut_year': 1978,
        'retirement_year': 1986,
    },
    {
        'name': 'Nikita Koloff',
        'real_name': 'Scott Alan Simpson',
        'about': 'Nikita Koloff was one of the most successful foreign heel characters in wrestling. Initially a Russian villain, he became a beloved babyface after his feud with Magnum T.A. He was NWA United States Champion.',
        'hometown': 'Minneapolis, Minnesota',
        'nationality': 'United States',
        'debut_year': 1984,
        'retirement_year': 1992,
    },
    {
        'name': 'The Rock n Roll Express',
        'real_name': 'Ricky Morton',
        'about': 'Ricky Morton is one half of the legendary Rock n Roll Express tag team with Robert Gibson. Multiple-time NWA World Tag Team Champions, they defined the babyface tag team formula that is still used today.',
        'hometown': 'Nashville, Tennessee',
        'nationality': 'United States',
        'debut_year': 1978,
    },
    {
        'name': 'Robert Gibson',
        'real_name': 'Ruben Edward Gibson',
        'about': 'Robert Gibson is one half of the Rock n Roll Express with Ricky Morton. Their feuds with the Midnight Express and other heel teams are legendary. Multiple-time NWA World Tag Team Champions.',
        'hometown': 'Pensacola, Florida',
        'nationality': 'United States',
        'debut_year': 1978,
    },
    {
        'name': 'Beautiful Bobby Eaton',
        'real_name': 'Robert Lee Eaton',
        'about': 'Bobby Eaton was considered one of the greatest tag team wrestlers ever. As part of the Midnight Express with Dennis Condrey and Stan Lane, he was a multiple-time NWA World Tag Team Champion known for his Alabama Jam.',
        'hometown': 'Huntsville, Alabama',
        'nationality': 'United States',
        'debut_year': 1976,
        'retirement_year': 2015,
    },
    {
        'name': 'Stan Lane',
        'real_name': 'Stanley Mark Lane',
        'about': 'Stan Lane was one half of the Midnight Express (with Bobby Eaton) and the Fabulous Ones (with Steve Keirn). He was known for his good looks and technical ability, winning multiple NWA Tag Team Championships.',
        'hometown': 'Winter Park, Florida',
        'nationality': 'United States',
        'debut_year': 1976,
        'retirement_year': 1994,
    },
    # Women's wrestling legends
    {
        'name': 'The Fabulous Moolah',
        'real_name': 'Mary Lillian Ellison',
        'about': 'The Fabulous Moolah was the most recognized female wrestler of the 20th century. She held the WWF Womens Championship for 28 years (though this is disputed) and trained generations of female wrestlers.',
        'hometown': 'Columbia, South Carolina',
        'nationality': 'United States',
        'debut_year': 1949,
        'retirement_year': 2007,
    },
    {
        'name': 'Mae Young',
        'real_name': 'Johnnie Mae Young',
        'about': 'Mae Young was a pioneer of womens professional wrestling. Competing from the 1930s until her death in 2014, she was NWA Womens Champion and remained active in WWE as a character until her 80s.',
        'hometown': 'Sand Springs, Oklahoma',
        'nationality': 'United States',
        'debut_year': 1939,
        'retirement_year': 2010,
    },
    {
        'name': 'Wendi Richter',
        'real_name': 'Wendi Richter',
        'about': 'Wendi Richter was a pioneer in bringing mainstream attention to womens wrestling through the Rock n Wrestling Connection with Cyndi Lauper. She defeated The Fabulous Moolah at WrestleMania I.',
        'hometown': 'Dallas, Texas',
        'nationality': 'United States',
        'debut_year': 1979,
        'retirement_year': 1987,
    },
    {
        'name': 'Alundra Blayze',
        'real_name': 'Debra Miceli',
        'about': 'Alundra Blayze (also known as Madusa) was a groundbreaking womens wrestler. She was WWF Womens Champion before jumping to WCW in the infamous trash can angle. She later became a monster truck driver.',
        'hometown': 'Minneapolis, Minnesota',
        'nationality': 'United States',
        'debut_year': 1984,
        'retirement_year': 2001,
    },
    {
        'name': 'Bull Nakano',
        'real_name': 'Keiko Nakano',
        'about': 'Bull Nakano was one of the greatest womens wrestlers ever. Dominant in AJW and later WWF, she was known for her imposing look and hard-hitting style. Her matches with Alundra Blayze are classics.',
        'hometown': 'Kawaguchi, Japan',
        'nationality': 'Japan',
        'debut_year': 1983,
        'retirement_year': 1997,
    },
    {
        'name': 'Dump Matsumoto',
        'real_name': 'Kaoru Matsumoto',
        'about': 'Dump Matsumoto was a legendary heel in Japanese womens wrestling. Known for her wild appearance and violent style, her feud with Chigusa Nagayo and the Crush Gals drew massive ratings in Japan.',
        'hometown': 'Tokyo, Japan',
        'nationality': 'Japan',
        'debut_year': 1980,
        'retirement_year': 1988,
    },
    {
        'name': 'Manami Toyota',
        'real_name': 'Manami Toyota',
        'about': 'Manami Toyota is widely considered the greatest womens wrestler of all time. In AJW during the 1990s, she revolutionized in-ring work with her incredible athleticism and innovative offense. Her matches with Aja Kong are legendary.',
        'hometown': 'Matsudo, Japan',
        'nationality': 'Japan',
        'debut_year': 1987,
        'retirement_year': 2017,
    },
    {
        'name': 'Aja Kong',
        'real_name': 'Erika Shishido',
        'about': 'Aja Kong is one of the most dominant womens wrestlers in history. Known for her size, power, and devastating uraken (spinning backfist), she was multiple-time WWWA World Champion in All Japan Women.',
        'hometown': 'Tokyo, Japan',
        'nationality': 'Japan',
        'debut_year': 1986,
    },
]

added = 0
for w_data in wrestlers_to_add:
    name = w_data['name']
    if not Wrestler.objects.filter(name=name).exists():
        base_slug = slugify(name)
        if Wrestler.objects.filter(slug=base_slug).exists():
            base_slug = f'{base_slug}-{str(uuid.uuid4())[:8]}'
        w_data['slug'] = base_slug
        try:
            w = Wrestler.objects.create(**w_data)
            print(f'Added: {name}')
            added += 1
        except Exception as e:
            print(f'Error: {name} - {e}')
    else:
        print(f'Exists: {name}')

print(f'\nTotal added: {added}')
print(f'Total wrestlers: {Wrestler.objects.count()}')
