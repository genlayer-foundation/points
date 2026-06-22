from types import SimpleNamespace
from unittest.mock import patch

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, TestCase

from utils.admin_widgets import CloudinaryUploadWidget
from validators.admin import ValidatorWalletAdmin
from validators.models import Validator, ValidatorWallet


User = get_user_model()


class ValidatorWalletAdminCloudinaryUploadTest(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            email='validator-admin-images@example.com',
            password='adminpass123',
        )
        user = User.objects.create_user(
            email='validator-images@example.com',
            password='testpass123',
        )
        validator = Validator.objects.create(user=user)
        self.wallet = ValidatorWallet.objects.create(
            address='0x0000000000000000000000000000000000000001',
            operator=validator,
            operator_address='0x0000000000000000000000000000000000000001',
            network='asimov',
            status='active',
        )
        self.model_admin = ValidatorWalletAdmin(ValidatorWallet, admin.site)
        self.request = RequestFactory().get('/admin/validators/validatorwallet/')
        self.request.user = self.admin_user

    def test_validator_wallet_admin_uses_cloudinary_upload_widget_for_logo(self):
        form = self.model_admin.get_form(self.request, self.wallet)

        self.assertIsInstance(form.base_fields['logo_uri'].widget, CloudinaryUploadWidget)

    @patch('utils.admin_mixins.CloudinaryService.upload_image')
    def test_validator_wallet_admin_uploads_logo_to_cloudinary(self, upload_image):
        upload_image.return_value = {
            'url': 'https://res.cloudinary.com/example/validator.png',
            'public_id': 'tally/validators/uploaded-validator',
        }
        uploaded_file = SimpleUploadedFile(
            'validator.png',
            b'fake image bytes',
            content_type='image/png',
        )
        request = SimpleNamespace(
            FILES={'logo_uri_upload': uploaded_file},
            POST={},
        )

        self.model_admin.save_model(request, self.wallet, form=None, change=True)

        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.logo_uri, 'https://res.cloudinary.com/example/validator.png')
        upload_image.assert_called_once_with(uploaded_file, folder='tally/validators')
