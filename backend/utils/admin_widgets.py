from django import forms
from django.template.loader import render_to_string


class CloudinaryUploadWidget(forms.Widget):
    """
    A composite widget that renders a file upload input, a URL text input,
    an image preview, and a clear checkbox for Cloudinary image fields.
    """
    template_name = 'admin/widgets/cloudinary_upload.html'
    needs_multipart_form = True

    def __init__(self, url_field_name='', attrs=None):
        self.url_field_name = url_field_name
        super().__init__(attrs=attrs)

    def render(self, name, value, attrs=None, renderer=None):
        context = {
            'file_field_name': f'{name}_upload',
            'url_field_name': name,
            'clear_field_name': f'{name}_clear',
            'current_url': value or '',
            'url_input_type': 'url',
        }
        return render_to_string(self.template_name, context)

    def value_from_datadict(self, data, files, name):
        return data.get(name, '')
