from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from contributions.models import FeaturedContent

User = get_user_model()


class Command(BaseCommand):
    help = 'Seeds FeaturedContent entries for the portal home page (hero banner and featured builds).'

    def handle(self, *args, **options):
        # ----------------------------------------------------------------
        # 1.  Ensure users exist (get_or_create with dummy email/address)
        # ----------------------------------------------------------------
        users = {}
        user_specs = [
            {
                'name': 'cognocracy',
                'email': 'cognocracy@seed.genlayer.com',
                'address': '0x0000000000000000000000000000000000000001',
            },
            {
                'name': 'raskovsky',
                'email': 'raskovsky@seed.genlayer.com',
                'address': '0x0000000000000000000000000000000000000002',
            },
            {
                'name': 'GenLayer',
                'email': 'genlayer@seed.genlayer.com',
                'address': '0x0000000000000000000000000000000000000003',
            },
        ]

        for spec in user_specs:
            user, created = User.objects.get_or_create(
                email=spec['email'],
                defaults={
                    'name': spec['name'],
                    'address': spec['address'],
                    'username': spec['name'],
                },
            )
            users[spec['name']] = user
            if created:
                self.stdout.write(self.style.SUCCESS(f"  Created user: {spec['name']}"))
            else:
                self.stdout.write(f"  User already exists: {spec['name']}")

        # ----------------------------------------------------------------
        # 2.  Hero banner
        # ----------------------------------------------------------------
        obj, created = FeaturedContent.objects.update_or_create(
            content_type='hero',
            title='Argue.fun Launch',
            defaults={
                'description': 'Deploy intelligent contracts, run validators, and earn GenLayer Points on the latest testnet.',
                'author': 'cognocracy',
                'user': users['cognocracy'],
                'url': '',
                'status': 'active',
                'order': 0,
            },
        )

        self.stdout.write(
            self.style.SUCCESS(f"  {'Created' if created else 'Updated'} hero: {obj.title}")
        )

        # ----------------------------------------------------------------
        # 3.  Featured builds
        # ----------------------------------------------------------------
        builds = [
            {
                'title': 'Argue.fun',
                'user': users['cognocracy'],
                'url': '',
                'order': 0,
            },
            {
                'title': 'Internet Court',
                'user': users['raskovsky'],
                'url': '',
                'order': 1,
            },
            {
                'title': 'Rally',
                'user': users['GenLayer'],
                'url': '',
                'order': 2,
            },
        ]

        for build in builds:
            obj, created = FeaturedContent.objects.update_or_create(
                content_type='build',
                title=build['title'],
                defaults={
                    'user': build['user'],
                    'url': build['url'],
                    'status': 'active',
                    'order': build['order'],
                    'description': '',
                    'author': '',
                },
            )

            self.stdout.write(
                self.style.SUCCESS(f"  {'Created' if created else 'Updated'} build: {obj.title}")
            )

        self.stdout.write(self.style.SUCCESS('\nFeatured content seeded successfully.'))
        self.stdout.write('Note: Upload images via Django admin or set hero_image_url / user_profile_image_url directly.')
