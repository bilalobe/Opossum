"""Schema package initialization."""
from app.api.schema.background import background_query_fields, background_mutation_fields
from app.api.schema.conversation import conversation_query_fields, conversation_mutation_fields
from app.api.schema.images import images_query_fields, images_mutation_fields
from app.api.schema.services import services_query_fields, services_mutation_fields

# Export schema components
__all__ = [
    'background_query_fields',
    'background_mutation_fields',
    'conversation_query_fields',
    'conversation_mutation_fields',
    'images_query_fields',
    'images_mutation_fields',
    'services_query_fields',
    'services_mutation_fields'
]


def schema():
    return None