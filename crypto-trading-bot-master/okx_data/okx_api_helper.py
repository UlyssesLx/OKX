import sys
import json
import requests
import hmac
import base64
import hashlib
from datetime import datetime
import os

API_KEY = os.environ.get('OKX_API_KEY', '')
API_SECRET = os.environ.get('OKX_SECRET_KEY', '')
PASSPHRASE = os.environ.get('OKX_PASSPHRASE', '')
BASE_URL = 'https://www.okx.com'

def sign(timestamp, method, path, body=''):
    message = timestamp + method + path + body
    mac = hmac.new(
        API_SECRET.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    )
    return base64.b64encode(mac.digest()).decode('utf-8')

def request(path, method='GET', body=None):
    timestamp = datetime.utcnow().isoformat(timespec='milliseconds') + 'Z'
    body_str = json.dumps(body, separators=(',', ':')) if body else ''
    
    headers = {
        'OK-ACCESS-KEY': API_KEY,
        'OK-ACCESS-SIGN': sign(timestamp, method, path, body_str),
        'OK-ACCESS-TIMESTAMP': timestamp,
        'OK-ACCESS-PASSPHRASE': PASSPHRASE,
        'Content-Type': 'application/json'
    }
    
    url = BASE_URL + path
    
    try:
        if method == 'GET':
            response = requests.get(url, headers=headers, timeout=30)
        elif method == 'POST':
            response = requests.post(url, headers=headers, json=body, timeout=30)
        else:
            response = requests.request(method, url, headers=headers, timeout=30)
        
        return response.json()
    except Exception as e:
        return {'error': str(e)}

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(json.dumps({'error': 'Usage: python okx_api_helper.py <path> [method] [body]'}))
        sys.exit(1)
    
    path = sys.argv[1]
    method = sys.argv[2] if len(sys.argv) > 2 else 'GET'
    body = json.loads(sys.argv[3]) if len(sys.argv) > 3 else None
    
    result = request(path, method, body)
    print(json.dumps(result))
