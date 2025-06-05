# Testing Guide

This guide covers how to run tests, performance tests, and understand the various testing configurations in the jcselect project.

## Quick Start

```bash
# Run all tests (excluding performance tests)
poetry run pytest

# Run with coverage report
poetry run pytest --cov=src/jcselect --cov-report=term-missing

# Run specific test file
poetry run pytest tests/unit/test_results_controller.py -v
```

## Test Structure

```
tests/
├── unit/           # Unit tests for individual components
├── integration/    # Integration tests for component interaction
├── gui/           # GUI tests using pytest-qt
├── perf/          # Performance tests (slow)
└── conftest.py    # Shared test fixtures
```

## Environment Flags

### CI_PERF_SKIP

Controls whether performance tests are skipped:
- `CI_PERF_SKIP=1` (default in CI): Skip performance tests
- `CI_PERF_SKIP=0`: Run performance tests

```bash
# Run all tests including performance tests
CI_PERF_SKIP=0 poetry run pytest

# Run only performance tests
CI_PERF_SKIP=0 poetry run pytest tests/perf/ -v
```

### CI_COV_MIN

Override the minimum coverage threshold:
- Default: 90%
- Override: Set `CI_COV_MIN=85` to require 85% coverage instead

```bash
# Run tests with custom coverage threshold
CI_COV_MIN=85 poetry run pytest
```

### QT_QPA_PLATFORM

For headless GUI testing:
- Linux CI: `QT_QPA_PLATFORM=offscreen`
- Local development: Usually not needed

## Performance Tests

Performance tests are located in `tests/perf/` and test:

1. **Large Dataset Performance** (`test_large_dataset_performance.py`)
   - Creates 5k candidates × 200 pens synthetic data
   - Tests `refreshData()` completes < 1.5s on SQLite
   - Memory usage stability during operations

2. **Fast Sync Latency** (`test_fast_sync_latency.py`)
   - Simulates 50 rapid ballot confirmations
   - Tests end-to-end latency ≤ 2s
   - Debouncing and memory impact testing

### Running Performance Tests Locally

```bash
# Install performance test dependencies
poetry add psutil --group dev

# Run performance tests with verbose output
CI_PERF_SKIP=0 poetry run pytest tests/perf/ -v -s

# Run specific performance test
CI_PERF_SKIP=0 poetry run pytest tests/perf/test_large_dataset_performance.py::TestLargeDatasetPerformance::test_refresh_data_performance -v
```

### Expected Performance Benchmarks

| Test | Target | Hardware Requirement |
|------|--------|---------------------|
| refreshData() with 5k candidates | < 1.5s | SQLite in-memory |
| Single ballot confirmation latency | ≤ 2.0s | Standard CI runner |
| 50 rapid confirmations (avg) | ≤ 2.0s | Standard CI runner |
| Memory growth (100 updates) | < 100MB | Any system |

## Coverage Requirements

- **Minimum Coverage**: 90% (configurable via `CI_COV_MIN`)
- **Coverage Reports**: 
  - Terminal: `--cov-report=term-missing`
  - XML: `--cov-report=xml` (for CI integration)
  - HTML: `--cov-report=html` (for local inspection)

### Excluded from Coverage

- Test files
- Alembic migrations
- QML files
- Virtual environments
- Build directories

```bash
# Generate HTML coverage report
poetry run pytest --cov=src/jcselect --cov-report=html
# Open htmlcov/index.html in browser
```

## Test Categories

### Unit Tests (`tests/unit/`)

Test individual components in isolation:
- DAO layer methods
- Controller logic
- Utility functions
- Model validation

```bash
# Run all unit tests
poetry run pytest tests/unit/ -v

# Run specific module tests
poetry run pytest tests/unit/test_results_dao.py -v
```

### Integration Tests (`tests/integration/`)

Test component interactions:
- Database operations with real data
- Sync engine integration
- Export functionality end-to-end

```bash
# Run integration tests
poetry run pytest tests/integration/ -v
```

### GUI Tests (`tests/gui/`)

Test QML components and user interactions:
- Component rendering
- Signal/slot connections
- User input handling

