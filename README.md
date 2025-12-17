# TestFlow Platform 🚀

A comprehensive **Test Case Management and Execution Platform** built with modern Python technologies. This platform enables teams to manage test cases, execute test suites, and generate detailed reports with real-time analytics.

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-blue.svg)
![MongoDB](https://img.shields.io/badge/MongoDB-6.0+-green.svg)
![Redis](https://img.shields.io/badge/Redis-7.0+-red.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)

## 🎯 Project Overview

TestFlow is an enterprise-grade test management solution designed for QA teams and developers to:

- **Organize** test cases into projects and test suites
- **Execute** tests asynchronously with real-time status updates
- **Track** test execution history and results
- **Analyze** test coverage and pass/fail trends
- **Integrate** with CI/CD pipelines via RESTful APIs

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend / API Clients                    │
└─────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                         FastAPI Application                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │   Auth      │  │   Projects  │  │  Test Cases │              │
│  │   Module    │  │   Module    │  │   Module    │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │  Execution  │  │  Reporting  │  │   Webhooks  │              │
│  │   Module    │  │   Module    │  │   Module    │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
└─────────────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│ PostgreSQL  │      │   MongoDB   │      │    Redis    │
│ (Relational)│      │ (Documents) │      │  (Cache)    │
└─────────────┘      └─────────────┘      └─────────────┘
                                                  │
                                                  ▼
                                          ┌─────────────┐
                                          │  RabbitMQ   │
                                          │  (Broker)   │
                                          └─────────────┘
                                                  │
                                                  ▼
                                          ┌─────────────┐
                                          │   Celery    │
                                          │  (Workers)  │
                                          └─────────────┘
```

## 🛠️ Tech Stack

| Category             | Technology              |
| -------------------- | ----------------------- |
| **Framework**        | FastAPI 0.104+          |
| **Language**         | Python 3.11+            |
| **Relational DB**    | PostgreSQL 15           |
| **Document DB**      | MongoDB 6.0             |
| **Cache**            | Redis 7.0               |
| **Message Queue**    | RabbitMQ / Celery       |
| **Authentication**   | JWT + OAuth2            |
| **Containerization** | Docker & Docker Compose |
| **CI/CD**            | GitHub Actions          |
| **Testing**          | Pytest + Coverage       |

## 📁 Project Structure

```
testflow-platform/
├── app/
│   ├── api/                    # API route handlers
│   │   ├── v1/
│   │   │   ├── auth.py
│   │   │   ├── projects.py
│   │   │   ├── test_cases.py
│   │   │   ├── test_suites.py
│   │   │   ├── executions.py
│   │   │   └── reports.py
│   │   └── deps.py             # Dependency injection
│   ├── core/                   # Core configurations
│   │   ├── config.py
│   │   ├── security.py
│   │   └── exceptions.py
│   ├── db/                     # Database connections
│   │   ├── postgresql.py
│   │   ├── mongodb.py
│   │   └── redis.py
│   ├── models/                 # SQLAlchemy models
│   │   ├── user.py
│   │   ├── project.py
│   │   ├── test_case.py
│   │   └── execution.py
│   ├── schemas/                # Pydantic schemas
│   │   ├── user.py
│   │   ├── project.py
│   │   ├── test_case.py
│   │   └── execution.py
│   ├── services/               # Business logic
│   │   ├── auth_service.py
│   │   ├── project_service.py
│   │   ├── test_case_service.py
│   │   └── execution_service.py
│   ├── tasks/                  # Celery async tasks
│   │   ├── celery_app.py
│   │   ├── execution_tasks.py
│   │   └── report_tasks.py
│   └── main.py                 # Application entry point
├── tests/                      # Test suite
│   ├── unit/
│   ├── integration/
│   └── conftest.py
├── docker/                     # Docker configurations
│   ├── Dockerfile
│   └── Dockerfile.celery
├── .github/
│   └── workflows/
│       └── ci.yml
├── docker-compose.yml
├── requirements.txt
├── requirements-dev.txt
├── alembic.ini
├── .env.example
└── README.md
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- Git

### Using Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/iambiniyam/testflow-platform.git
cd testflow-platform

# Copy environment file
cp .env.example .env

# Start all services
docker-compose up -d

# Run database migrations
docker-compose exec app alembic upgrade head

# Access the API documentation
open http://localhost:8000/docs
```

### Local Development

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
.\venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements-dev.txt

# Set up environment variables
cp .env.example .env

# Start infrastructure services
docker-compose up -d postgres mongodb redis rabbitmq

# Run database migrations
alembic upgrade head

# Start the application
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Start Celery worker (in another terminal)
celery -A app.tasks.celery_app worker --loglevel=info
```

## 📚 API Documentation

Once the application is running, access the interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

### Key Endpoints

| Method | Endpoint                         | Description             |
| ------ | -------------------------------- | ----------------------- |
| POST   | `/api/v1/auth/register`          | Register new user       |
| POST   | `/api/v1/auth/login`             | User login              |
| GET    | `/api/v1/projects`               | List all projects       |
| POST   | `/api/v1/projects`               | Create new project      |
| GET    | `/api/v1/test-cases`             | List test cases         |
| POST   | `/api/v1/test-cases`             | Create test case        |
| POST   | `/api/v1/executions`             | Start test execution    |
| GET    | `/api/v1/executions/{id}/status` | Get execution status    |
| GET    | `/api/v1/reports/summary`        | Get test summary report |

## 🔐 Authentication

The API uses JWT-based authentication with role-based access control (RBAC).

### Roles

- **Admin**: Full access to all resources
- **Manager**: Manage projects and test cases
- **Tester**: Execute tests and view reports
- **Viewer**: Read-only access

### Example Authentication Flow

```python
import httpx

# Login
response = httpx.post(
    "http://localhost:8000/api/v1/auth/login",
    json={"email": "user@example.com", "password": "password123"}
)
token = response.json()["access_token"]

# Use token for authenticated requests
headers = {"Authorization": f"Bearer {token}"}
projects = httpx.get(
    "http://localhost:8000/api/v1/projects",
    headers=headers
)
```

## 📊 Key Features

### 1. Test Case Management

- Create, update, delete test cases
- Organize test cases with tags and categories
- Support for multiple test types (manual, automated, integration)
- Version history and change tracking

### 2. Test Suite Organization

- Group test cases into reusable test suites
- Hierarchical suite structure
- Dynamic test case selection based on tags

### 3. Asynchronous Test Execution

- Execute test suites asynchronously via Celery
- Real-time execution status updates
- Parallel test execution support
- Retry mechanism for failed tests

### 4. Comprehensive Reporting

- Execution history and trends
- Pass/fail rate analytics
- Test coverage reports
- Export reports (PDF, Excel, JSON)

### 5. Integration Capabilities

- RESTful API for CI/CD integration
- Webhook notifications
- Import/export test cases (JSON, CSV)

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/unit/test_auth.py

# Run integration tests
pytest tests/integration/ -v
```

## 📈 Performance Optimizations

1. **Redis Caching**: Frequently accessed data is cached
2. **Database Indexing**: Optimized queries with proper indexes
3. **Connection Pooling**: Efficient database connection management
4. **Async Operations**: Non-blocking I/O for high concurrency
5. **Pagination**: All list endpoints support pagination

## 🔧 Configuration

Key configuration options in `.env`:

```env
# Application
APP_NAME=TestFlow
DEBUG=false
SECRET_KEY=your-secret-key

# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=testflow
POSTGRES_USER=postgres
POSTGRES_PASSWORD=password

# MongoDB
MONGODB_URL=mongodb://localhost:27017
MONGODB_DB=testflow

# Redis
REDIS_URL=redis://localhost:6379/0

# RabbitMQ
RABBITMQ_URL=amqp://guest:guest@localhost:5672//

# JWT
JWT_SECRET_KEY=your-jwt-secret
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 👤 Author

**Biniyam Gashaw**

- LinkedIn: [Biniyam](https://www.linkedin.com/in/iambiniyam/)

---

⭐ If you find this project useful, please consider giving it a star!
