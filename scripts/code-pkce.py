# generate_pkce.py
import base64
import hashlib
import secrets

# Generate code_verifier (random string)
code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')

# Generate code_challenge (SHA256 hash of verifier)
code_challenge = (
    base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode('utf-8')).digest()).decode('utf-8').rstrip('=')
)

print('PKCE Parameters:')
print('=' * 50)
print(f'code_verifier: {code_verifier}')
print(f'code_challenge: {code_challenge}')
print('=' * 50)
print("\nSave the code_verifier - you'll need it when exchanging the code!")
