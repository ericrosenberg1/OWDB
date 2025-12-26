#!/usr/bin/env python
"""Add missing legendary champions to the database."""
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

# Add missing legendary champions
wrestlers_to_add = [
    {
        'name': 'Superstar Billy Graham',
        'real_name': 'Eldridge Wayne Coleman',
        'about': 'Superstar Billy Graham was one of the most influential professional wrestlers in history. As WWWF Champion from 1977-1978, his combination of physique, charisma, and promo ability influenced generations including Hulk Hogan, Jesse Ventura, and Triple H. His flashy attire and boastful interviews established the template for the modern wrestling heel.',
        'hometown': 'Phoenix, Arizona',
        'nationality': 'United States',
        'debut_year': 1969,
        'retirement_year': 1989,
    },
    {
        'name': 'The Great Muta',
        'real_name': 'Keiji Mutoh',
        'about': 'The Great Muta is the legendary alter ego of Keiji Mutoh, one of the greatest Japanese wrestlers of all time. Known for his painted face, dramatic entrance, and the signature green mist, Muta was a crossover star in WCW, NJPW, and All Japan. He popularized the moonsault and the Shining Wizard.',
        'hometown': 'Yamanashi, Japan',
        'nationality': 'Japan',
        'debut_year': 1984,
    },
    {
        'name': 'Mil Mascaras',
        'real_name': 'Aaron Rodriguez Arellano',
        'about': 'Mil Mascaras (The Man of 1,000 Masks) is a Mexican lucha libre legend and one of the first masked wrestlers to achieve international fame. Debuting in 1965, he brought lucha libre to audiences worldwide and influenced countless wrestlers with his high-flying style. He is a WWE Hall of Famer.',
        'hometown': 'San Luis Potosi, Mexico',
        'nationality': 'Mexico',
        'debut_year': 1965,
    },
    {
        'name': 'El Hijo del Santo',
        'real_name': 'Jorge Rodriguez',
        'about': 'El Hijo del Santo is the son of legendary luchador El Santo and one of the greatest masked wrestlers of his era. Carrying on his fathers legacy, he competed in CMLL, AAA, and internationally, known for his technical excellence and aerial abilities. His matches with Negro Casas are considered among the best in lucha libre history.',
        'hometown': 'Mexico City, Mexico',
        'nationality': 'Mexico',
        'debut_year': 1982,
    },
    {
        'name': 'Dr. Wagner Jr.',
        'real_name': 'Juan Manuel Gonzalez Barron',
        'about': 'Dr. Wagner Jr. is a Mexican professional wrestler and one of the biggest stars in lucha libre. The son of Dr. Wagner, he has competed in AAA, CMLL, and various promotions worldwide. Known for his feuds with El Hijo del Santo and his reign as AAA Mega Champion.',
        'hometown': 'Torreon, Mexico',
        'nationality': 'Mexico',
        'debut_year': 1986,
    },
    {
        'name': 'L.A. Park',
        'real_name': 'Adolfo Tapia Ibarra',
        'about': 'L.A. Park (formerly known as La Parka in AAA) is one of the most charismatic wrestlers in lucha libre. Known for his skull mask, dancing, and comedic style, he became a fan favorite in WCW and AAA. He is a multiple-time champion in AAA, CMLL, and independent promotions.',
        'hometown': 'Aguascalientes, Mexico',
        'nationality': 'Mexico',
        'debut_year': 1987,
    },
    {
        'name': 'Cien Caras',
        'real_name': 'Carmelo Reyes Gonzalez',
        'about': 'Cien Caras (100 Faces) is a legendary Mexican luchador and patriarch of the Munoz wrestling family. As leader of Los Capos, he was one of the top rudos in CMLL and UWA. His sons include Mascara Ano 2000 Jr. and other notable wrestlers.',
        'hometown': 'Gomez Palacio, Mexico',
        'nationality': 'Mexico',
        'debut_year': 1979,
    },
    # More notable missing champions
    {
        'name': 'Vader',
        'real_name': 'Leon Allen White',
        'about': 'Vader (Big Van Vader) was one of the most dominant super heavyweights in wrestling history. A three-time WCW World Champion, IWGP Champion, and AJPW Triple Crown Champion, he was known for his incredible agility despite his size. His moonsault was legendary.',
        'hometown': 'Lynwood, California',
        'nationality': 'United States',
        'debut_year': 1985,
        'retirement_year': 2017,
    },
    {
        'name': 'Tatsumi Fujinami',
        'real_name': 'Tatsumi Fujinami',
        'about': 'Tatsumi Fujinami is a Japanese wrestling legend known as The Dragon. He held the IWGP Heavyweight Championship and was NWA World Heavyweight Champion. His technical wrestling style influenced generations of Japanese wrestlers.',
        'hometown': 'Oita, Japan',
        'nationality': 'Japan',
        'debut_year': 1971,
    },
    {
        'name': 'Shinya Hashimoto',
        'real_name': 'Shinya Hashimoto',
        'about': 'Shinya Hashimoto was one of the Three Musketeers of New Japan Pro-Wrestling along with Masahiro Chono and Keiji Mutoh. He was a three-time IWGP Heavyweight Champion known for his hard-hitting style and devastating kicks.',
        'hometown': 'Tochigi, Japan',
        'nationality': 'Japan',
        'debut_year': 1984,
        'retirement_year': 2005,
    },
    {
        'name': 'Masahiro Chono',
        'real_name': 'Masahiro Chono',
        'about': 'Masahiro Chono is a Japanese wrestling legend and member of the Three Musketeers. A two-time IWGP Heavyweight Champion and five-time G1 Climax winner, he was the leader of the nWo Japan faction.',
        'hometown': 'Kofu, Japan',
        'nationality': 'Japan',
        'debut_year': 1984,
        'retirement_year': 2014,
    },
    {
        'name': 'Riki Choshu',
        'real_name': 'Mitsuo Yoshida',
        'about': 'Riki Choshu is a Korean-Japanese professional wrestler who revolutionized New Japan Pro-Wrestling. His rivalry with Antonio Inoki defined the 1980s, and his lariat finishing move became iconic. He is credited with creating the modern NJPW style.',
        'hometown': 'Seoul, South Korea',
        'nationality': 'Japan',
        'debut_year': 1974,
        'retirement_year': 2019,
    },
    {
        'name': 'Genichiro Tenryu',
        'real_name': 'Genichiro Shimada',
        'about': 'Genichiro Tenryu was one of the most respected wrestlers in Japanese wrestling history. A former sumo wrestler, he competed in All Japan, founded SWS, and feuded with the biggest names across multiple promotions. His match quality was legendary even into his 60s.',
        'hometown': 'Akita, Japan',
        'nationality': 'Japan',
        'debut_year': 1976,
        'retirement_year': 2015,
    },
    {
        'name': 'Stan Hansen',
        'real_name': 'John Stanley Hansen',
        'about': 'Stan Hansen was an American professional wrestler who became a legend in Japan. Known for his brutal lariat and wild style, he was a multiple-time Triple Crown Champion in AJPW and IWGP Champion in NJPW. He is considered one of the greatest gaijin wrestlers ever.',
        'hometown': 'Borger, Texas',
        'nationality': 'United States',
        'debut_year': 1973,
        'retirement_year': 2001,
    },
    {
        'name': 'Bruiser Brody',
        'real_name': 'Frank Donald Goodish',
        'about': 'Bruiser Brody was one of the most intense and unpredictable wrestlers in history. Known for his wild man persona and chainsaw entrance, he was a star in WWC Puerto Rico, AJPW, and throughout the territories. His tragic death in 1988 shocked the wrestling world.',
        'hometown': 'Detroit, Michigan',
        'nationality': 'United States',
        'debut_year': 1973,
        'retirement_year': 1988,
    },
    {
        'name': 'Abdullah the Butcher',
        'real_name': 'Lawrence Robert Shreve',
        'about': 'Abdullah the Butcher is a Canadian professional wrestler known for his hardcore style and bloodbaths. Wrestling across multiple continents for over 50 years, he was infamous for his fork attacks and the deep scars on his forehead from decades of blading.',
        'hometown': 'Windsor, Ontario, Canada',
        'nationality': 'Canada',
        'debut_year': 1958,
    },
    {
        'name': 'Chavo Guerrero Sr.',
        'real_name': 'Salvador Guerrero III',
        'about': 'Chavo Guerrero Sr. was a Mexican-American professional wrestler and patriarch of the Guerrero wrestling dynasty. He competed in NWA territories, WWF, and across Mexico. His sons include Chavo Jr. and nephew was the legendary Eddie Guerrero.',
        'hometown': 'El Paso, Texas',
        'nationality': 'United States',
        'debut_year': 1970,
        'retirement_year': 2006,
    },
    {
        'name': 'Gory Guerrero',
        'real_name': 'Salvador Guerrero Quesada',
        'about': 'Gory Guerrero was the patriarch of the Guerrero wrestling family and one of the greatest technical wrestlers of his era. He invented the Gory Special submission hold and trained some of the greatest wrestlers in history. Father of Eddie, Chavo, Hector, and Mando Guerrero.',
        'hometown': 'Mexico City, Mexico',
        'nationality': 'Mexico',
        'debut_year': 1937,
        'retirement_year': 1970,
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
