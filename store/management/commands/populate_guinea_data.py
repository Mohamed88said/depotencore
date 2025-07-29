from django.core.management.base import BaseCommand
from store.models import GuineaRegion, GuineaPrefecture, GuineaQuartier

class Command(BaseCommand):
    help = 'Populate Guinea administrative divisions'

    def handle(self, *args, **options):
        # Données administratives de la Guinée
        guinea_data = {
            'Conakry': {
                'code': 'CKY',
                'prefectures': {
                    'Dixinn': ['Hamdallaye', 'Dixinn Centre', 'Dixinn Port', 'Minière'],
                    'Kaloum': ['Kaloum Centre', 'Almamya', 'Boulbinet', 'Tombo'],
                    'Matam': ['Matam Centre', 'Nongo', 'Kipé', 'Enco5'],
                    'Matoto': ['Matoto Centre', 'Bambeto', 'Sangoyah', 'Sonfonia'],
                    'Ratoma': ['Ratoma Centre', 'Koloma', 'Kaporo Rails', 'Wanindara']
                }
            },
            'Kindia': {
                'code': 'KND',
                'prefectures': {
                    'Kindia': ['Kindia Centre', 'Damakania', 'Linsan', 'Molota'],
                    'Coyah': ['Coyah Centre', 'Kouriah', 'Wonkifong', 'Manéah'],
                    'Dubréka': ['Dubréka Centre', 'Badi', 'Tanéné', 'Khorira'],
                    'Forécariah': ['Forécariah Centre', 'Benty', 'Kaback', 'Sikhourou'],
                    'Télimélé': ['Télimélé Centre', 'Gougoudjé', 'Konsankoro', 'Thionthian']
                }
            },
            'Boké': {
                'code': 'BOK',
                'prefectures': {
                    'Boké': ['Boké Centre', 'Dabiss', 'Kolaboui', 'Sangarédi'],
                    'Boffa': ['Boffa Centre', 'Douprou', 'Koba', 'Tamita'],
                    'Fria': ['Fria Centre', 'Banguingny', 'Tormelin'],
                    'Gaoual': ['Gaoual Centre', 'Foulamory', 'Malanta', 'Wendou M\'Bour'],
                    'Koundara': ['Koundara Centre', 'Guingan', 'Kamaby', 'Sambailo']
                }
            },
            'Labé': {
                'code': 'LAB',
                'prefectures': {
                    'Labé': ['Labé Centre', 'Diari', 'Garambé', 'Popodara'],
                    'Koubia': ['Koubia Centre', 'Fafaya', 'Gadha-Woundou', 'Pilimini'],
                    'Lélouma': ['Lélouma Centre', 'Diari-Maré', 'Lafou', 'Parawol'],
                    'Mali': ['Mali Centre', 'Balaki', 'Donghol-Touma', 'Yembering'],
                    'Tougué': ['Tougué Centre', 'Fatako', 'Kansangui', 'Kolangui']
                }
            },
            'Mamou': {
                'code': 'MAM',
                'prefectures': {
                    'Mamou': ['Mamou Centre', 'Dounet', 'Konkouré', 'Saramoussaya'],
                    'Dalaba': ['Dalaba Centre', 'Ditinn', 'Kaalan', 'Mitty'],
                    'Pita': ['Pita Centre', 'Dongol-Sigon', 'Ley-Miro', 'Timbo']
                }
            },
            'Faranah': {
                'code': 'FAR',
                'prefectures': {
                    'Faranah': ['Faranah Centre', 'Banian', 'Gnalén', 'Marela'],
                    'Dabola': ['Dabola Centre', 'Arfamoussaya', 'Bissikrima', 'Kindoye'],
                    'Dinguiraye': ['Dinguiraye Centre', 'Banora', 'Dialakoro', 'Kalinko'],
                    'Kissidougou': ['Kissidougou Centre', 'Bardou', 'Firawa', 'Yendé']
                }
            },
            'Kankan': {
                'code': 'KAN',
                'prefectures': {
                    'Kankan': ['Kankan Centre', 'Baté-Nafadji', 'Missamana', 'Morodou'],
                    'Kérouané': ['Kérouané Centre', 'Banankoro', 'Komodou', 'Sibiribaro'],
                    'Kouroussa': ['Kouroussa Centre', 'Babila', 'Douako', 'Kiniero'],
                    'Mandiana': ['Mandiana Centre', 'Dialakoro', 'Faralako', 'Kiniéran'],
                    'Siguiri': ['Siguiri Centre', 'Doko', 'Franwalia', 'Niagassola']
                }
            },
            'Nzérékoré': {
                'code': 'NZE',
                'prefectures': {
                    'Nzérékoré': ['Nzérékoré Centre', 'Gouécké', 'Palé', 'Womey'],
                    'Beyla': ['Beyla Centre', 'Diécké', 'Fouala', 'Sinko'],
                    'Guékédou': ['Guékédou Centre', 'Fangamadou', 'Kassadou', 'Tekoulo'],
                    'Lola': ['Lola Centre', 'Bossou', 'Gama', 'N\'Zoo'],
                    'Macenta': ['Macenta Centre', 'Balizia', 'Kouankan', 'Sérédou'],
                    'Yomou': ['Yomou Centre', 'Banié', 'Bowé', 'Djécké']
                }
            }
        }

        self.stdout.write('Création des données administratives de la Guinée...')

        for region_name, region_data in guinea_data.items():
            region, created = GuineaRegion.objects.get_or_create(
                name=region_name,
                defaults={'code': region_data['code']}
            )
            
            if created:
                self.stdout.write(f'Région créée: {region_name}')
            
            for prefecture_name, quartiers in region_data['prefectures'].items():
                prefecture, created = GuineaPrefecture.objects.get_or_create(
                    region=region,
                    name=prefecture_name,
                    defaults={'code': prefecture_name[:3].upper()}
                )
                
                if created:
                    self.stdout.write(f'  Préfecture créée: {prefecture_name}')
                
                for quartier_name in quartiers:
                    quartier, created = GuineaQuartier.objects.get_or_create(
                        prefecture=prefecture,
                        name=quartier_name
                    )
                    
                    if created:
                        self.stdout.write(f'    Quartier créé: {quartier_name}')

        self.stdout.write(
            self.style.SUCCESS('Données administratives de la Guinée créées avec succès!')
        )