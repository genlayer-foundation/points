from django.contrib import admin
from django.contrib.admin.utils import flatten_fieldsets
from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from utils.admin_widgets import CloudinaryUploadWidget


class CloudinaryUploadAdminCoverageTest(TestCase):
    def test_registered_cloudinary_admin_fields_render_upload_widget(self):
        user = get_user_model()(email='admin@example.com', is_staff=True, is_superuser=True)
        request = RequestFactory().get('/admin/')
        request.user = user
        failures = []
        checked = []

        for model, model_admin in admin.site._registry.items():
            upload_fields = getattr(model_admin, 'cloudinary_upload_fields', {})
            if not upload_fields:
                continue

            obj = model()
            form = model_admin.get_form(
                request,
                obj,
                fields=flatten_fieldsets(model_admin.get_fieldsets(request, obj)),
            )

            for field_name in upload_fields:
                checked.append(f'{model._meta.label}.{field_name}')
                field = form.base_fields.get(field_name)
                if not field or not isinstance(field.widget, CloudinaryUploadWidget):
                    widget_name = type(field.widget).__name__ if field else None
                    failures.append(f'{model._meta.label}.{field_name}: {widget_name}')

        self.assertTrue(checked)
        self.assertEqual(failures, [])
