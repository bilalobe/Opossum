"""GraphQL schema definition for the Opossum Search API."""
import graphene
import logging
from app.api.schema import (
    background_query_fields, background_mutation_fields,
    conversation_query_fields, conversation_mutation_fields,
    images_query_fields, images_mutation_fields,
    services_query_fields, services_mutation_fields
)

logger = logging.getLogger(__name__)

class Query(graphene.ObjectType):
    """Root query type for the GraphQL API."""
    # Add domain-specific query fields
    locals().update(background_query_fields)
    locals().update(conversation_query_fields)
    locals().update(images_query_fields)
    locals().update(services_query_fields)

class Mutation(graphene.ObjectType):
    """Root mutation type for the GraphQL API."""
    # Add domain-specific mutation fields
    locals().update(background_mutation_fields)
    locals().update(conversation_mutation_fields)
    locals().update(images_mutation_fields)
    locals().update(services_mutation_fields)

schema = graphene.Schema(
    query=Query,
    mutation=Mutation,
    description="Opossum Search GraphQL API for chat, image processing, and service monitoring"
)