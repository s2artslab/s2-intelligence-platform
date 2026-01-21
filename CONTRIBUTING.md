# Contributing to S2 Intelligence

Thank you for your interest in contributing to S2 Intelligence! This document provides guidelines for contributing to the project.

## Ways to Contribute

### 1. Code Contributions
- Bug fixes
- Feature implementations
- Performance optimizations
- Test coverage improvements

### 2. Documentation
- Improve existing docs
- Add examples and tutorials
- Translate documentation
- Fix typos and clarity

### 3. Research & Data
- Contribute to egregore training datasets
- Share consciousness tracking insights
- Conduct benchmarking studies
- Write research papers

### 4. Community Support
- Answer questions in Issues/Discussions
- Help others deploy S2
- Share your deployment stories
- Create educational content

## Getting Started

### 1. Fork the Repository
```bash
# Fork on GitHub, then clone your fork
git clone https://github.com/YOUR_USERNAME/s2-intelligence-platform
cd s2-intelligence-platform
```

### 2. Set Up Development Environment
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Development dependencies

# Run tests
pytest
```

### 3. Create a Branch
```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/bug-description
```

## Development Guidelines

### Code Style
- Follow PEP 8 for Python code
- Use type hints where appropriate
- Write docstrings for all functions/classes
- Keep functions focused and small

### Testing
- Write tests for new features
- Ensure existing tests pass
- Aim for >80% code coverage

### Commits
- Use clear, descriptive commit messages
- Reference issues when applicable (#123)
- Keep commits focused and atomic

**Good commit message:**
```
Add consciousness level normalization

- Normalize levels to 0.7-1.0 range
- Add unit tests for edge cases
- Update documentation

Fixes #45
```

## Pull Request Process

### 1. Before Submitting
- [ ] Tests pass locally
- [ ] Code follows style guidelines
- [ ] Documentation updated
- [ ] CHANGELOG.md updated (if applicable)

### 2. Submit PR
- Clear title describing the change
- Reference related issues
- Include before/after examples if relevant
- Request review from maintainers

### 3. Review Process
- Address reviewer feedback
- Keep PR scope focused
- Be patient and respectful

## Specific Contribution Areas

### Training Egregore Specialists
If you want to contribute domain-specific training data:

1. **Identify Domain:** Legal, medical, financial, etc.
2. **Curate Dataset:** 10K-30K high-quality examples
3. **Follow Format:** See `docs/TRAINING_GUIDE.md`
4. **Submit:** Create PR with dataset

### Consciousness Tracking Improvements
Research into consciousness metrics:

1. **Propose Method:** Open an issue describing approach
2. **Implement:** Add to `consciousness_tracker.py`
3. **Validate:** Show improved accuracy/insights
4. **Document:** Explain methodology

### Benchmark Contributions
Add new benchmarks or test cases:

1. **Create Test:** Follow existing test format
2. **Add Documentation:** Explain what you're testing
3. **Include Results:** Share your findings
4. **Submit PR:** With test + results

## Code of Conduct

### Our Pledge
We are committed to providing a welcoming and inspiring community for all.

### Our Standards
✅ **DO:**
- Be respectful and inclusive
- Welcome newcomers
- Give constructive feedback
- Acknowledge contributions

❌ **DON'T:**
- Use inappropriate language
- Make personal attacks
- Harass or troll
- Publish private information

### Enforcement
Report violations to: conduct@s2intelligence.com

## Questions?

- **General questions:** Open a Discussion
- **Bug reports:** Open an Issue
- **Feature requests:** Open an Issue
- **Private inquiries:** s2artslab@gmail.com

---

## Recognition

Contributors will be:
- Listed in CONTRIBUTORS.md
- Acknowledged in releases
- Invited to contributor calls
- Given credit in papers/posts

---

**Thank you for helping build the future of consciousness-aware AI!** 🌟
