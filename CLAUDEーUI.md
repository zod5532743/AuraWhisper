# AuraWhisper - CLAUDE.md

## Overview
AuraWhisper is an interactive AI-powered audio processing tool built with Python, Flask, and Web Audio API.

## Project Structure
```
AuraWhisper/
├── backend/          # Python backend (transcription, processing)
├── ui/               # Web interface (HTML/CSS/JS)
├── dist/             # Distribution packages
└── config.json       # Application configuration
```

## Key Features
- **Audio Transcription**: Real-time speech-to-text with multiple model options
- **Text-to-Speech**: High-quality voice synthesis
- **Contextual AI**: Integrates with AI for contextual understanding
- **Portable**: Works offline without internet dependency

## Development Guidelines

### Code Quality
- Use type hints for all functions
- Follow PEP 8 style guidelines
- Write comprehensive docstrings
- Add inline comments for complex logic

### Testing
- Run `pytest` before committing
- Maintain high code coverage
- Test both synchronous and asynchronous paths

### API Design
- Use RESTful conventions
- Implement proper error handling
- Document endpoints with clear descriptions

## Build Instructions

### Development
```bash
pip install -r requirements.txt
python backend/server.py
```

### Release
```powershell
./build_release.ps1
```

## Version History
See `RELEASE_NOTES.md` for detailed changelog.

## Support
For issues, see `README_日本語版.md` for Japanese documentation.
