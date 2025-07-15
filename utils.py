import base64

def encode_id(code):
  return base64.urlsafe_b64encode(code.encode()).decode().rstrip("=")

def decode_id(token):
  return base64.urlsafe_b64decode(token + "=" * (-len(token) % 4)).decode()
