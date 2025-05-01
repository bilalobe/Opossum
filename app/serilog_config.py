import os
import sys
import uuid
from datetime import datetime
from flask import g, request
import serilog
from serilog.events import LogEventLevel
from serilog.formatting.json import JsonFormatter
from serilog.sinks.rolling_file import RollingFileSink
from serilog.sinks.console import ConsoleSink

# Import Config from the main app level (which now points to the new system)
from app.config import Config

# --- Custom Enricher for Flask Request Context ---

class FlaskRequestEnricher(serilog.ILogEventEnricher):
    """Adds Flask request context (like request_id) to log events."""
    def enrich(self, log_event, property_factory):
        try:
            # Get request_id from Flask's application context global 'g' if available
            request_id = g.get('request_id', None)
            if request_id:
                log_event.add_property_if_absent(property_factory.create_property('request_id', request_id))
        except RuntimeError: # Working outside of request context
            pass

# --- Serilog Configuration Function ---

def configure_serilog():
    """
    Configures the global Serilog logger using settings from app.config.Config.
    """
    # Get settings from the central Config object
    log_level_str = Config.LOG_LEVEL
    log_to_console = Config.LOG_TO_CONSOLE
    log_to_file = Config.LOG_TO_FILE
    log_file_path = Config.LOG_FILE_PATH
    otel_service_name = Config.OTEL_SERVICE_NAME
    flask_env = Config.ENV

    # Map string level to Serilog level
    log_level_map = {
        "DEBUG": LogEventLevel.DEBUG,
        "INFO": LogEventLevel.INFORMATION,
        "WARNING": LogEventLevel.WARNING,
        "ERROR": LogEventLevel.ERROR,
        "CRITICAL": LogEventLevel.FATAL, # Map CRITICAL to FATAL
    }
    min_level = log_level_map.get(log_level_str.upper(), LogEventLevel.INFORMATION)

    # Basic configuration
    log_config = serilog.LoggerConfiguration() \
        .minimum_level(min_level) \
        .enrich.with_thread_id() \
        .enrich.with_process_id() \
        .enrich.with_property("application_name", otel_service_name) \
        .enrich.with_property("environment", flask_env) \
        .enrich(FlaskRequestEnricher()) # Add our custom enricher

    # --- Configure Sinks ---

    # Console Sink (JSON formatted)
    if log_to_console:
        console_formatter = JsonFormatter(indent=None) # Standard JSON, no extra indentation
        log_config = log_config.write_to(ConsoleSink(formatter=console_formatter))

    # Rolling File Sink (JSON formatted)
    if log_to_file:
        file_formatter = JsonFormatter(indent=None) # Use standard JSON for files
        log_config = log_config.write_to(RollingFileSink(
            path=log_file_path,
            formatter=file_formatter,
            file_size_limit_bytes=10 * 1024 * 1024, # 10 MB
            retained_file_count_limit=5,
            roll_on_file_size_limit=True
        ))

    # --- OTLP Sink (Placeholder) ---
    # otel_endpoint = Config.OTEL_EXPORTER_OTLP_ENDPOINT
    # if Config.OTEL_ENABLED and otel_endpoint:
    #     # ... (OTLP Sink implementation if available) ...
    #     pass

    # Create and set the global logger
    log = log_config.create_logger()
    serilog.Log.set_logger(log)

    # Log confirmation
    serilog.Log.information(
        "Serilog logging configured. Minimum Level: {MinLevel}, Console: {Console}, File: {File}",
        min_level, log_to_console, log_to_file
    )

    # Optional: Redirect standard logging to Serilog
    try:
        from serilog.extensions.capture_standard_library import capture_standard_library_logging
        capture_standard_library_logging()
        serilog.Log.information("Standard library logging redirected to Serilog.")
    except ImportError:
        serilog.Log.warning("Could not import capture_standard_library_logging. Standard logging not redirected.")
