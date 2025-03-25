"""Apollo Studio compatible monitoring middleware using OpenTelemetry."""
import logging

from ddtrace import patch, tracer
from flask import jsonify
from opentelemetry.instrumentation.flask import FlaskInstrumentor

logger = logging.getLogger(__name__)


class ApolloMiddleware:
    """Middleware for Apollo-compatible monitoring."""

    def __init__(self, app, schema):
        self.app = app
        self.schema = schema
        self.setup_monitoring()
        self.setup_routes()

    def setup_monitoring(self):
        """Set up OpenTelemetry monitoring."""
        # Initialize Flask instrumentation
        FlaskInstrumentor().instrument_app(self.app)

        # Initialize Datadog APM for Apollo compatibility
        patch(graphql=True)

        @tracer.wrap(service="opossum-graphql")
        def wrap_graphql_execute(fn):
            def wrapped(*args, **kwargs):
                with tracer.trace("graphql.execute"):
                    return fn(*args, **kwargs)

            return wrapped

        # Wrap GraphQL execution
        self.schema.execute = wrap_graphql_execute(self.schema.execute)

    def setup_routes(self):
        """Set up monitoring endpoints."""

        @self.app.route('/.well-known/apollo/server-health')
        def health_check():
            """Apollo health check endpoint."""
            return jsonify({
                "status": "pass",
                "checks": {
                    "graphql": {"status": "pass"},
                    "storage": {"status": "pass"}
                }
            })

        @self.app.route('/graphql/metrics')
        def metrics():
            """Prometheus-compatible metrics endpoint."""
            return jsonify({
                "schema_version": "1.0",
                "schemaChangeLastSuccess": True,
                "servicesTotal": 1,
                "queries": tracer.stats().get("graphql.execute", 0)
            })

        @self.app.route('/graphql/schema')
        def get_schema():
            """Serve the GraphQL schema."""
            return self.schema.stringify(), 200, {
                'Content-Type': 'text/plain',
                'Apollo-Schema-Version': '1.0'
            }

    def get_apollo_config(self):
        """Get Apollo Studio configuration."""
        return {
            "apollo": {
                "graphRef": "opossum-search@current",
                "schemaReporting": {
                    "enabled": True,
                    "headers": {
                        "user-agent": "Opossum-Search/1.0"
                    }
                },
                "includeTraces": True,
                "sendTraces": True,
                "sendErrors": True
            }
        }
