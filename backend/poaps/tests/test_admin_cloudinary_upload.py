from types import SimpleNamespace
from unittest.mock import patch

from django.contrib import admin
from django.contrib.admin.utils import flatten_fieldsets
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, TestCase
from django.utils import timezone

from poaps.admin import PoapDropAdmin
from poaps.models import PoapDrop
from utils.admin_widgets import CloudinaryUploadWidget


User = get_user_model()


class PoapDropAdminCloudinaryUploadTest(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            email='poap-admin-images@example.com',
            password='adminpass123',
        )
        self.drop = PoapDrop.objects.create(
            title='Cloudinary POAP',
            description='A POAP with uploaded artwork.',
            event_start_at=timezone.now(),
            created_by=self.admin_user,
        )
        self.model_admin = PoapDropAdmin(PoapDrop, admin.site)
        self.request = RequestFactory().get('/admin/poaps/poapdrop/')
        self.request.user = self.admin_user
        self.client.force_login(self.admin_user)

    def test_poap_admin_uses_cloudinary_upload_widget_for_artwork(self):
        form = self.model_admin.get_form(
            self.request,
            self.drop,
            fields=flatten_fieldsets(self.model_admin.get_fieldsets(self.request, self.drop)),
        )

        self.assertIsInstance(form.base_fields['artwork_url'].widget, CloudinaryUploadWidget)
        self.assertNotIn('artwork_public_id', form.base_fields)

    def test_poap_admin_change_page_renders_artwork_upload_input(self):
        response = self.client.get(f'/admin/poaps/poapdrop/{self.drop.pk}/change/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'cloudinary-upload-widget')
        self.assertContains(response, 'name="artwork_url_upload"')

    @patch('utils.admin_mixins.CloudinaryService.upload_image')
    def test_poap_admin_uploads_artwork_to_cloudinary(self, upload_image):
        upload_image.return_value = {
            'url': 'https://res.cloudinary.com/example/poap.png',
            'public_id': 'tally/poaps/uploaded-poap',
        }
        uploaded_file = SimpleUploadedFile(
            'poap.png',
            b'fake image bytes',
            content_type='image/png',
        )
        request = SimpleNamespace(
            FILES={'artwork_url_upload': uploaded_file},
            POST={},
        )
        form = SimpleNamespace(cleaned_data={})

        self.model_admin.save_model(request, self.drop, form=form, change=True)

        self.drop.refresh_from_db()
        self.assertEqual(self.drop.artwork_url, 'https://res.cloudinary.com/example/poap.png')
        self.assertEqual(self.drop.artwork_public_id, 'tally/poaps/uploaded-poap')
        upload_image.assert_called_once_with(uploaded_file, folder='tally/poaps')
