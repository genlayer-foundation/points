import cloudinary
import cloudinary.uploader
from django.conf import settings
from typing import Optional, Dict
import time

from tally.middleware.logging_utils import get_app_logger

logger = get_app_logger('cloudinary')


class CloudinaryService:
    """Service for handling Cloudinary image uploads and transformations"""
    
    # Image specifications
    PROFILE_IMAGE_SPEC = {
        'width': 400,
        'height': 400,
        'crop': 'fill',
        'gravity': 'face',
        'quality': 'auto:good',
        'format': 'auto'
    }
    
    BANNER_IMAGE_SPEC = {
        'width': 1500,
        'height': 500,
        'crop': 'fill',
        'gravity': 'center',
        'quality': 'auto:good',
        'format': 'auto'
    }
    
    @classmethod
    def configure(cls):
        """Configure Cloudinary with settings"""
        cloudinary.config(
            cloud_name=settings.CLOUDINARY_CLOUD_NAME,
            api_key=settings.CLOUDINARY_API_KEY,
            api_secret=settings.CLOUDINARY_API_SECRET,
            secure=True
        )
    
    @classmethod
    def upload_profile_image(cls, image_file, user_id: int) -> Dict:
        """
        Upload and transform profile image
        
        Args:
            image_file: The image file to upload
            user_id: The user's ID for unique naming
            
        Returns:
            Dict with 'url' and 'public_id'
        """
        try:
            cls.configure()
            
            # Delete old image if exists (get current user's profile image public_id if needed)
            # This would need to be passed in or retrieved from the database
            
            # Use unsigned upload with preset (no transformations during upload)
            upload_preset = getattr(settings, 'CLOUDINARY_UPLOAD_PRESET', 'tally_unsigned')
            timestamp = int(time.time())
            
            result = cloudinary.uploader.unsigned_upload(
                image_file,
                upload_preset,
                public_id=f"user_{user_id}_profile_{timestamp}",
                folder="tally/profiles"
            )
            
            # Build URL with transformations
            transformation_str = "w_400,h_400,c_fill,g_face,q_auto:good,f_auto"
            base_url = result['secure_url']
            
            # Insert transformation into URL
            if '/upload/' in base_url:
                parts = base_url.split('/upload/')
                transformed_url = f"{parts[0]}/upload/{transformation_str}/{parts[1]}"
            else:
                transformed_url = base_url
            
            return {
                'url': transformed_url,
                'public_id': result['public_id']
            }
            
        except Exception as e:
            logger.error(f"Failed to upload profile image: {str(e)}")
            if "Upload preset not found" in str(e):
                raise Exception(
                    "Cloudinary upload preset not configured. Please create an unsigned upload preset "
                    "named 'tally_unsigned' in your Cloudinary dashboard (Settings > Upload > Upload presets)."
                )
            raise
    
    @classmethod
    def upload_banner_image(cls, image_file, user_id: int) -> Dict:
        """
        Upload and transform banner image
        
        Args:
            image_file: The image file to upload
            user_id: The user's ID for unique naming
            
        Returns:
            Dict with 'url' and 'public_id'
        """
        try:
            cls.configure()
            
            # Use unsigned upload with preset (no transformations during upload)
            upload_preset = getattr(settings, 'CLOUDINARY_UPLOAD_PRESET', 'tally_unsigned')
            timestamp = int(time.time())
            
            result = cloudinary.uploader.unsigned_upload(
                image_file,
                upload_preset,
                public_id=f"user_{user_id}_banner_{timestamp}",
                folder="tally/banners"
            )
            
            # Build URL with transformations
            transformation_str = "w_1500,h_500,c_fill,g_center,q_auto:good,f_auto"
            base_url = result['secure_url']
            
            # Insert transformation into URL
            if '/upload/' in base_url:
                parts = base_url.split('/upload/')
                transformed_url = f"{parts[0]}/upload/{transformation_str}/{parts[1]}"
            else:
                transformed_url = base_url
            
            return {
                'url': transformed_url,
                'public_id': result['public_id']
            }
            
        except Exception as e:
            logger.error(f"Failed to upload banner image: {str(e)}")
            if "Upload preset not found" in str(e):
                raise Exception(
                    "Cloudinary upload preset not configured. Please create an unsigned upload preset "
                    "named 'tally_unsigned' in your Cloudinary dashboard (Settings > Upload > Upload presets)."
                )
            raise
    
    @classmethod
    def delete_image(cls, public_id: str) -> bool:
        """
        Delete an image from Cloudinary
        
        Args:
            public_id: The public ID of the image to delete
            
        Returns:
            True if deletion was successful
        """
        if not public_id:
            return True
            
        try:
            cls.configure()
            result = cloudinary.uploader.destroy(public_id)
            return result.get('result') == 'ok'
        except Exception as e:
            logger.error(f"Failed to delete image: {str(e)}")
            return False
    
    @classmethod
    def get_upload_preset(cls, image_type: str) -> Dict:
        """
        Get upload configuration for direct browser uploads
        
        Args:
            image_type: 'profile' or 'banner'
            
        Returns:
            Configuration dict for frontend upload
        """
        cls.configure()
        
        if image_type == 'profile':
            transformation = cls.PROFILE_IMAGE_SPEC
            folder = "tally/profiles"
        elif image_type == 'banner':
            transformation = cls.BANNER_IMAGE_SPEC
            folder = "tally/banners"
        else:
            raise ValueError(f"Invalid image type: {image_type}")
        
        return {
            'cloud_name': settings.CLOUDINARY_CLOUD_NAME,
            'upload_preset': settings.CLOUDINARY_UPLOAD_PRESET,  # Unsigned preset for browser uploads
            'folder': folder,
            'transformation': transformation,
            'multiple': False,
            'max_file_size': 10485760,  # 10MB
            'allowed_formats': ['jpg', 'jpeg', 'png', 'webp']
        }