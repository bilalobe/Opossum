"""End-to-End test suite initialization for Opossum Search."""

import os
import logging
import pytest

# Configure logging for E2E tests
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)
logger.info("Initializing E2E test suite")

# Set environment variables for E2E testing
os.environ.setdefault('TESTING', 'True')
os.environ.setdefault('TEST_ENV', 'e2e')