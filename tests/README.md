# Test Suite Documentation

## Overview

This test suite provides comprehensive coverage for the ArchieOS Backend, following Context7 best practices for pytest, LangChain, and serverless function testing.

## Test Structure

```
tests/
├── conftest.py              # Shared fixtures and configuration
├── fixtures/                 # Reusable test fixtures
│   ├── slack_events.py
│   └── classifications.py
├── utils/                    # Test utilities
│   ├── helpers.py
│   ├── factories.py
│   └── assertions.py
├── unit/                     # Unit tests
│   ├── test_models/         # Pydantic model tests
│   └── test_services/        # Service layer tests
├── integration/              # Integration tests
│   ├── test_supabase/       # Supabase integration tests
│   └── test_pipeline/       # End-to-end pipeline tests
├── test_api/                 # API endpoint tests
├── test_langchain/           # LangChain agent tests
├── performance/              # Performance benchmarks
└── security/                 # Security tests
```

## Running Tests

### Run all tests
```bash
pytest
```

### Run specific test categories
```bash
# Unit tests only
pytest -m unit

# Integration tests
pytest -m integration

# Skip slow tests
pytest -m "not slow"

# Run with coverage
pytest --cov=src --cov-report=html
```

### Run tests in parallel
```bash
pytest -n auto
```

### Run specific test file
```bash
pytest tests/unit/test_models/test_classification.py
```

## Test Markers

- `@pytest.mark.unit` - Unit tests (fast, no external dependencies)
- `@pytest.mark.integration` - Integration tests (require external services)
- `@pytest.mark.e2e` - End-to-end tests
- `@pytest.mark.slow` - Tests that take > 1 second
- `@pytest.mark.benchmark` - Performance benchmark tests
- `@pytest.mark.security` - Security-related tests
- `@pytest.mark.langchain` - LangChain-specific tests

## Fixtures

### Common Fixtures (conftest.py)

- `mock_supabase_client` - Mocked Supabase client
- `mock_langchain_agent` - Mocked LangChain agent
- `sample_slack_event` - Sample Slack event payload
- `sample_classification_group` - Sample GROUP classification
- `sample_classification_stray` - Sample STRAY classification
- `freeze_time_fixture` - Time freezing for debounce tests
- `mock_vercel_request` - Mock Vercel serverless request

## Test Utilities

### Helpers (`tests/utils/helpers.py`)
- `generate_slack_signature()` - Generate valid Slack signatures
- `create_slack_event()` - Create Slack event payloads
- `create_vercel_request()` - Create Vercel request objects

### Factories (`tests/utils/factories.py`)
- `create_realtor_data()` - Generate realtor test data
- `create_listing_data()` - Generate listing test data
- `create_activity_data()` - Generate activity test data
- `create_agent_task_data()` - Generate agent task test data

### Assertions (`tests/utils/assertions.py`)
- `assert_valid_classification()` - Validate classification objects
- `assert_valid_realtor()` - Validate realtor objects
- `assert_valid_listing()` - Validate listing objects
- `assert_valid_response()` - Validate API responses

## Coverage Goals

- **Target:** 80%+ code coverage
- **Current:** Run `pytest --cov=src --cov-report=term-missing` to see current coverage

## CI/CD

Tests run automatically on:
- Every push to master/main
- Every pull request
- Scheduled runs for integration tests

See `.github/workflows/test.yml` for CI/CD configuration.

## Writing New Tests

### Unit Test Example
```python
import pytest
from src.services.my_service import my_function

@pytest.mark.unit
def test_my_function():
    """Test my_function behavior."""
    result = my_function("input")
    assert result == "expected_output"
```

### Integration Test Example
```python
import pytest

@pytest.mark.integration
@pytest.mark.asyncio
async def test_database_operation(mock_supabase_client):
    """Test database operation."""
    # Test code here
    pass
```

### Parametrized Test Example
```python
@pytest.mark.parametrize("input,expected", [
    ("input1", "output1"),
    ("input2", "output2"),
])
def test_multiple_scenarios(input, expected):
    assert my_function(input) == expected
```

## Best Practices

1. **Use fixtures** for test setup/teardown
2. **Mock external dependencies** (Supabase, LLM APIs)
3. **Use parametrization** for testing multiple scenarios
4. **Mark tests appropriately** (unit, integration, slow, etc.)
5. **Write descriptive test names** that explain what is being tested
6. **Keep tests isolated** - each test should be independent
7. **Use async fixtures** for async tests with `@pytest.mark.asyncio`

## Troubleshooting

### Tests failing with import errors
- Ensure all dependencies are installed: `pip install -e ".[dev]"`
- Check that `src/` is in Python path

### Async test issues
- Ensure `pytest-asyncio` is installed
- Use `@pytest.mark.asyncio` decorator
- Use `async def` for async test functions

### Coverage not working
- Ensure `pytest-cov` is installed
- Run with `--cov=src` flag
- Check `pytest.ini` configuration


