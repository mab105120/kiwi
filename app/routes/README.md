# Route Development Guidelines

## Transaction Management Pattern

All routes that modify data MUST commit transactions:

### Pattern for Write Operations

```python
@app.route('/api/users', methods=['POST'])
def create_user():
    try:
        data = request.get_json()
        user_service.create_user(...)  # Service calls flush()
        db.session.commit()            # Route commits transaction
        return jsonify({'success': True}), 201
    except Exception as e:
        db.session.rollback()         # Explicit rollback (also in error handler)
        return jsonify({'error': str(e)}), 400
```

### Pattern for Read Operations

```python
@app.route('/api/users/<username>', methods=['GET'])
def get_user(username):
    # No commit needed for reads
    user = user_service.get_user_by_username(username)
    if not user:
        return jsonify({'error': 'Not found'}), 404
    return jsonify(user.to_dict()), 200
```

### Pattern for multi-service operations

```python
@app.route('/api/transfer', methods=['POST'])
def transfer_funds():
    try:
        # All services flush, none commit
        portfolio_service.sell_investment(...)
        user_service.update_balance(...)
        portfolio_service.buy_investment(...)
        
        # Single commit for entire operation (atomic)
        db.session.commit()
        return jsonify({'success': True}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400
```
