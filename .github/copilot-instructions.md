# Kiwi Portfolio Management System - AI Developer Guide

## Architecture Overview

This is a **Flask REST API** for portfolio management. The project manages investment portfolios with users, securities, investments, and transactions. A legacy CLI interface exists but is being phased out in favor of a full web application.

### Core Components
- **Models** (`app/models/`): SQLAlchemy ORM entities with eager-loading (`lazy="selectin"`)
- **Services** (`app/service/`): Business logic layer that performs `flush()` but never `commit()`
- **Routes** (`app/routes/`): Flask REST API endpoints responsible for `commit()`

### Database & ORM
- MySQL in dev/prod, SQLite in-memory for tests
- Config switching via `get_config('development'|'production'|'test')`
- All models use `lazy="selectin"` to avoid N+1 queries

## Critical Transaction Management Pattern

**Services FLUSH, Routes COMMIT** - This is the most important rule in the codebase.

### Service Layer Pattern
```python
# In app/service/user_service.py
def create_user(username: str, password: str, firstname: str, lastname: str, balance: float):
    try:
        db.session.add(User(username=username, password=password, ...))
        db.session.flush()  # ✓ Service flushes only
    except Exception as e:
        db.session.rollback()
        raise UnsupportedUserOperationError(f"Failed to create user: {str(e)}")
```

### Route Layer Pattern
```python
# In app/routes/user_routes.py
@app.route('/api/users', methods=['POST'])
def create_user():
    try:
        user_service.create_user(...)  # Service flushes
        db.session.commit()            # ✓ Route commits
        return jsonify({'success': True}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400
```

**Rationale**: This enables **atomic multi-service operations** where routes orchestrate multiple service calls and commit once. See [app/routes/README.md](../app/routes/README.md) for complete patterns.

## Request Validation with Pydantic

All routes use **Pydantic models** for request validation. Define schemas in `app/routes/domain/request_schema.py`:

```python
from pydantic import BaseModel, Field

class CreateUserRequest(BaseModel):
    username: str = Field(min_length=1, max_length=30)
    password: str = Field(min_length=6)
    firstname: str = Field(min_length=1, max_length=30)
    lastname: str = Field(min_length=1, max_length=30)
    balance: float = Field(ge=0.0, default=0.0)
```

**Validation happens automatically** when constructing the model:
```python
# In route:
data = CreateUserRequest(**request.get_json())  # Validates & raises ValidationError if invalid
user_service.create_user(**data.model_dump())   # Pass validated data to service
```

**Benefits**:
- Type coercion (strings → floats automatically)
- Rich constraints (min_length, ge, regex, etc.)
- Detailed error messages with field-level feedback
- Self-documenting API

## Response Schemas with Pydantic

All error responses use **Pydantic models** for consistency. Define schemas in `app/routes/domain/response_schema.py`.

### ErrorResponse Pattern

Every error response must include a `request_id` for traceability:

```python
from flask import g
from app.routes.domain import ErrorResponse

# In any route error condition
error = ErrorResponse(
    error_msg='Descriptive error message',
    request_id=g.get('request_id', 'N/A'),
)
return jsonify(error.model_dump()), <status_code>
```

**Example JSON response:**
```json
{
  "error_msg": "User admin not found",
  "request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

This ensures all errors are consistent and can be traced through logs using the `request_id`.

## Building Flask Routes with Blueprints

Routes are organized using Flask Blueprints following RESTful conventions. See [app/routes/user_routes.py](../app/routes/user_routes.py) for reference implementation.

### Complete Route Module Pattern
```python
# In app/routes/user_routes.py
from flask import Blueprint, g, jsonify, request
import app.service.user_service as user_service
from app.db import db
import app.routes.domain.request_schema as request_schema
from app.routes.domain import ErrorResponse

user_bp = Blueprint('user', __name__)

# GET collection
@user_bp.route('/', methods=['GET'])
def get_all_users():
    users = user_service.get_all_users()
    return jsonify([user.__to_dict__() for user in users]), 200

# GET single resource
@user_bp.route('/<username>', methods=['GET'])
def get_user(username):
    user = user_service.get_user_by_username(username)
    if user is None:
        error = ErrorResponse(
            error_msg=f'User {username} not found',
            request_id=g.get('request_id', 'N/A'),
        )
        return jsonify(error.model_dump()), 404
    return jsonify(user.__to_dict__()), 200

# POST (create)
@user_bp.route('/', methods=['POST'])
def create_user():
    data = request_schema.CreateUserRequest(**request.get_json())
    user_service.create_user(**data.model_dump())
    db.session.commit()  # Route commits!
    return jsonify({"message": "User created successfully"}), 201

