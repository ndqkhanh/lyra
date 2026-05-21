# Contributing to Lyra RSI

Thank you for your interest in contributing to Lyra RSI! This document provides guidelines for contributing to the project.

## Code of Conduct

Please be respectful and constructive in all interactions.

## How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported in Issues
2. If not, create a new issue with:
   - Clear title and description
   - Steps to reproduce
   - Expected vs actual behavior
   - System information (OS, Node version, etc.)
   - Relevant logs or error messages

### Suggesting Enhancements

1. Check if the enhancement has been suggested
2. Create a new issue with:
   - Clear title and description
   - Use case and motivation
   - Proposed implementation (if applicable)
   - Potential drawbacks or alternatives

### Pull Requests

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass (`npm test`)
6. Ensure code is formatted (`npm run format`)
7. Ensure linting passes (`npm run lint`)
8. Commit your changes (`git commit -m 'Add amazing feature'`)
9. Push to the branch (`git push origin feature/amazing-feature`)
10. Open a Pull Request

### Pull Request Guidelines

- Follow the existing code style
- Write clear commit messages
- Add tests for new features
- Update documentation as needed
- Keep PRs focused on a single feature/fix
- Reference related issues

## Development Setup

```bash
# Clone your fork
git clone https://github.com/yourusername/lyra-rsi.git
cd lyra-rsi

# Install dependencies
npm install

# Copy environment template
cp .env.example .env

# Run tests
npm test

# Run in development mode
npm run dev
```

## Code Style

- Use TypeScript
- Follow existing patterns
- Use meaningful variable names
- Add comments for complex logic
- Keep functions focused and small
- Use async/await over promises

## Testing

- Write unit tests for new functionality
- Ensure all tests pass before submitting PR
- Aim for high test coverage
- Test edge cases and error conditions

## Documentation

- Update README.md for user-facing changes
- Add JSDoc comments for public APIs
- Update type definitions as needed
- Include examples for new features

## Commit Messages

Follow conventional commits format:

```
type(scope): subject

body

footer
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

Examples:
```
feat(agent0): add synthetic task generation
fix(skillrl): correct skill scoring calculation
docs(readme): update installation instructions
```

## Questions?

Feel free to open an issue for questions or discussions.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
