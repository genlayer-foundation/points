from django.contrib import admin, messages

from users.cloudinary_service import CloudinaryService
from utils.admin_widgets import CloudinaryUploadWidget

from tally.middleware.logging_utils import get_app_logger

logger = get_app_logger('admin')


class CloudinaryUploadMixin:
    """
    Admin mixin that enables direct Cloudinary uploads from the Django admin.

    Configure via `cloudinary_upload_fields` on the ModelAdmin:

        cloudinary_upload_fields = {
            'image_url': {
                'public_id_field': 'image_public_id',
                'folder': 'tally/images',
            },
        }

    Each key is a URL field on the model. The mixin will:
      - Inject a file upload input next to each URL field
      - On save, upload the file to Cloudinary and populate the URL + public_id
      - Optionally delete the old image when replaced
      - Support clearing the image via a checkbox
    """

    cloudinary_upload_fields = {}

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        for url_field in self.cloudinary_upload_fields:
            if url_field in form.base_fields:
                form.base_fields[url_field].widget = CloudinaryUploadWidget(
                    url_field_name=url_field,
                )
                form.base_fields[url_field].required = False
        return form

    def _get_writable_readonly_fields(self, request, obj=None):
        """Return public_id fields that we manage but shouldn't be truly readonly during save."""
        fields = set()
        for config in self.cloudinary_upload_fields.values():
            pid_field = config.get('public_id_field')
            if pid_field:
                fields.add(pid_field)
        return fields

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        managed_fields = self._get_writable_readonly_fields(request, obj)
        return [f for f in readonly if f not in managed_fields]

    def get_exclude(self, request, obj=None):
        exclude = list(super().get_exclude(request, obj) or [])
        for config in self.cloudinary_upload_fields.values():
            pid_field = config.get('public_id_field')
            if pid_field and pid_field not in exclude:
                exclude.append(pid_field)
        return exclude

    def save_model(self, request, obj, form, change):
        for url_field, config in self.cloudinary_upload_fields.items():
            pid_field = config.get('public_id_field', '')
            folder = config.get('folder', 'tally/uploads')

            file_input_name = f'{url_field}_upload'
            clear_input_name = f'{url_field}_clear'

            uploaded_file = request.FILES.get(file_input_name)
            should_clear = request.POST.get(clear_input_name)

            if should_clear and not uploaded_file:
                old_pid = getattr(obj, pid_field, '') if pid_field else ''
                if old_pid:
                    CloudinaryService.delete_image(old_pid)
                setattr(obj, url_field, '')
                if pid_field:
                    setattr(obj, pid_field, '')
                continue

            if uploaded_file:
                old_pid = getattr(obj, pid_field, '') if pid_field else ''
                try:
                    result = CloudinaryService.upload_image(
                        uploaded_file, folder=folder,
                    )
                    setattr(obj, url_field, result['url'])
                    if pid_field:
                        setattr(obj, pid_field, result['public_id'])

                    if old_pid:
                        CloudinaryService.delete_image(old_pid)
                except Exception as e:
                    logger.error(f"Cloudinary upload failed for {url_field}: {e}")
                    messages.error(request, f"Image upload failed for {url_field}: {e}")

        super().save_model(request, obj, form, change)
