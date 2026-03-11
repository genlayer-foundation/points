import os
import shutil

from django.conf import settings
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from contributions.models import FeaturedContent

User = get_user_model()


class Command(BaseCommand):
    help = 'Seeds FeaturedContent entries for the portal home page (hero banner and featured builds).'

    def _copy_to_media(self, source_path, relative_dest):
        """
        Copy a file to MEDIA_ROOT if it doesn't already exist at the destination.
        Returns the relative path within MEDIA_ROOT, or None if the source doesn't exist.
        """
        if not os.path.exists(source_path):
            self.stdout.write(self.style.WARNING(f"    Image not found: {source_path}"))
            return None

        dest_path = os.path.join(settings.MEDIA_ROOT, relative_dest)
        dest_dir = os.path.dirname(dest_path)
        os.makedirs(dest_dir, exist_ok=True)

        if not os.path.exists(dest_path):
            shutil.copy2(source_path, dest_path)
            self.stdout.write(self.style.SUCCESS(f"    Copied: {relative_dest}"))
        else:
            self.stdout.write(f"    Already exists: {relative_dest}")

        return relative_dest

    def handle(self, *args, **options):
        media_root = settings.MEDIA_ROOT

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
        hero_defaults = {
            'description': 'Deploy intelligent contracts, run validators, and earn GenLayer Points on the latest testnet.',
            'author': 'cognocracy',
            'user': users['cognocracy'],
            'url': '',
            'is_active': True,
            'order': 0,
        }

        obj, created = FeaturedContent.objects.update_or_create(
            content_type='hero',
            title='Argue.fun Launch',
            defaults=hero_defaults,
        )

        # Copy hero image to media directory
        hero_source = os.path.join(media_root, 'featured', 'hero-bg.png')
        hero_rel = 'featured/hero-bg.png'
        result = self._copy_to_media(hero_source, hero_rel)
        if result:
            obj.hero_image = result
            obj.save()

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
                'hero_image_source': os.path.join(media_root, 'featured', 'argue-fun-bg.jpg'),
                'hero_image_rel': 'featured/argue-fun-bg.jpg',
                'avatar_source': os.path.join(media_root, 'featured', 'avatars', 'cognocracy-avatar.png'),
                'avatar_rel': 'featured/avatars/cognocracy-avatar.png',
                'url': '',
                'order': 0,
            },
            {
                'title': 'Internet Court',
                'user': users['raskovsky'],
                'hero_image_source': os.path.join(media_root, 'featured', 'internet-court-bg.jpg'),
                'hero_image_rel': 'featured/internet-court-bg.jpg',
                'avatar_source': os.path.join(media_root, 'featured', 'avatars', 'raskovsky-avatar.png'),
                'avatar_rel': 'featured/avatars/raskovsky-avatar.png',
                'url': '',
                'order': 1,
            },
            {
                'title': 'Rally',
                'user': users['GenLayer'],
                'hero_image_source': os.path.join(media_root, 'featured', 'rally-bg.jpg'),
                'hero_image_rel': 'featured/rally-bg.jpg',
                'avatar_source': os.path.join(media_root, 'featured', 'avatars', 'genlayer-avatar.png'),
                'avatar_rel': 'featured/avatars/genlayer-avatar.png',
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
                    'is_active': True,
                    'order': build['order'],
                    'description': '',
                    'author': '',
                },
            )

            updated = False

            # Copy hero image to media directory
            result = self._copy_to_media(build['hero_image_source'], build['hero_image_rel'])
            if result:
                obj.hero_image = result
                updated = True

            # Copy avatar to media directory
            result = self._copy_to_media(build['avatar_source'], build['avatar_rel'])
            if result:
                obj.user_profile_image = result
                updated = True

            if updated:
                obj.save()

            self.stdout.write(
                self.style.SUCCESS(f"  {'Created' if created else 'Updated'} build: {obj.title}")
            )

        self.stdout.write(self.style.SUCCESS('\nFeatured content seeded successfully.'))
