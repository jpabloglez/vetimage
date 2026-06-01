"""
DICOM Tag Editor Serializers
"""

import re

from rest_framework import serializers

TAG_HEX_RE = re.compile(r'^[0-9A-Fa-f]{8}$')

RESTRICTED_TAGS = frozenset({
    '7FE00010',  # PixelData
    '00020000', '00020001', '00020002', '00020003',
    '00020010', '00020012', '00020013',
})


class DicomTagQuerySerializer(serializers.Serializer):
    """Validates query params for tag listing."""
    search = serializers.CharField(required=False, allow_blank=True)


class TagUpdateItemSerializer(serializers.Serializer):
    """A single tag update entry."""
    tag = serializers.CharField()
    value = serializers.CharField(allow_blank=True)

    def validate_tag(self, value):
        tag_upper = value.upper()
        if not TAG_HEX_RE.match(tag_upper):
            raise serializers.ValidationError(
                f"'{value}' is not a valid 8-character hex DICOM tag."
            )
        if tag_upper in RESTRICTED_TAGS:
            raise serializers.ValidationError(
                f"Tag {tag_upper} is restricted and cannot be edited."
            )
        return tag_upper


class DicomTagUpdateSerializer(serializers.Serializer):
    """Validates input for updating DICOM tags."""
    tags = TagUpdateItemSerializer(many=True, min_length=1)
