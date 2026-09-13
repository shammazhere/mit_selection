
"""
Explanation Generator Module

Creates templated natural-language explanations from fusion inputs.
"""

from .generator import (
    ExplanationGenerator,
    ExplanationResult,
    default_explanation_generator
)

__all__ = [
    "ExplanationGenerator",
    "ExplanationResult",
    "default_explanation_generator"
]
