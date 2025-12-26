#!/usr/bin/env python
"""Add modern champions to the database."""
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

# Modern champions (2020s era)
wrestlers_to_add = [
    # AEW Champions
    {
        'name': 'Thunder Rosa',
        'real_name': 'Melissa Cervantes',
        'about': 'Thunder Rosa is a Mexican-American professional wrestler and former AEW Womens World Champion. Known for her lucha libre style and face paint, she founded Mission Pro Wrestling and has competed in NWA, AEW, and international promotions.',
        'hometown': 'Tijuana, Mexico',
        'nationality': 'Mexico',
        'debut_year': 2014,
    },
    {
        'name': 'Mercedes Mone',
        'real_name': 'Mercedes Varnado',
        'about': 'Mercedes Mone (formerly Sasha Banks) is one of the most decorated womens wrestlers of her generation. A multi-time WWE Womens Champion and member of the Four Horsewomen, she is now competing in AEW and NJPW.',
        'hometown': 'Fairfield, California',
        'nationality': 'United States',
        'debut_year': 2010,
    },
    {
        'name': 'Toni Storm',
        'real_name': 'Toni Rossall',
        'about': 'Toni Storm is an Australian professional wrestler and former AEW Womens World Champion. Known for her retro Hollywood glamour persona, she has competed in WWE, NXT UK, Stardom, and AEW.',
        'hometown': 'Gold Coast, Australia',
        'nationality': 'Australia',
        'debut_year': 2009,
    },
    {
        'name': 'Mariah May',
        'real_name': 'Mariah May',
        'about': 'Mariah May is a British professional wrestler and AEW Womens World Champion. After competing in Stardom and NXT UK, she rose to prominence in AEW with her glamorous persona.',
        'hometown': 'Blackpool, England',
        'nationality': 'United Kingdom',
        'debut_year': 2020,
    },
    {
        'name': 'Swerve Strickland',
        'real_name': 'Shane Strickland',
        'about': 'Swerve Strickland is an American professional wrestler and former AEW World Champion. Known for his athletic style and charisma, he previously competed as Isaiah Swerve Scott in WWE NXT.',
        'hometown': 'Tacoma, Washington',
        'nationality': 'United States',
        'debut_year': 2011,
    },
    {
        'name': 'Samoa Joe',
        'real_name': 'Nuufolau Joel Seanoa',
        'about': 'Samoa Joe is a multi-time world champion across ROH, TNA, NXT, and AEW. Known for his hard-hitting style and devastating Muscle Buster, he is considered one of the greatest independent wrestlers turned mainstream star.',
        'hometown': 'Orange County, California',
        'nationality': 'United States',
        'debut_year': 1999,
    },
    # WWE Champions 2024
    {
        'name': 'Cody Rhodes',
        'real_name': 'Cody Garrett Runnels',
        'about': 'Cody Rhodes is the son of Dusty Rhodes and current WWE Champion. After leaving WWE, he helped create AEW before returning to WWE in 2022. His WrestleMania 40 victory completed his story to finish his fathers legacy.',
        'hometown': 'Marietta, Georgia',
        'nationality': 'United States',
        'debut_year': 2006,
    },
    {
        'name': 'Gunther',
        'real_name': 'Walter Hahn',
        'about': 'Gunther (formerly WALTER) is an Austrian professional wrestler and World Heavyweight Champion. The longest-reigning Intercontinental Champion in WWE history, he is known for his brutal chops and European strong style.',
        'hometown': 'Vienna, Austria',
        'nationality': 'Austria',
        'debut_year': 2005,
    },
    {
        'name': 'Nia Jax',
        'real_name': 'Savelina Fanene',
        'about': 'Nia Jax is an American professional wrestler and WWE Womens Champion. A former model and cousin of The Rock, she is known for her power moves and dominant presence in the womens division.',
        'hometown': 'San Diego, California',
        'nationality': 'United States',
        'debut_year': 2014,
    },
    {
        'name': 'Liv Morgan',
        'real_name': 'Gionna Daddio',
        'about': 'Liv Morgan is an American professional wrestler and current Womens World Champion. Rising from the Riott Squad, she has become one of the top stars in WWE with her technical ability and revenge tour storyline.',
        'hometown': 'Elmwood Park, New Jersey',
        'nationality': 'United States',
        'debut_year': 2014,
    },
    {
        'name': 'Bron Breakker',
        'real_name': 'Bronson Rechsteiner',
        'about': 'Bron Breakker is the son of Rick Steiner and nephew of Scott Steiner. A two-time NXT Champion and current Intercontinental Champion, he combines his family legacy with explosive athleticism.',
        'hometown': 'Woodstock, Georgia',
        'nationality': 'United States',
        'debut_year': 2021,
    },
    {
        'name': 'LA Knight',
        'real_name': 'Shaun Ricker',
        'about': 'LA Knight is one of the most popular wrestlers in WWE. After years on the independent circuit as Eli Drake, he has become a main event star known for his catchphrase YEAH and mic skills.',
        'hometown': 'Burbank, California',
        'nationality': 'United States',
        'debut_year': 2003,
    },
    # NJPW Current Champions
    {
        'name': 'Zack Sabre Jr.',
        'real_name': 'Zack Mayence',
        'about': 'Zack Sabre Jr. is a British technical wrestling master and current IWGP World Heavyweight Champion. Known for his incredible submission arsenal and limb work, he has revolutionized catch wrestling in the modern era.',
        'hometown': 'Sheerness, England',
        'nationality': 'United Kingdom',
        'debut_year': 2004,
    },
    {
        'name': 'Jeff Cobb',
        'real_name': 'Jeffrey Theodore Cobb',
        'about': 'Jeff Cobb is an American-Guamanian professional wrestler competing in NJPW and ROH. A former Olympian, he is known for his incredible strength and the Tour of the Islands finisher.',
        'hometown': 'Honolulu, Hawaii',
        'nationality': 'United States',
        'debut_year': 2009,
    },
    {
        'name': 'David Finlay',
        'real_name': 'David Finlay Jr.',
        'about': 'David Finlay is an Irish professional wrestler in NJPW and the leader of the Bullet Club War Dogs. The son of legendary wrestler Fit Finlay, he has become a top heel in New Japan.',
        'hometown': 'Carrickfergus, Northern Ireland',
        'nationality': 'Ireland',
        'debut_year': 2012,
    },
    {
        'name': 'El Phantasmo',
        'real_name': 'Michael Furguson',
        'about': 'El Phantasmo is a Canadian professional wrestler in NJPW. A former IWGP Junior Heavyweight Champion and member of Bullet Club, he is known for his high-flying style and comedic heel work.',
        'hometown': 'Vancouver, British Columbia, Canada',
        'nationality': 'Canada',
        'debut_year': 2006,
    },
    # Indie Stars
    {
        'name': 'Josh Alexander',
        'real_name': 'Joshua Lemay',
        'about': 'Josh Alexander is a Canadian professional wrestler and former Impact World Champion. Known as The Walking Weapon for his amateur wrestling background, he is one of the top workers in Impact Wrestling.',
        'hometown': 'Niagara Falls, Ontario, Canada',
        'nationality': 'Canada',
        'debut_year': 2005,
    },
    {
        'name': 'Moose',
        'real_name': 'Quinn Ojinnaka',
        'about': 'Moose is an American professional wrestler and former Impact World Champion. A former NFL player, he brings incredible athleticism to wrestling with his power moves and spear.',
        'hometown': 'Austell, Georgia',
        'nationality': 'United States',
        'debut_year': 2012,
    },
    {
        'name': 'Jordynne Grace',
        'real_name': 'Patricia Parker',
        'about': 'Jordynne Grace is an American professional wrestler and Impact Knockouts Champion. Known for her incredible strength and muscle buster, she is one of the top womens wrestlers outside WWE and AEW.',
        'hometown': 'Austin, Texas',
        'nationality': 'United States',
        'debut_year': 2015,
    },
    {
        'name': 'Nick Aldis',
        'real_name': 'Nicholas Aldis',
        'about': 'Nick Aldis is a British professional wrestler and multi-time NWA Worlds Heavyweight Champion. Now a WWE producer and occasional performer, he helped revive the NWA under Billy Corgan.',
        'hometown': 'King Lynn, England',
        'nationality': 'United Kingdom',
        'debut_year': 2003,
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
