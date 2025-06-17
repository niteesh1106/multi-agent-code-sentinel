# 🤖 Multi-Agent Code Review System

An intelligent code review system that uses multiple specialized LLM agents to automatically analyze pull requests for security vulnerabilities, performance issues, code style, and documentation quality.

## ✨ Features

- **🔐 Security Agent**: Detects OWASP Top 10 vulnerabilities, SQL injection, XSS, and exposed secrets
- **⚡ Performance Agent**: Analyzes time complexity, identifies memory leaks, and detects N+1 queries
- **🎨 Style Agent**: Enforces language-specific linting rules and coding conventions
- **📝 Documentation Agent**: Evaluates docstring quality, README completeness, and inline comments
- **🧠 RAG-Enhanced**: Retrieves relevant coding standards and best practices
- **💰 Cost-Optimized**: Uses open-source models with intelligent caching

## 🏗️ Architecture

```
GitHub PR → Webhook → API Gateway → Queue → Agent Orchestrator
                                               ├── Security Agent
                                               ├── Performance Agent
                                               ├── Style Agent
                                               └── Documentation Agent
                                                         ↓
                                               RAG System (ChromaDB)
                                                         ↓
                                               Report Generator → GitHub Comment
```

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Docker & Docker Compose
- [Ollama](https://ollama.ai/) installed locally
- GitHub Personal Access Token

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/niteesh1106/multi-agent-code-review.git
   cd multi-agent-code-review
   ```

2. **Set up Python environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Pull required Ollama models**
   ```bash
   ollama pull mistral
   ollama pull codellama
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your GitHub token and preferences
   ```

5. **Start Redis (using Docker)**
   ```bash
   docker run -d -p 6379:6379 redis:alpine
   ```

6. **Run the application**
   ```bash
   # Start the API server
   uvicorn src.api.main:app --reload

   # In another terminal, start Celery worker
   celery -A src.core.celery_app worker --loglevel=info
   ```

## 🔧 Configuration

### GitHub Webhook Setup

1. Go to your repository settings → Webhooks
2. Add webhook URL: `http://your-domain.com/api/webhook`
3. Set content type to `application/json`
4. Select events: Pull Request, Pull Request Review Comment
5. Add secret (use the same in `.env`)

### Agent Configuration

Agents can be configured in `configs/settings.yaml`:

```yaml
agents:
  security:
    enabled: true
    model: "codellama"
    temperature: 0.1
    max_issues: 10
  
  performance:
    enabled: true
    model: "codellama"
    complexity_threshold: "O(n^2)"
```

## 📊 Usage

### API Endpoints

- `POST /api/webhook` - GitHub webhook receiver
- `GET /api/review/{pr_id}` - Get review status
- `POST /api/review/manual` - Trigger manual review
- `GET /api/health` - Health check

### CLI Usage

```bash
# Review a specific PR
python -m src.cli review --repo owner/repo --pr 123

# Index coding standards
python -m src.cli index --file standards/security.md

# Run evaluation
python -m src.cli evaluate --dataset test_prs.json
```

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test category
pytest tests/unit/agents/
```

## 📈 Performance

- Average review time: < 30 seconds for PRs under 500 lines
- Token usage: ~2000 tokens per PR review
- Cost per review: < $0.01 (using open-source models)

## 🛠️ Development

### Project Structure

```
src/
├── agents/          # Individual agent implementations
├── core/            # Orchestrator and core logic
├── rag/             # Vector store and retrieval
├── api/             # FastAPI application
└── utils/           # Helper functions
```

### Adding a New Agent

1. Create new file in `src/agents/`
2. Inherit from `BaseAgent` class
3. Implement `analyze()` method
4. Register in orchestrator

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [LangChain](https://langchain.com/) for the LLM orchestration framework
- [Ollama](https://ollama.ai/) for local LLM hosting
- [ChromaDB](https://www.trychroma.com/) for vector storage

## 📧 Contact

Niteesh Nitin Singh - [niteesh.nitin@gmail.com](mailto:niteesh.nitin@gmail.com)

Project Link: [https://github.com/niteesh1106/multi-agent-code-review](https://github.com/niteesh1106/multi-agent-code-review)

---

**Note**: This is a portfolio project demonstrating LLM orchestration and MLOps best practices. For production use, consider using commercial LLMs and enterprise-grade infrastructure.