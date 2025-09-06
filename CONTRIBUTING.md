# Contributing to Doc Flow Agent

Thank you for your interest in contributing to Doc Flow Agent! This document provides guidelines for contributing to the project.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/your-username/doc_flow_agent.git`
3. Create a new branch: `git checkout -b feature/your-feature-name`
4. Install dependencies: `pip install -r requirements.txt`
5. Set up environment variables by copying `.env.example` to `.env` and configuring your API keys

## Development Guidelines

### Code Style
- Follow PEP 8 style guidelines
- Use meaningful variable and function names
- Add docstrings to all functions and classes
- Keep functions focused and single-purpose

### Testing
- Add tests for new features
- Ensure all existing tests pass
- Run tests with: `pytest`

### SOP Documents
- When adding new SOP documents, follow the existing format
- Use English for doc_id, description, and documentation
- Ensure proper YAML front matter structure
- Test your SOPs with the execution engine

### Developer Certificate of Origin (DCO)

**All contributions must be signed off using the Developer Certificate of Origin (DCO).**

- Sign your commits using `git commit -s`
- This certifies that you have the right to submit the code under the project's license
- See [DCO.md](DCO.md) for full details

### Pull Request Process

1. **Sign off all commits** with DCO (see above)
2. Update documentation if needed
3. Add tests for new functionality
4. Ensure your code follows the style guidelines
5. Create a pull request with:
   - Clear title and description
   - Reference any related issues
   - List of changes made

## Types of Contributions

- **Bug fixes**: Help us fix issues in the codebase
- **New features**: Add new functionality to the framework
- **Documentation**: Improve documentation, examples, or guides
- **SOP documents**: Create new Standard Operating Procedures
- **Tools**: Implement new tools for the framework

## Reporting Issues

When reporting issues, please include:
- Clear description of the problem
- Steps to reproduce
- Expected vs actual behavior
- Environment details (Python version, OS, etc.)
- Relevant logs or error messages

## Questions?

Feel free to open an issue for questions or join discussions in the repository.

Thanks for contributing!
