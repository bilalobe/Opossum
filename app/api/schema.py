"""GraphQL schema definition for the Opossum Search API."""
import logging

import graphene

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


class SVGGenerationInput(graphene.InputObjectType):
    """Input for SVG generation."""
    prompt = graphene.String(required=True, description="Text prompt to generate SVG from")
    style = graphene.String(description="Optional style guidance")
    max_complexity = graphene.Int(description="Maximum complexity level (1-10)")


class SVGGenerationResult(graphene.ObjectType):
    """Result of SVG generation."""
    svg_content = graphene.String(description="SVG content as a string")
    base64_image = graphene.String(description="Base64 encoded PNG representation")
    metadata = graphene.JSONString(description="Additional metadata about the generation process")


async def resolve_generate_svg(info, input):
    """Generate an SVG from a text prompt."""
    # Check authorization if needed
    # user = info.context.get("user")

    from app.models.chat2svg import Chat2SVGGenerator
    generator = Chat2SVGGenerator()

    try:
        result = await generator.generate_svg_from_prompt(input.prompt, style=input.style)
        return SVGGenerationResult(
            svg_content=result["svg_content"],
            base64_image=result["base64_image"],
            metadata=result["metadata"]
        )
    except Exception as e:
        import traceback
        logger.error(f"Error generating SVG: {str(e)}\n{traceback.format_exc()}")
        from graphene import GraphQLError
        raise GraphQLError(f"Failed to generate SVG: {str(e)}")


class Mutation(graphene.ObjectType):
    """Root mutation type for the GraphQL API."""
    # Add domain-specific mutation fields
    locals().update(background_mutation_fields)
    locals().update(conversation_mutation_fields)
    locals().update(images_mutation_fields)
    locals().update(services_mutation_fields)

    generate_svg = graphene.Field(
        SVGGenerationResult,
        input=SVGGenerationInput(required=True),
        description="Generate an SVG from a text prompt using Chat2SVG"
    )


schema = graphene.Schema(
    query=Query,
    mutation=Mutation,
    description="Opossum Search GraphQL API for chat, image processing, and service monitoring"
)
