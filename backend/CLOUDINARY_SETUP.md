# Cloudinary Setup Guide

This guide explains how to set up Cloudinary for image uploads in the Tally application.

## Prerequisites

1. Create a free Cloudinary account at https://cloudinary.com
2. Get your credentials from the Cloudinary Dashboard

## Configuration Steps

### 1. Create an Upload Preset

The application requires an **unsigned upload preset** named `tally_unsigned`. You can create this either through the Cloudinary dashboard or via API.

#### Option A: Via Cloudinary Dashboard
1. Log in to your Cloudinary account
2. Go to Settings > Upload
3. Click "Add upload preset"
4. Set the following:
   - Preset name: `tally_unsigned`
   - Signing Mode: **Unsigned**
   - Folder: `tally` (optional)
5. Save the preset

#### Option B: Via API (Python script)
```python
import requests

cloud_name = "your_cloud_name"
api_key = "your_api_key"
api_secret = "your_api_secret"

url = f'https://api.cloudinary.com/v1_1/{cloud_name}/upload_presets'
auth = (api_key, api_secret)

data = {
    'name': 'tally_unsigned',
    'unsigned': True,
    'folder': 'tally'
}

response = requests.post(url, json=data, auth=auth)
print(response.json())
```

### 2. Environment Variables

Add these variables to your `.env` file:

```env
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret
CLOUDINARY_UPLOAD_PRESET=tally_unsigned
```

### 3. For AWS Deployment

Add these parameters to AWS Systems Manager Parameter Store:

```bash
/tally/prod/cloudinary_cloud_name
/tally/prod/cloudinary_api_key
/tally/prod/cloudinary_api_secret
```

The deployment script (`deploy-apprunner.sh`) is already configured to inject these as environment variables.

## How It Works

1. **Profile Images**: Uploaded to `tally/profiles/` folder, automatically resized to 400x400px
2. **Banner Images**: Uploaded to `tally/banners/` folder, automatically resized to 1500x500px
3. **Transformations**: Applied via URL parameters for optimal performance
4. **Naming Convention**: `user_{id}_{type}_{timestamp}` to ensure uniqueness

## Image Specifications

- **Profile Image**: 400x400px, face-focused cropping
- **Banner Image**: 1500x500px, center-focused cropping
- **Supported Formats**: JPEG, PNG, WebP
- **Max File Size**: 10MB
- **Quality**: Auto-optimized for best quality/size ratio

## Troubleshooting

### "Upload preset not found" Error
- Ensure the `tally_unsigned` preset exists in your Cloudinary account
- Verify the preset is set to "Unsigned" mode
- Check that your Cloudinary credentials are correct

### Images Not Displaying
- Verify the Cloudinary cloud name is correct
- Check browser console for CORS errors
- Ensure the transformation parameters in URLs are valid

### Deployment Issues
- Verify SSM parameters are set correctly in AWS
- Check App Runner logs for environment variable issues
- Ensure the IAM role has permission to read SSM parameters

## Security Notes

- The upload preset is **unsigned** to allow frontend uploads
- API credentials are only used for server-side operations (deletion)
- Each upload uses a unique timestamp to prevent overwrites
- Old images should be deleted when uploading new ones to save storage