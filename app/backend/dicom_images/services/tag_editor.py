"""
DICOM Tag Editor Service

Provides read/update operations on DICOM tags stored in MedicalImage.
"""

import logging
import re

import pydicom

from dicom_images.models import MedicalImage
from dicom_images.utils import extract_all_dicom_tags

logger = logging.getLogger(__name__)

# Tags that must never be edited
RESTRICTED_TAGS = frozenset({
    '7FE00010',  # PixelData
    '00020000',  # FileMetaInformationGroupLength
    '00020001',  # FileMetaInformationVersion
    '00020002',  # MediaStorageSOPClassUID
    '00020003',  # MediaStorageSOPInstanceUID
    '00020010',  # TransferSyntaxUID
    '00020012',  # ImplementationClassUID
    '00020013',  # ImplementationVersionName
})

TAG_HEX_RE = re.compile(r'^[0-9A-Fa-f]{8}$')


class DicomTagEditorService:
    """Read and update DICOM tags on MedicalImage instances."""

    def get_tags(self, image_id, user, search=None):
        """
        Return the dicom_tags JSONField content for *image_id*.

        If *search* is provided, filter tags whose name or tag key
        contains the search string (case-insensitive).
        """
        image = MedicalImage.objects.select_related(
            'series__study'
        ).get(id=image_id, series__study__uploaded_by=user)

        tags = image.dicom_tags or {}

        if search:
            search_lower = search.lower()
            tags = {
                k: v for k, v in tags.items()
                if search_lower in k.lower()
                or search_lower in v.get('name', '').lower()
                or search_lower in str(v.get('value', '')).lower()
            }

        return tags

    def update_tags(self, image_id, tag_updates, user):
        """
        Modify DICOM tags on disk and refresh the JSONField.

        *tag_updates* is a list of dicts: [{"tag": "00100020", "value": "NEW"}]

        Returns the refreshed tags dict.
        """
        image = MedicalImage.objects.select_related(
            'series__study'
        ).get(id=image_id, series__study__uploaded_by=user)

        # Validate all updates first
        for update in tag_updates:
            tag_key = update['tag'].upper()
            if tag_key in RESTRICTED_TAGS:
                raise ValueError(
                    f"Tag {tag_key} is restricted and cannot be edited."
                )
            if not TAG_HEX_RE.match(tag_key):
                raise ValueError(
                    f"Tag '{update['tag']}' is not a valid 8-character hex string."
                )

        # Read the DICOM file
        dcm = pydicom.dcmread(image.file.path)

        for update in tag_updates:
            tag_key = update['tag'].upper()
            group = int(tag_key[:4], 16)
            element = int(tag_key[4:], 16)
            tag = pydicom.tag.Tag(group, element)

            if tag in dcm:
                dcm[tag].value = update['value']
            else:
                # Attempt to add the tag — requires VR lookup
                try:
                    from pydicom.datadict import keyword_for_tag, dictionary_VR
                    vr = dictionary_VR(tag)
                    dcm.add_new(tag, vr, update['value'])
                except Exception:
                    raise ValueError(
                        f"Cannot add unknown tag {tag_key}. "
                        "Tag must already exist in the DICOM file or be in the DICOM dictionary."
                    )

        # Save modified file
        dcm.save_as(image.file.path)

        # Refresh stored tags
        refreshed_tags = extract_all_dicom_tags(dcm)
        image.dicom_tags = refreshed_tags
        image.save(update_fields=['dicom_tags'])

        return refreshed_tags
