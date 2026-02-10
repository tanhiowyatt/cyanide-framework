# Contributing to Cyanide Honeypot

Thank you for your interest in contributing to the Cyanide Honeypot project! We welcome contributions from the community to help improve the security and capabilities of this tool.

## Getting Started

### Prerequisites

- Python 3.9+
- Docker (optional, for containerized testing)

### Setting up the Environment

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/tanhiowyatt/cyanide.git
    cd cyanide
    ```

2.  **Create a virtual environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    pip install ruff  # For linting
    ```

## Development Guidelines

### Code Style

We use **Ruff** for linting and code formatting. Please ensure your code adheres to these standards before submitting a pull request.

- Run the linter:
    ```bash
    ruff check .
    ```
- Auto-fix common issues:
    ```bash
    ruff check --fix .
    ```

### Testing

All new features and bug fixes must be accompanied by tests. We use **pytest**.

- Run all tests:
    ```bash
    pytest tests/
    ```
- Run a specific test file:
    ```bash
    pytest tests/path/to/test_file.py
    ```

## Submitting Pull Requests

1.  **Fork the repository** and create a new branch for your feature or fix.
    ```bash
    git checkout -b feature/my-new-feature
    ```

2.  **Make your changes** and commit them with clear, descriptive messages.

3.  **Run tests and linting** to ensure no regressions.

4.  **Push your branch** to your fork:
    ```bash
    git push origin feature/my-new-feature
    ```

5.  **Open a Pull Request** against the `main` branch. Describe your changes detailedly and link any relevant issues.

## Reporting Bugs

If you find a bug, please open an issue on GitHub with the following details:
- Steps to reproduce
- Expected behavior
- Actual behavior
- Logs or screenshots (if applicable)

## License

By contributing, you agree that your contributions will be licensed under the project's [license](LICENSE).
