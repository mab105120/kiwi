from functools import wraps
from typing import Dict, Optional

import requests
from flask import current_app, jsonify, request
from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTClaimsError, JWTError


class CognitoTokenValidator:
    """Handles AWS Cognito JWT token validation"""

    def __init__(self, region: str, user_pool_id: str, app_client_id: str):
        self.region = region
        self.user_pool_id = user_pool_id
        self.app_client_id = app_client_id
        self.issuer = f'https://cognito-idp.{region}.amazonaws.com/{user_pool_id}'
        self.jwks_url = f'{self.issuer}/.well-known/jwks.json'
        self._jwks = None

    def _get_jwks(self) -> Dict:
        """Fetch JSON Web Key Set from Cognito (cached)"""
        if self._jwks is None:
            response = requests.get(self.jwks_url)
            response.raise_for_status()
            self._jwks = response.json()
        return self._jwks

    def _get_signing_key(self, token: str) -> Optional[Dict]:
        """Extract the signing key from JWKS that matches the token's key ID"""
        try:
            # Decode header without verification to get the key ID (kid)
            header = jwt.get_unverified_header(token)
            kid = header.get('kid')

            if not kid:
                return None

            # Find the matching key in JWKS
            jwks = self._get_jwks()
            for key in jwks.get('keys', []):
                if key.get('kid') == kid:
                    return key

            return None
        except JWTError:
            return None

    def validate_token(self, token: str) -> Dict:
        """
        Validate the JWT token and return decoded claims

        Args:
            token: The JWT access token

        Returns:
            Dict containing the token claims

        Raises:
            Exception: If token validation fails
        """
        # Get the signing key
        signing_key = self._get_signing_key(token)
        if not signing_key:
            raise Exception('Unable to find matching signing key')

        try:
            # Decode and validate the token
            claims = jwt.decode(
                token,
                signing_key,
                algorithms=['RS256'],
                audience=self.app_client_id,  # Validates the token was issued for this app
                issuer=self.issuer,  # Validates the token came from this user pool
                options={
                    'verify_signature': True,
                    'verify_exp': True,  # Verify expiration
                    'verify_aud': True,  # Verify audience
                    'verify_iss': True,  # Verify issuer
                },
            )

            # Additional validation: check token_use claim
            # Access tokens should have token_use = "access"
            if claims.get('token_use') != 'access':
                current_app.logger.warning(f'Invalid token_use: {claims.get("token_use")}')
                raise Exception(f'Invalid token_use: {claims.get("token_use")}')

            return claims

        except ExpiredSignatureError:
            current_app.logger.warning('Token has expired')
            raise Exception('Token has expired')
        except JWTClaimsError as e:
            current_app.logger.warning(f'Invalid token claims: {str(e)}')
            raise Exception(f'Invalid token claims: {str(e)}')
        except JWTError as e:
            current_app.logger.warning(f'Token validation failed: {str(e)}')
            raise Exception(f'Token validation failed: {str(e)}')


def get_token_from_header() -> Optional[str]:
    """Extract token from Authorization header"""
    auth_header = request.headers.get('Authorization', '')

    if not auth_header:
        return None

    # Expected format: "Bearer <token>"
    parts = auth_header.split()

    if len(parts) != 2 or parts[0].lower() != 'bearer':
        return None

    return parts[1]
