# Contributing to Synrax AI Agent

Thank you for your interest in contributing to Synrax AI Agent! We welcome contributions from the community and are grateful for any help you can provide.

## 🚀 Getting Started

### Prerequisites

- Python 3.11 or higher
- Git
- Ollama (for testing with LLM features)
- Docker (optional, for containerized development)

### Development Setup

1. **Fork and clone the repository**
   ```bash
   git clone https://github.com/martinsebastian/synrax-ai-agent.git
   cd synrax-ai-agent
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

4. **Set up pre-commit hooks**
   ```bash
   pre-commit install
   ```

5. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

6. **Run tests to ensure everything works**
   ```bash
   pytest
   ```

## 🔄 Development Workflow

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Follow the coding standards below
   - Add tests for new functionality
   - Update documentation as needed

3. **Run quality checks**
   ```bash
   # Format code
   black src/ tests/
   isort src/ tests/
   
   # Lint code
   flake8 src/ tests/
   
   # Type checking
   mypy src/
   
   # Security scan
   bandit -r src/
   
   # Run tests
   pytest --cov=src
   ```

4. **Commit your changes**
   ```bash
   git add .
   git commit -m "feat: add new feature description"
   ```

5. **Push to your fork**
   ```bash
   git push origin feature/your-feature-name
   ```

6. **Create a Pull Request**
   - Use the PR template
   - Ensure all checks pass
   - Request review from maintainers

## 📋 Coding Standards

### Python Code Style

- Follow [PEP 8](https://pep8.org/) guidelines
- Use [Black](https://black.readthedocs.io/) for code formatting
- Use [isort](https://pycqa.github.io/isort/) for import sorting
- Maximum line length: 88 characters (Black default)

### Type Hints

- Use type hints for all function parameters and return values
- Import types from `typing` module when needed
- Use `Optional[T]` for nullable parameters

```python
from typing import List, Optional, Dict, Any

def process_documents(docs: List[str], config: Optional[Dict[str, Any]] = None) -> List[Dict[str, str]]:
    """Process a list of documents."""
    pass
```

### Documentation

- Write docstrings for all public functions, classes, and modules
- Use Google-style docstrings
- Include examples in docstrings when helpful

```python
def query_agent(question: str, context: Optional[str] = None) -> Dict[str, Any]:
    """Query the AI agent with a question.
    
    Args:
        question: The user's question to process
        context: Optional context to include in the query
        
    Returns:
        Dictionary containing the answer and source documents
        
    Example:
        >>> result = query_agent("What is machine learning?")
        >>> print(result["answer"])
    """
    pass
```

### Error Handling

- Use specific exception types
- Include meaningful error messages
- Log errors appropriately

```python
import logging

logger = logging.getLogger(__name__)

try:
    result = process_data(data)
except ValueError as e:
    logger.error(f"Invalid data format: {e}")
    raise
except Exception as e:
    logger.error(f"Unexpected error in process_data: {e}")
    raise
```

## 🧪 Testing Guidelines

### Test Structure

- Place tests in the `tests/` directory
- Name test files with `test_` prefix
- Use descriptive test function names

### Test Types

1. **Unit Tests**: Test individual functions and classes
2. **Integration Tests**: Test component interactions
3. **API Tests**: Test HTTP endpoints
4. **Security Tests**: Test authentication and authorization

### Writing Good Tests

```python
import pytest
from unittest.mock import patch, MagicMock

class TestAIAgent:
    """Test the AIAgent class."""
    
    def test_initialization_success(self):
        """Test successful agent initialization."""
        agent = AIAgent()
        assert agent is not None
        
    def test_query_with_valid_input(self):
        """Test query with valid input returns expected response."""
        agent = AIAgent()
        result = agent.query("test question")
        
        assert "answer" in result
        assert isinstance(result["answer"], str)
        
    @patch('src.agent.ChatOllama')
    def test_query_with_mocked_llm(self, mock_llm):
        """Test query with mocked LLM."""
        mock_llm.return_value.invoke.return_value = "mocked response"
        
        agent = AIAgent()
        result = agent.query("test")
        
        assert result["answer"] == "mocked response"
```

### Test Coverage

- Maintain minimum 90% test coverage
- Focus on testing critical paths and edge cases
- Mock external dependencies (Ollama, databases, etc.)

## 🐛 Bug Reports

When reporting bugs, please include:

1. **Environment Information**
   - Python version
   - Operating system
   - Package versions

2. **Steps to Reproduce**
   - Minimal code example
   - Input data that causes the issue
   - Expected vs actual behavior

3. **Error Information**
   - Full error messages and stack traces
   - Log output (sanitized of sensitive information)

## 💡 Feature Requests

For new features:

1. **Check existing issues** to avoid duplicates
2. **Describe the use case** clearly
3. **Consider implementation complexity**
4. **Discuss architectural impact**

## 📝 Documentation

### README Updates

- Update feature lists for new functionality
- Add usage examples for new APIs
- Update installation instructions if needed

### Code Comments

- Explain complex algorithms or business logic
- Document non-obvious design decisions
- Include TODO comments for future improvements

### API Documentation

- Update endpoint documentation for new routes
- Include request/response examples
- Document error codes and responses

## 🔒 Security

### Security Guidelines

- Never commit secrets, passwords, or API keys
- Use environment variables for configuration
- Validate all user inputs
- Follow OWASP security guidelines
- Report security vulnerabilities privately

### Reporting Security Issues

Email security issues to: martin.sebastian@synrax.com

Please include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact assessment
- Suggested fix (if any)

## 📞 Getting Help

- **General Questions**: Use GitHub Discussions
- **Bug Reports**: Create GitHub Issues
- **Security Issues**: Email martin.sebastian@synrax.com
- **Feature Requests**: Use GitHub Issues with enhancement label

## 🎯 Areas for Contribution

We especially welcome contributions in these areas:

### High Priority
- 🔒 **Security**: Authentication improvements, security audits
- 🧪 **Testing**: Increase test coverage, add performance tests
- 📊 **Monitoring**: Enhanced metrics and alerting
- 📚 **Documentation**: User guides, tutorials, examples

### Medium Priority
- 🧠 **AI/ML**: New embedding models, improved RAG algorithms
- 🌐 **Frontend**: UI improvements, mobile responsiveness
- 🔧 **DevOps**: CI/CD improvements, deployment automation
- 🚀 **Performance**: Optimization, caching improvements

### Good First Issues
- 📝 Documentation improvements
- 🐛 Bug fixes with clear reproduction steps
- 🧪 Adding tests for existing functionality
- 🎨 Code style and formatting improvements

## 📋 Review Process

1. **Automated Checks**: All PRs must pass CI/CD pipeline
2. **Code Review**: At least one maintainer review required
3. **Testing**: New functionality must include tests
4. **Documentation**: Updates to docs for user-facing changes

## 🏆 Recognition

Contributors will be:
- Added to the CONTRIBUTORS.md file
- Mentioned in release notes for significant contributions
- Invited to join the maintainer team for sustained contributions

## 📄 License

By contributing to Synrax AI Agent, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to Synrax AI Agent! Your efforts help make this project better for everyone.

*For questions about contributing, please reach out to Martin Sebastian at martin.sebastian@synrax.com*