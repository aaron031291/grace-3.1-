"""
Product Discovery Pipeline

Takes synthesized market intelligence and generates product concepts.
Grace considers multiple product types (SaaS, courses, ebooks, AI automation,
physical products) and selects based on pain points, market gaps, and
Grace's own capabilities.
"""

from .product_ideation import ProductIdeationEngine
from .niche_finder import NicheFinder
