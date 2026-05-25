from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from contributions.models import Category, Contribution, ContributionType, FeaturedContent
from projects.models import Project
from stewards.models import Steward
from users.models import User


class ProjectAPITest(TestCase):
    def setUp(self):
        Project.objects.all().delete()
        self.user = User.objects.create_user(
            email='builder@example.com',
            password='pass',
            address='0x0000000000000000000000000000000000000001',
            name='Project Builder',
        )
        self.category = Category.objects.create(name='Project Test Builder', slug='project-test-builder')
        self.contribution_type = ContributionType.objects.create(
            name='Project Submission',
            slug='project-submission-test',
            category=self.category,
            min_points=0,
            max_points=100,
        )

    def create_project(self, **overrides):
        defaults = {
            'title': 'Cognocracy',
            'description': 'A governance project built on GenLayer.',
            'author': 'Cognocracy Team',
            'user': self.user,
            'url': 'https://cognocracy.example.com',
            'github_url': '',
            'details': 'Longer project context.',
            'status': Project.STATUS_ACTIVE,
            'order': 10,
        }
        defaults.update(overrides)
        return Project.objects.create(**defaults)

    def create_contribution(self):
        contribution = Contribution(
            user=self.user,
            contribution_type=self.contribution_type,
            points=42,
            frozen_global_points=42,
            contribution_date=timezone.now() - timedelta(days=1),
            title='Built the project interface',
            notes='Accepted project work.',
        )
        Contribution.objects.bulk_create([contribution])
        return Contribution.objects.get(title='Built the project interface')

    def test_project_list_excludes_inactive_and_featured_content_builds(self):
        active = self.create_project(title='Active Project')
        self.create_project(title='Inactive Project', status=Project.STATUS_IDLE)
        FeaturedContent.objects.create(
            content_type='hero',
            title='Hero Content',
            user=self.user,
            status='active',
        )

        response = self.client.get('/api/v1/projects/')

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        slugs = {item['slug'] for item in payload}
        self.assertEqual(slugs, {active.slug})
        self.assertEqual(payload[0]['link'], f'/builders/projects/{active.slug}')

    def test_project_detail_includes_related_contributions(self):
        project = self.create_project(github_url='https://github.com/example/cognocracy')
        project.participants.add(self.user)
        contribution = self.create_contribution()
        project.related_contributions.add(contribution)

        response = self.client.get(f'/api/v1/projects/{project.slug}/')

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['slug'], project.slug)
        self.assertEqual(payload['github_url'], 'https://github.com/example/cognocracy')
        self.assertEqual(payload['participants'][0]['name'], 'Project Builder')
        self.assertEqual(len(payload['related_contributions']), 1)
        self.assertEqual(payload['related_contributions'][0]['title'], 'Built the project interface')

    def test_non_owner_cannot_update_project_profile(self):
        project = self.create_project()
        other_user = User.objects.create_user(
            email='other@example.com',
            password='pass',
            address='0x0000000000000000000000000000000000000002',
            name='Other Builder',
        )
        self.client.force_login(other_user)

        response = self.client.patch(
            f'/api/v1/projects/{project.slug}/profile/',
            data={'description': 'Nope'},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 403)

    def test_project_participant_can_update_project_profile(self):
        project = self.create_project()
        participant = User.objects.create_user(
            email='participant-editor@example.com',
            password='pass',
            address='0x0000000000000000000000000000000000000005',
            name='Participant Editor',
        )
        project.participants.add(participant)
        self.client.force_login(participant)

        response = self.client.patch(
            f'/api/v1/projects/{project.slug}/profile/',
            data={'description': 'Participant update.'},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        project.refresh_from_db()
        self.assertEqual(project.description, 'Participant update.')

    def test_staff_user_cannot_update_project_profile_without_project_access(self):
        project = self.create_project()
        staff_user = User.objects.create_user(
            email='staff@example.com',
            password='pass',
            address='0x0000000000000000000000000000000000000006',
            name='Staff User',
            is_staff=True,
        )
        self.client.force_login(staff_user)

        response = self.client.patch(
            f'/api/v1/projects/{project.slug}/profile/',
            data={'description': 'Staff update.'},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 403)

    def test_steward_cannot_update_project_profile_without_project_access(self):
        project = self.create_project()
        steward_user = User.objects.create_user(
            email='steward@example.com',
            password='pass',
            address='0x0000000000000000000000000000000000000007',
            name='Steward User',
        )
        Steward.objects.create(user=steward_user)
        self.client.force_login(steward_user)

        response = self.client.patch(
            f'/api/v1/projects/{project.slug}/profile/',
            data={'description': 'Steward update.'},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 403)

    def test_superuser_can_update_project_profile(self):
        project = self.create_project()
        superuser = User.objects.create_superuser(
            email='admin@example.com',
            password='pass',
            address='0x0000000000000000000000000000000000000008',
            name='Admin User',
        )
        self.client.force_login(superuser)

        response = self.client.patch(
            f'/api/v1/projects/{project.slug}/profile/',
            data={'description': 'Admin update.'},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        project.refresh_from_db()
        self.assertEqual(project.description, 'Admin update.')

    def test_project_owner_can_update_profile_fields_and_participants(self):
        project = self.create_project()
        participant = User.objects.create_user(
            email='participant@example.com',
            password='pass',
            address='0x0000000000000000000000000000000000000003',
            name='Participant Builder',
        )
        participant_contribution = Contribution(
            user=participant,
            contribution_type=self.contribution_type,
            points=28,
            frozen_global_points=28,
            contribution_date=timezone.now() - timedelta(days=2),
            title='Participant related work',
            notes='Accepted participant work.',
        )
        Contribution.objects.bulk_create([participant_contribution])
        participant_contribution = Contribution.objects.get(title='Participant related work')
        self.client.force_login(self.user)

        response = self.client.patch(
            f'/api/v1/projects/{project.slug}/profile/',
            data={
                'description': 'Updated short description.',
                'details': 'Updated about content.',
                'url': 'https://updated.example.com',
                'github_url': 'https://github.com/example/project',
                'x_url': 'https://x.com/example',
                'telegram_url': 'https://t.me/example',
                'discord_url': 'https://discord.gg/example',
                'demo_url': 'https://youtu.be/dQw4w9WgXcQ',
                'participant_ids': [self.user.id, participant.id],
                'related_contribution_ids': [participant_contribution.id],
            },
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        project.refresh_from_db()
        self.assertEqual(project.description, 'Updated short description.')
        self.assertEqual(project.details, 'Updated about content.')
        self.assertEqual(project.url, 'https://updated.example.com')
        self.assertEqual(project.x_url, 'https://x.com/example')
        self.assertEqual(project.demo_url, 'https://youtu.be/dQw4w9WgXcQ')
        self.assertEqual(project.participants.count(), 2)
        self.assertEqual(project.related_contributions.count(), 1)
        self.assertEqual(
            [participant['name'] for participant in response.json()['participants']],
            ['Project Builder', 'Participant Builder'],
        )
        self.assertEqual(response.json()['related_contributions'][0]['title'], 'Participant related work')

    def test_project_profile_rejects_related_contribution_outside_participants(self):
        project = self.create_project()
        other_user = User.objects.create_user(
            email='outside@example.com',
            password='pass',
            address='0x0000000000000000000000000000000000000004',
            name='Outside Builder',
        )
        outside_contribution = Contribution(
            user=other_user,
            contribution_type=self.contribution_type,
            points=12,
            frozen_global_points=12,
            contribution_date=timezone.now() - timedelta(days=2),
            title='Outside work',
            notes='Accepted outside work.',
        )
        Contribution.objects.bulk_create([outside_contribution])
        outside_contribution = Contribution.objects.get(title='Outside work')
        self.client.force_login(self.user)

        response = self.client.patch(
            f'/api/v1/projects/{project.slug}/profile/',
            data={
                'participant_ids': [self.user.id],
                'related_contribution_ids': [outside_contribution.id],
            },
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('related_contribution_ids', response.json())

    def test_project_detail_404s_for_inactive_project(self):
        project = self.create_project(status=Project.STATUS_IDLE)

        response = self.client.get(f'/api/v1/projects/{project.slug}/')

        self.assertEqual(response.status_code, 404)
