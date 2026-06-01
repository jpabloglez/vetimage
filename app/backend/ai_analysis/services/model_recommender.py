"""
AI Model Recommendation Service

Intelligently matches uploaded medical images with compatible AI models
based on modality, dimensions, anatomical region, and other characteristics.
"""

from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class ModelRecommender:
    """
    Service for recommending compatible AI models based on image metadata.

    Scoring Algorithm:
    - Modality Match: 50 points (exact) or 25 points (partial)
    - Dimension Compatibility: 30 points (perfect) or 10 points (possible)
    - Anatomical Region Match: 20 points (exact) or 10 points (compatible)

    Total possible score: 100 points
    """

    # Modality compatibility mapping (partial matches)
    MODALITY_COMPAT = {
        'MR': ['MRI', 'T1', 'T2', 'FLAIR'],
        'CT': ['CTX', 'COMPUTED TOMOGRAPHY'],
        'OCT': ['OPTICAL COHERENCE TOMOGRAPHY'],
        'SLO': ['SCANNING LASER OPHTHALMOSCOPY'],
        'CR': ['X-RAY', 'RADIOGRAPHY'],
        'DX': ['DIGITAL X-RAY'],
    }

    # Anatomical region compatibility (related regions)
    REGION_COMPAT = {
        'brain': ['head', 'skull', 'cerebrum', 'cerebellum'],
        'chest': ['lung', 'thorax', 'heart', 'mediastinum'],
        'abdomen': ['liver', 'kidney', 'spleen', 'stomach'],
        'eye': ['retina', 'macula', 'optic nerve'],
    }

    @classmethod
    def _is_partial_modality_match(cls, metadata_modality: str, model_modality: str) -> bool:
        """
        Check if there's a partial match between modalities.

        Args:
            metadata_modality: Modality from image metadata
            model_modality: Supported modality from AI model

        Returns:
            True if there's a compatibility match
        """
        meta_mod_upper = metadata_modality.upper()
        model_mod_upper = model_modality.upper()

        # Check direct substring match
        if meta_mod_upper in model_mod_upper or model_mod_upper in meta_mod_upper:
            return True

        # Check compatibility mapping
        for key, aliases in cls.MODALITY_COMPAT.items():
            if meta_mod_upper == key or meta_mod_upper in aliases:
                if model_mod_upper == key or model_mod_upper in aliases:
                    return True

        return False

    @classmethod
    def _is_region_compatible(cls, metadata_region: Optional[str], model_region: str) -> bool:
        """
        Check if anatomical regions are compatible.

        Args:
            metadata_region: Region from image metadata (can be None)
            model_region: Supported region from AI model

        Returns:
            True if regions are compatible
        """
        if not metadata_region:
            return False

        meta_region_lower = metadata_region.lower()
        model_region_lower = model_region.lower()

        # Direct match
        if meta_region_lower == model_region_lower:
            return True

        # Substring match
        if meta_region_lower in model_region_lower or model_region_lower in meta_region_lower:
            return True

        # Check compatibility mapping
        for key, related in cls.REGION_COMPAT.items():
            if meta_region_lower == key or meta_region_lower in related:
                if model_region_lower == key or model_region_lower in related:
                    return True

        return False

    @classmethod
    def _is_2d_image(cls, dimensions: Dict[str, int]) -> bool:
        """Check if image is 2D."""
        return 'depth' not in dimensions or dimensions.get('depth', 1) == 1

    @classmethod
    def _is_3d_image(cls, dimensions: Dict[str, int]) -> bool:
        """Check if image is 3D."""
        return 'depth' in dimensions and dimensions.get('depth', 1) > 1

    @classmethod
    def calculate_compatibility_score(
        cls,
        model,  # AIModel instance
        metadata: Dict[str, Any]
    ) -> int:
        """
        Calculate compatibility score between model and image.

        Args:
            model: AIModel instance
            metadata: Image metadata dictionary

        Returns:
            Compatibility score (0-100)
        """
        score = 0

        # 1. Modality Match (50 points max)
        image_modality = metadata.get('modality', 'UNKNOWN')

        if image_modality == 'UNKNOWN':
            # No modality information, give minimal score
            score += 5
        else:
            # Check exact match in supported modalities
            supported_modalities = model.supported_modalities or []

            exact_match = any(
                image_modality.upper() == mod.upper()
                for mod in supported_modalities
            )

            if exact_match:
                score += 50
            else:
                # Check partial match
                partial_match = any(
                    cls._is_partial_modality_match(image_modality, mod)
                    for mod in supported_modalities
                )
                if partial_match:
                    score += 25

        # 2. Dimension Compatibility (30 points max)
        dimensions = metadata.get('dimensions', {})
        model_type = model.model_type or ''

        if cls._is_2d_image(dimensions):
            if '2d' in model_type.lower() or 'segmentation' in model_type.lower():
                score += 30
            elif '3d' not in model_type.lower():
                score += 10  # May still work
        elif cls._is_3d_image(dimensions):
            if '3d' in model_type.lower() or 'volume' in model_type.lower():
                score += 30
            elif 'registration' in model_type.lower():
                score += 30  # Registration typically handles 3D
            else:
                score += 10  # May work with slice extraction

        # 3. Anatomical Region Match (20 points max)
        image_region = metadata.get('anatomical_region')
        model_regions = model.anatomical_regions or []

        if image_region and model_regions:
            # Check exact match
            exact_region_match = any(
                image_region.lower() == region.lower()
                for region in model_regions
            )

            if exact_region_match:
                score += 20
            else:
                # Check compatible regions
                compatible = any(
                    cls._is_region_compatible(image_region, region)
                    for region in model_regions
                )
                if compatible:
                    score += 10

        return min(score, 100)  # Cap at 100

    @classmethod
    def generate_match_reasons(
        cls,
        model,  # AIModel instance
        metadata: Dict[str, Any],
        score: int
    ) -> List[str]:
        """
        Generate human-readable reasons for compatibility score.

        Args:
            model: AIModel instance
            metadata: Image metadata
            score: Calculated compatibility score

        Returns:
            List of match reason strings
        """
        reasons = []

        image_modality = metadata.get('modality', 'UNKNOWN')
        supported_modalities = model.supported_modalities or []

        # Modality reasons
        if image_modality != 'UNKNOWN' and supported_modalities:
            exact_match = any(
                image_modality.upper() == mod.upper()
                for mod in supported_modalities
            )

            if exact_match:
                reasons.append(f"Exact modality match: {image_modality}")
            else:
                partial_match = any(
                    cls._is_partial_modality_match(image_modality, mod)
                    for mod in supported_modalities
                )
                if partial_match:
                    reasons.append(f"Compatible modality: {image_modality}")

        # Dimension reasons
        dimensions = metadata.get('dimensions', {})
        if cls._is_3d_image(dimensions):
            if 'registration' in model.model_type.lower() or '3d' in model.model_type.lower():
                reasons.append("Optimized for 3D volumes")
        elif cls._is_2d_image(dimensions):
            if 'segmentation' in model.model_type.lower() or '2d' in model.model_type.lower():
                reasons.append("Optimized for 2D images")

        # Anatomical region reasons
        image_region = metadata.get('anatomical_region')
        model_regions = model.anatomical_regions or []

        if image_region and model_regions:
            exact_match = any(
                image_region.lower() == region.lower()
                for region in model_regions
            )
            if exact_match:
                reasons.append(f"Specialized for {image_region} imaging")

        # Add model capabilities
        if hasattr(model, 'use_cases') and model.use_cases:
            if len(reasons) < 3:  # Add use case if not enough reasons
                reasons.append(f"Supports {len(model.use_cases)} analysis tasks")

        return reasons

    @classmethod
    def generate_warnings(
        cls,
        model,  # AIModel instance
        metadata: Dict[str, Any],
        score: int
    ) -> List[str]:
        """
        Generate warnings about potential compatibility issues.

        Args:
            model: AIModel instance
            metadata: Image metadata
            score: Calculated compatibility score

        Returns:
            List of warning strings
        """
        warnings = []

        # Low score warning
        if score < 30:
            warnings.append("Low compatibility score - this model may not be suitable for this image")

        # Modality mismatch
        image_modality = metadata.get('modality', 'UNKNOWN')
        if image_modality == 'UNKNOWN':
            warnings.append("Image modality unknown - please verify model compatibility manually")

        # Dimension mismatch
        dimensions = metadata.get('dimensions', {})
        model_type = model.model_type or ''

        if cls._is_3d_image(dimensions) and '2d' in model_type.lower():
            warnings.append("3D image but model optimized for 2D - may need slice extraction")
        elif cls._is_2d_image(dimensions) and '3d' in model_type.lower():
            warnings.append("2D image but model expects 3D volumes")

        return warnings

    @classmethod
    def recommend_models(
        cls,
        metadata: Dict[str, Any],
        queryset=None,  # AIModel queryset
        min_score: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get ranked list of compatible AI models for an image.

        Args:
            metadata: Image metadata dictionary
            queryset: Optional AIModel queryset to filter (defaults to active models)
            min_score: Minimum compatibility score threshold

        Returns:
            List of dicts with model, score, reasons, and warnings
        """
        # Import here to avoid circular dependency
        from ai_analysis.models import AIModel

        # Get active models if no queryset provided
        if queryset is None:
            queryset = AIModel.objects.filter(is_active=True)

        scored_models = []

        for model in queryset:
            score = cls.calculate_compatibility_score(model, metadata)

            # Skip if below threshold
            if score < min_score:
                continue

            reasons = cls.generate_match_reasons(model, metadata, score)
            warnings = cls.generate_warnings(model, metadata, score)

            scored_models.append({
                'model': model,
                'compatibility_score': score,
                'match_reasons': reasons,
                'warnings': warnings,
            })

        # Sort by score (highest first)
        scored_models.sort(key=lambda x: x['compatibility_score'], reverse=True)

        logger.info(
            f"Recommended {len(scored_models)} models for {metadata.get('format')} "
            f"image with modality {metadata.get('modality')}"
        )

        return scored_models