# PUT (update)
@user_bp.route('/update-balance', methods=['PUT'])
def update_balance():
    data = request_schema.UpdateUserBalanceRequest(**request.get_json())
    user_service.update_user_balance(**data.model_dump())
    db.session.commit()  # Route commits!
    return jsonify({"message": "User balance updated successfully"}), 200

# DELETE
@user_bp.route('/<username>', methods=['DELETE'])
def delete_user(username):
    user_service.delete_user(username)
    db.session.commit()  # Route commits!
    return jsonify({"message": "User deleted successfully"}), 200
```

### Blueprint Registration
```python
# 1. Export blueprint in app/routes/__init__.py
from .user_routes import user_bp
__all__ = ['user_bp']

# 2. Register in app/__init__.py
from app.routes import user_bp
app.register_blueprint(user_bp, url_prefix='/users')
```

### Route Development Checklist
- ✅ One blueprint per entity
- ✅ Use Pydantic models for request validation
- ✅ Use `ErrorResponse` from `app.routes.domain` for all error responses with `request_id`
- ✅ Routes only handle HTTP concerns (parse request, call service, commit, return response)
- ✅ Business logic stays in service layer
- ✅ Write operations must call `db.session.commit()`
- ✅ Return 404 for missing resources, not empty lists
- ✅ Use RESTful URL patterns (`/`, `/<id>` instead of `/all`, `/create`)
- ✅ Models implement `__to_dict__()` for JSON serialization

## Type Safety with SQLAlchemy

Models use `TYPE_CHECKING` blocks to provide IDE type hints:

```python
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models import Portfolio  # Avoids circular imports

class User(db.Model):
    portfolios: Mapped[List["Portfolio"]] = relationship(...)
    
    if TYPE_CHECKING:
        def __init__(self, *, username: str, password: str, ...) -> None: ...
```

This pattern solves PyLance's inability to infer SQLAlchemy constructors while avoiding circular dependencies.

## Testing Strategy

### Fixtures Architecture
- **Session-scoped `app`**: Creates in-memory DB with seed data (`admin` user, 3 securities)
- **Function-scoped `db_session`**: Wraps each test in a transaction that rolls back
- **Commit mocking**: `db.session.commit()` is monkey-patched to `flush()` in tests

```python
# In tests/conftest.py
@pytest.fixture(scope="function")
def db_session(app, monkeypatch):
    # ... setup transaction
    def mock_commit():
        test_session.flush()  # Commit becomes flush in tests
    monkeypatch.setattr(test_session, 'commit', mock_commit)
    yield test_session
    trans.rollback()  # Ensures test isolation
```

### Running Tests
```bash
pytest                          # All tests
pytest tests/service/          # Service layer only
pytest tests/routes/           # API routes only
pytest -k "test_create_user"   # Specific test pattern
```

## Error Handling Strategy

**Centralized error handling** via Flask error handlers in `app/__init__.py`:

```python
@app.errorhandler(ValidationError)
def validation_error_handler(e):
    app.logger.warning(f"Validation error: {e.errors()}")
    return jsonify({'error': 'Invalid input', 'details': e.errors()}), 400

@app.errorhandler(Exception)
def error_handler(e):
    db.session.rollback()
    app.logger.error(f"Unhandled exception: {str(e)}", exc_info=True)
    return jsonify({'error': str(e)}), 500
```

**Service-specific exceptions**:
- `UnsupportedUserOperationError` (user_service)
- `UnsupportedPortfolioOperationError` (portfolio_service)
- Always wrap service operations and raise with context

**Routes do NOT catch exceptions** - let them bubble to global handlers for consistent error responses.

## Development Workflow

### Setup
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Database
- Development MySQL connection: `kiwi_local:kiwilocaldb@localhost:3306/kiwilocal`
- Configure via `app/config.py`

### Running
```bash
python -m app.main  # Starts Flask dev server
```

## Key Files Reference
- [app/__init__.py](../app/__init__.py): App factory with request logging and error handling
- [app/routes/README.md](../app/routes/README.md): Complete transaction management patterns
- [tests/conftest.py](../tests/conftest.py): Test fixtures and commit mocking strategy
- [app/config.py](../app/config.py): Environment-based configuration

## Common Operations

### Adding a New Service Method
1. Add function to `app/service/<entity>_service.py` that calls `db.session.flush()`
2. Wrap in try/except with appropriate custom exception
3. Create tests in `tests/service/test_<entity>_service.py` using `db_session` fixture
4. If exposing via API, add route that calls `db.session.commit()`

### Adding a New Model
1. Create in `app/models/` with `lazy="selectin"` relationships
2. Add `TYPE_CHECKING` block for constructor type hints
3. Import in `app/models/__init__.py`
4. Update test fixtures in `tests/conftest.py` if needed for seed data