```bash
# Run GUI tests (may require display)
poetry run pytest tests/gui/ -v

# Run GUI tests headless (Linux)
QT_QPA_PLATFORM=offscreen poetry run pytest tests/gui/ -v
```

## Continuous Integration

### Regular CI (Push/PR)

Runs on matrix: `[ubuntu-latest, windows-latest] × [Python 3.10, 3.11]`

```yaml
env:
  CI_PERF_SKIP: 1  # Skip performance tests
  CI_COV_MIN: 90   # Require 90% coverage
```

### Nightly Performance CI

Runs performance tests on schedule:

```yaml
env:
  CI_PERF_SKIP: 0  # Enable performance tests
  QT_QPA_PLATFORM: offscreen
```

## Test Data Management

### Fixtures

Common test fixtures are in `conftest.py`:
- Database sessions
- Mock controllers
- Sample data

### Synthetic Data Generation

Performance tests generate large synthetic datasets:
- 200 pens
- 25 parties
- 5,000 candidates (25 per party per pen)
- Random vote distributions

## Debugging Tests

### Verbose Output

```bash
# Show test names and outcomes
poetry run pytest -v

# Show print statements and logs
poetry run pytest -s

# Show full tracebacks
poetry run pytest --tb=long
```

### Running Single Tests

```bash
# Run specific test method
poetry run pytest tests/unit/test_dao.py::TestDAO::test_get_totals_by_party -v

# Run tests matching pattern
poetry run pytest -k "test_performance" -v
```

### Memory Debugging

For memory-related issues:

```bash
# Install memory profiler
pip install memory-profiler

# Profile memory usage
poetry run python -m memory_profiler your_test_script.py
```

## Static Analysis

### Ruff (Linting)

```bash
# Check code style
poetry run ruff check .

# Auto-fix issues
poetry run ruff check . --fix

# Format code
poetry run ruff format .
```

### MyPy (Type Checking)

```bash
# Run type checking
poetry run mypy src/jcselect

# Check specific file
poetry run mypy src/jcselect/controllers/results_controller.py
```

## Common Issues

### Qt GUI Tests Failing

**Issue**: GUI tests fail with display errors
**Solution**: Set `QT_QPA_PLATFORM=offscreen` or install virtual display

```bash
# Linux
sudo apt-get install xvfb
export QT_QPA_PLATFORM=offscreen

# Or use xvfb-run
xvfb-run -a poetry run pytest tests/gui/
```

### Performance Tests Timeout

**Issue**: Performance tests take too long or timeout
**Solution**: Check system resources and database performance

```bash
# Check available memory
free -h

# Monitor test execution
poetry run pytest tests/perf/ -v -s --tb=short
```

### Coverage Below Threshold

**Issue**: Tests pass but coverage is below minimum
**Solution**: Add tests for uncovered code or adjust threshold

```bash
# See what's missing coverage
poetry run pytest --cov=src/jcselect --cov-report=term-missing

# Generate detailed HTML report
poetry run pytest --cov=src/jcselect --cov-report=html
```

## Best Practices

1. **Write Fast Unit Tests**: Keep unit tests under 100ms each
2. **Mock External Dependencies**: Use mocks for database, file system, network
3. **Use Fixtures**: Share common setup code via pytest fixtures
4. **Test Edge Cases**: Include boundary conditions and error scenarios
5. **Keep Tests Independent**: Each test should be able to run in isolation
6. **Use Descriptive Names**: Test names should describe what they verify
7. **Group Related Tests**: Use test classes to organize related functionality

## Hardware Requirements

### Minimum for Development

- RAM: 8GB (4GB available for tests)
- CPU: 2 cores
- Storage: 1GB free space
- Python: 3.10 or 3.11

### Recommended for Performance Testing

- RAM: 16GB (8GB available for tests)
- CPU: 4+ cores
- Storage: SSD with 5GB free space
- Python: 3.11

### CI Environment

- Ubuntu: `ubuntu-latest` (4 cores, 16GB RAM)
- Windows: `windows-latest` (4 cores, 16GB RAM)
- Performance tests run on Ubuntu only for consistency 