from types import SimpleNamespace
from unittest.mock import patch

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, TestCase

from users.admin import UserAdmin
from utils.admin_widgets import CloudinaryUploadWidget


User = get_user_model()


class UserAdminCloudinaryUploadTest(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            email='admin-images@example.com',
            password='adminpass123',
        )
        self.user = User.objects.create_user(
            email='user-images@example.com',
            password='testpass123',
            name='Image User',
        )
        self.model_admin = UserAdmin(User, admin.site)
        self.request = RequestFactory().get('/admin/users/user/')
        self.request.user = self.admin_user

    def test_user_admin_uses_cloudinary_upload_widgets_for_images(self):
        form = self.model_admin.get_form(self.request, self.user)

        self.assertIsInstance(form.base_fields['profile_image_url'].widget, CloudinaryUploadWidget)
        self.assertIsInstance(form.base_fields['banner_image_url'].widget, CloudinaryUploadWidget)
        self.assertNotIn('profile_image_public_id', form.base_fields)
        self.assertNotIn('banner_image_public_id', form.base_fields)

    @patch('utils.admin_mixins.CloudinaryService.upload_image')
    def test_user_admin_uploads_profile_image_to_cloudinary(self, upload_image):
        upload_image.return_value = {
            'url': 'https://res.cloudinary.com/example/profile.png',
            'public_id': 'tally/profiles/uploaded-profile',
        }
        uploaded_file = SimpleUploadedFile(
            'profile.png',
            b'fake image bytes',
            content_type='image/png',
        )
        request = SimpleNamespace(
            FILES={'profile_image_url_upload': uploaded_file},
            POST={},
        )

        self.model_admin.save_model(request, self.user, form=None, change=True)

        self.user.refresh_from_db()
        self.assertEqual(self.user.profile_image_url, 'https://res.cloudinary.com/example/profile.png')
        self.assertEqual(self.user.profile_image_public_id, 'tally/profiles/uploaded-profile')
        upload_image.assert_called_once_with(uploaded_file, folder='tally/profiles')
