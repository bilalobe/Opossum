# Contributing to Opossum Search

Thank you for your interest in contributing to Opossum Search! This document provides guidelines and instructions for contributing to the project.

## Code of Conduct

All contributors are expected to adhere to our Code of Conduct. We are committed to making participation in this project a harassment-free experience for everyone, regardless of level of experience, gender, gender identity and expression, sexual orientation, disability, personal appearance, body size, race, ethnicity, age, religion, or nationality.

## Getting Started

### Development Environment Setup

1. **Clone the repository**

   ```bash
   git clone https://github.com/bilalobe/opossum.git
   cd opossum
   ```

2. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt  # Development dependencies
   ```

3. **Set up environment variables**

   Copy the example environment file and update it with your settings:

   ```bash
   cp .env.example .env
   ```

   Required environment variables:
   - `REDIS_HOST`: Redis host address
   - `GEMINI_API_KEY`: Google Gemini API key
   - `OPENTELEMETRY_ENDPOINT`: OpenTelemetry collector endpoint (if using telemetry)

4. **Start the development server**

   ```bash
   python app/main.py
   ```

### Running Tests

Before submitting a contribution, ensure all tests pass:

```bash
pytest
```

For specific test suites:

```bash
pytest tests/test_redis_cache.py
pytest tests/test_resilience.py
```

## Development Workflow

### Branching Strategy

- `main`: Production-ready code
- `develop`: Integration branch for features
- `feature/*`: Feature branches
- `bugfix/*`: Bug fix branches
- `docs/*`: Documentation updates

### Creating a Feature Branch

```bash
git checkout develop
git pull
git checkout -b feature/your-feature-name
```

### Making Changes

1. Make your changes following the coding standards
2. Add tests for new functionality
3. Update documentation as needed
4. Ensure all tests pass

### Committing Changes

Follow the conventional commits specification:

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

Types:
- `feat`: A new feature
- `fix`: A bug fix
- docs: Documentation only changes
- `style`: Changes that do not affect the meaning of the code
- `refactor`: A code change that neither fixes a bug nor adds a feature
- `perf`: A code change that improves performance
- `test`: Adding missing tests or correcting existing tests
- `chore`: Changes to the build process or auxiliary tools

Example:
```
feat(model-selection): add capability scoring for model routing

Implements a scoring system for model selection based on query capabilities.
This allows more efficient routing to appropriate AI backends.

Closes #123
```

## Pull Request Process

1. **Update your feature branch with the latest changes from develop**
   ```bash
   git checkout develop
   git pull
   git checkout feature/your-feature-name
   git rebase develop
   ```

2. **Push your changes to your fork**
   ```bash
   git push origin feature/your-feature-name
   ```

3. **Create a pull request (PR) to the develop branch**
   - Fill in the PR template with all required information
   - Link related issues
   - Request review from appropriate team members

4. **Address review feedback**
   - Make requested changes
   - Push additional commits
   - Respond to comments

5. **PR Approval and Merge**
   - PRs require at least one approval
   - All automated checks must pass
   - Merge will be handled by maintainers

## Coding Standards

### Python Style Guide

- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) style guide
- Use type hints for function signatures
- Maximum line length: 88 characters
- Use Black for code formatting
- Use isort for import sorting

### Documentation

- Use docstrings for all modules, classes, and functions
- Follow Google docstring format
- Update appropriate markdown documentation files

## Testing Requirements

- All new features must include unit tests
- Maintain or improve test coverage
- Include integration tests for API endpoints or model interaction
- Performance tests for resource-intensive operations

## Component-Specific Guidelines

### Redis Caching

- Always provide TTL for cached items
- Use namespaced keys for different cache types
- Consider memory usage implications
- Test with both cache hits and misses

### Model Integration

- New model integrations must implement the standard interface
- Include capability declaration in the model registry
- Add comprehensive error handling
- Document model-specific limitations

### GraphQL API

- Follow naming conventions for types and fields
- Add schema documentation comments
- Include input validation
- Add appropriate permissions

### Image Processing & SVG

- Include performance optimization for resource-intensive operations
- Add appropriate input validation for file sizes
- Document any new filter or effect thoroughly

## Documentation Guidelines

- Update markdown files in the docs/ directory for features
- Use clear headings and proper hierarchy
- Include code examples when relevant
- Add diagrams for complex processes (use Mermaid)
- Update API documentation for new endpoints

## Community Resources

- **Issue Tracker**: Report bugs or suggest features on our GitHub issues
- **Discussions**: Join project discussions on GitHub Discussions
- **Chat**: Join our Discord server for real-time collaboration
- **Mailing List**: Subscribe to our development mailing list for updates

## Release Process

Contributors should be aware of our release process:

1. Features are merged into `develop`
2. Release candidates are created from `develop`
3. After testing, RC is merged to `main`
4. Tags are created for versions

## Recognition

All contributors will be recognized in our CONTRIBUTORS.md file and release notes.

---

Thank you for contributing to Opossum Search! Your efforts help make this project better for everyone.
