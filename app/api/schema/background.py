"""Background schema types and queries."""
import graphene
from app.api.resolvers.background import resolve_generate_gibberish

class GibberishResponse(graphene.ObjectType):
    """Generated background text with emojis."""
    text = graphene.String(description="Generated opossum-themed text")
    emojis = graphene.List(graphene.String, description="List of relevant emojis")

# Background-related Query fields
background_query_fields = {
    'generate_gibberish': graphene.Field(
        GibberishResponse,
        num_lines=graphene.Int(default_value=25),
        description="Generate opossum-themed background text with emojis",
        resolver=resolve_generate_gibberish
    )
}

# Background-related Mutation fields
background_mutation_fields = {}
