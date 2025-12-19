"""
Image caching service for storing CC-licensed images on Cloudflare R2.

This service downloads images from sources like Wikimedia Commons,
uploads them to R2, and returns CDN URLs for serving.
"""

import hashlib
import logging
import mimetypes
import uuid
from io import BytesIO
from typing import Optional, Tuple
from urllib.parse import urlparse

import requests
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.utils import timezone

logger = logging.getLogger(__name__)


class ImageCacheService:
    """
    Service for caching images from external sources to Cloudflare R2.

    Images are organized by entity type and stored with unique filenames
    to prevent collisions while maintaining a logical structure.
    """

    # Supported image formats
    ALLOWED_MIME_TYPES = {
        'image/jpeg': '.jpg',
        'image/png': '.png',
        'image/gif': '.gif',
        'image/webp': '.webp',
    }

    # Maximum image size (10MB)
    MAX_IMAGE_SIZE = 10 * 1024 * 1024

    # Request timeout
    REQUEST_TIMEOUT = 30

    # User agent for downloading
    USER_AGENT = "OWDBBot/1.0 (https://wrestlingdb.org/about/bot; contact@wrestlingdb.org)"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.USER_AGENT,
            'Accept': 'image/*',
        })

    def _generate_filename(self, entity_type: str, entity_id: int,
                          original_url: str, extension: str) -> str:
        """
        Generate a unique filename for the cached image.

        Format: {entity_type}/{entity_id}/{hash}_{timestamp}{extension}
        Example: wrestlers/123/a1b2c3d4_1703001234.jpg
        """
        # Create a hash of the original URL for uniqueness
        url_hash = hashlib.md5(original_url.encode()).hexdigest()[:8]
        timestamp = int(timezone.now().timestamp())

        return f"{entity_type}/{entity_id}/{url_hash}_{timestamp}{extension}"

    def _get_extension_from_url(self, url: str) -> str:
        """Extract file extension from URL."""
        parsed = urlparse(url)
        path = parsed.path.lower()

        for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
            if path.endswith(ext):
                return '.jpg' if ext == '.jpeg' else ext

        return '.jpg'  # Default to jpg

    def _get_extension_from_content_type(self, content_type: str) -> str:
        """Get file extension from content type."""
        if content_type:
            mime = content_type.split(';')[0].strip().lower()
            return self.ALLOWED_MIME_TYPES.get(mime, '.jpg')
        return '.jpg'

    def download_image(self, url: str) -> Optional[Tuple[bytes, str]]:
        """
        Download an image from a URL.

        Args:
            url: The image URL to download

        Returns:
            Tuple of (image_bytes, extension) or None if failed
        """
        try:
            response = self.session.get(
                url,
                timeout=self.REQUEST_TIMEOUT,
                stream=True
            )
            response.raise_for_status()

            # Check content type
            content_type = response.headers.get('Content-Type', '')
            if not content_type.startswith('image/'):
                logger.warning(f"Not an image: {url} (Content-Type: {content_type})")
                return None

            # Check size
            content_length = int(response.headers.get('Content-Length', 0))
            if content_length > self.MAX_IMAGE_SIZE:
                logger.warning(f"Image too large: {url} ({content_length} bytes)")
                return None

            # Download the image
            image_data = BytesIO()
            downloaded = 0
            for chunk in response.iter_content(chunk_size=8192):
                downloaded += len(chunk)
                if downloaded > self.MAX_IMAGE_SIZE:
                    logger.warning(f"Image exceeded size limit during download: {url}")
                    return None
                image_data.write(chunk)

            extension = self._get_extension_from_content_type(content_type)
            return image_data.getvalue(), extension

        except requests.RequestException as e:
            logger.error(f"Failed to download image {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error downloading image {url}: {e}")
            return None

    def upload_to_r2(self, image_data: bytes, path: str) -> Optional[str]:
        """
        Upload image data to R2 storage.

        Args:
            image_data: The image bytes
            path: The storage path (e.g., "wrestlers/123/abc123.jpg")

        Returns:
            The CDN URL of the uploaded image or None if failed
        """
        try:
            # Check if R2 is configured
            if not hasattr(settings, 'R2_ACCESS_KEY_ID') or not settings.R2_ACCESS_KEY_ID:
                logger.warning("R2 not configured, cannot upload image")
                return None

            # Upload to R2
            content_file = ContentFile(image_data)
            saved_path = default_storage.save(path, content_file)

            # Return the CDN URL
            url = default_storage.url(saved_path)
            logger.info(f"Uploaded image to R2: {url}")
            return url

        except Exception as e:
            logger.error(f"Failed to upload image to R2: {e}")
            return None

    def cache_image(self, source_url: str, entity_type: str,
                   entity_id: int) -> Optional[str]:
        """
        Download an image and cache it to R2.

        Args:
            source_url: The original image URL
            entity_type: Type of entity (e.g., "wrestlers", "promotions")
            entity_id: The entity's database ID

        Returns:
            The CDN URL of the cached image or None if failed
        """
        # Download the image
        result = self.download_image(source_url)
        if not result:
            return None

        image_data, extension = result

        # Generate storage path
        path = self._generate_filename(entity_type, entity_id, source_url, extension)

        # Upload to R2
        cdn_url = self.upload_to_r2(image_data, path)

        return cdn_url

    def cache_and_update_entity(self, entity, image_result: dict,
                                archive_old: bool = True) -> bool:
        """
        Cache an image for an entity and update its fields.

        Args:
            entity: The model instance (Wrestler, Promotion, etc.)
            image_result: Dict from WikimediaCommonsClient with image metadata
            archive_old: Whether to archive the old image to history

        Returns:
            True if successful, False otherwise
        """
        from ..models import ImageHistory

        source_url = image_result.get('thumb_url') or image_result.get('url')
        if not source_url:
            logger.warning(f"No image URL in result for {entity}")
            return False

        # Determine entity type for storage path
        entity_type = entity.__class__.__name__.lower() + 's'  # e.g., "wrestlers"

        # Archive old image if exists and requested
        if archive_old and entity.has_image():
            reason = 'better_image_found' if entity.needs_image_refresh() else 'scheduled_refresh'
            ImageHistory.archive_current_image(entity, reason=reason)

        # Cache to R2
        cdn_url = self.cache_image(source_url, entity_type, entity.pk)
        if not cdn_url:
            logger.warning(f"Failed to cache image for {entity}")
            return False

        # Update entity fields
        entity.image_url = cdn_url
        entity.image_original_url = source_url
        entity.image_source_url = image_result.get('description_url', '')
        entity.image_license = image_result.get('license', '')
        entity.image_credit = image_result.get('artist', '')
        entity.image_fetched_at = timezone.now()

        entity.save(update_fields=[
            'image_url', 'image_original_url', 'image_source_url',
            'image_license', 'image_credit', 'image_fetched_at'
        ])

        logger.info(f"Cached image for {entity}: {cdn_url}")
        return True

    def refresh_stale_images(self, entity_class, min_age_days: int = 30,
                            limit: int = 10) -> int:
        """
        Find and refresh images older than min_age_days.

        Args:
            entity_class: The model class (Wrestler, Promotion, etc.)
            min_age_days: Minimum age in days before refreshing
            limit: Maximum number of entities to process

        Returns:
            Number of images refreshed
        """
        from ..scrapers import WikimediaCommonsClient

        cutoff = timezone.now() - timezone.timedelta(days=min_age_days)

        # Find entities with old images
        entities = entity_class.objects.filter(
            image_url__isnull=False,
            image_fetched_at__lt=cutoff
        ).order_by('image_fetched_at')[:limit]

        client = WikimediaCommonsClient()
        refreshed = 0

        for entity in entities:
            try:
                # Find a new image
                result = self._find_image_for_entity(client, entity)
                if result:
                    # Check if it's actually a different/better image
                    new_url = result.get('url') or result.get('thumb_url')
                    if new_url and new_url != entity.image_original_url:
                        if self.cache_and_update_entity(entity, result, archive_old=True):
                            refreshed += 1
                            logger.info(f"Refreshed image for {entity}")
                    else:
                        # Same image, just update timestamp to prevent re-checking
                        entity.image_fetched_at = timezone.now()
                        entity.save(update_fields=['image_fetched_at'])
            except Exception as e:
                logger.error(f"Error refreshing image for {entity}: {e}")
                continue

        return refreshed

    def _find_image_for_entity(self, client, entity):
        """Find an image for an entity using the appropriate method."""
        entity_type = entity.__class__.__name__

        if entity_type == 'Wrestler':
            return client.find_wrestler_image(
                name=entity.name,
                real_name=getattr(entity, 'real_name', None)
            )
        elif entity_type == 'Promotion':
            return client.find_promotion_image(
                name=entity.name,
                abbreviation=getattr(entity, 'abbreviation', None)
            )
        elif entity_type == 'Venue':
            return client.find_venue_image(
                name=entity.name,
                location=getattr(entity, 'location', None)
            )
        elif entity_type == 'Event':
            return client.find_event_image(
                name=entity.name,
                promotion=entity.promotion.abbreviation if entity.promotion else None,
                year=entity.date.year if entity.date else None
            )
        elif entity_type == 'Title':
            return client.find_title_image(
                name=entity.name,
                promotion=entity.promotion.abbreviation if entity.promotion else None
            )
        else:
            logger.warning(f"Unknown entity type: {entity_type}")
            return None


# Singleton instance
_image_cache_service = None

def get_image_cache_service() -> ImageCacheService:
    """Get the singleton ImageCacheService instance."""
    global _image_cache_service
    if _image_cache_service is None:
        _image_cache_service = ImageCacheService()
    return _image_cache_service
