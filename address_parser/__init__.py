"""
address_parser — Thai/English address parser with self-learning knowledge base
"""
from .models import ParsedAddress
from .knowledge_base import KnowledgeBase
from .parser import AddressParser

__all__ = ["ParsedAddress", "KnowledgeBase", "AddressParser"]
__version__ = "1.0.0"
