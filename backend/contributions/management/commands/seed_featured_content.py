import os

from django.conf import settings
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from contributions.models import FeaturedContent
from users.cloudinary_service import CloudinaryService

User = get_user_model()


class Command(BaseCommand):
    help = 'Seeds FeaturedContent entries for the portal home page (hero banner and featured builds).'

    def _upload_to_cloudinary(self, image_path, featured_obj, upload_type='hero'):
        """
        Upload a local image file to Cloudinary and return the result dict.
        Returns None if the file does not exist.

        Args:
            image_path: Absolute path to the local image file
            featured_obj: FeaturedContent instance (used for naming)
            upload_type: 'hero' or 'avatar'
        """
        if not os.path.exists(image_path):
            self.stdout.write(self.style.WARNING(f"    Image not found: {image_path}"))
            return None

        try:
            with open(image_path, 'rb') as f:
                if upload_type == 'hero':
                    result = CloudinaryService.upload_featured_image(f, featured_obj.pk)
                else:
                    result = CloudinaryService.upload_featured_avatar(f, featured_obj.pk)
            self.stdout.write(self.style.SUCCESS(f"    Uploaded {upload_type}: {result['url'][:80]}..."))
            return result
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"    Cloudinary upload failed for {upload_type}: {e}"))
            return None

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
            'subtitle': 'cognocracy',
            'user': users['cognocracy'],
            'hero_image_url': '',
            'url': '',
            'is_active': True,
            'order': 0,
        }

        obj, created = FeaturedContent.objects.update_or_create(
            content_type='hero',
            title='Argue.fun Launch',
            defaults=hero_defaults,
        )

        # Upload hero image to Cloudinary
        hero_image_path = os.path.join(media_root, 'featured', 'hero-bg.png')
        result = self._upload_to_cloudinary(hero_image_path, obj, 'hero')
        if result:
            obj.hero_image_url = result['url']
            obj.hero_image_public_id = result['public_id']
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
                'hero_image_file': os.path.join(media_root, 'featured', 'argue-fun-bg.jpg'),
                'avatar_file': os.path.join(media_root, 'featured', 'avatars', 'cognocracy-avatar.png'),
                'url': '',
                'order': 0,
            },
            {
                'title': 'Internet Court',
                'user': users['raskovsky'],
                'hero_image_file': os.path.join(media_root, 'featured', 'internet-court-bg.jpg'),
                'avatar_file': os.path.join(media_root, 'featured', 'avatars', 'raskovsky-avatar.png'),
                'url': '',
                'order': 1,
            },
            {
                'title': 'Rally',
                'user': users['GenLayer'],
                'hero_image_file': os.path.join(media_root, 'featured', 'rally-bg.jpg'),
                'avatar_file': os.path.join(media_root, 'featured', 'avatars', 'genlayer-avatar.png'),
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
                    'hero_image_url': '',
                    'url': build['url'],
                    'is_active': True,
                    'order': build['order'],
                    'description': '',
                    'subtitle': '',
                },
            )

            # Upload hero image to Cloudinary
            updated = False
            result = self._upload_to_cloudinary(build['hero_image_file'], obj, 'hero')
            if result:
                obj.hero_image_url = result['url']
                obj.hero_image_public_id = result['public_id']
                updated = True

            # Upload avatar to Cloudinary
            result = self._upload_to_cloudinary(build['avatar_file'], obj, 'avatar')
            if result:
                obj.user_profile_image_url = result['url']
                obj.user_profile_image_public_id = result['public_id']
                updated = True

            if updated:
                obj.save()

            self.stdout.write(
                self.style.SUCCESS(f"  {'Created' if created else 'Updated'} build: {obj.title}")
            )

        self.stdout.write(self.style.SUCCESS('\nFeatured content seeded successfully.'))
