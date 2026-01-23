import json

import requests
from flask import current_app


class CognitoClientError(Exception):
    pass


def get_user_info(access_token):
    try:
        region = current_app.config.get('COGNITO_REGION')
        url = f'https://cognito-idp.{region}.amazonaws.com/'
        headers = {
            'Content-Type': 'application/x-amz-json-1.1',
            'X-Amz-Target': 'AWSCognitoIdentityProviderService.GetUser',
        }
        payload = {'AccessToken': access_token}
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        data = response.json()
        attributes = {attr['Name']: attr['Value'] for attr in data['UserAttributes']}

        return {'username': data['Username'], 'attributes': attributes}
    except Exception as e:
        current_app.logger.error(f'Error fetching user info: {str(e)}')
        raise CognitoClientError(f'Failed to fetch user info due to error: {str(e)}')
