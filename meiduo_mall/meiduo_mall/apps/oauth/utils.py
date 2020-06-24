from itsdangerous import TimedJSONWebSignatureSerializer
from django.conf import settings
from itsdangerous import BadData


def generate_access_token(openid):

    serializer = TimedJSONWebSignatureSerializer(settings.SECRET_KEY, expires_in=600)
    data = {'openid': openid}
    token = serializer.dumps(data)
    return token.decode()


def check_access_token(access_token):

    serializer = TimedJSONWebSignatureSerializer(settings.SECRET_KEY, expires_in=600)
    try:
        data = serializer.loads(access_token)
    except BadData:
        return None
    return data.get('openid')
