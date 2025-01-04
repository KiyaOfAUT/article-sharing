from django.core.cache import cache
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.exceptions import InvalidToken
from django.utils.translation import gettext_lazy as _


class CachedTokenAuthentication(JWTAuthentication):
    def authenticate(self, request):
        header = self.get_header(request)  
        if not header:
            return None
        token = self.get_raw_token(header)  
        if not token:
            return None
        validated_token = self.get_validated_token(token)
        try:
            user_id = validated_token[api_settings.USER_ID_CLAIM]
        except KeyError:
            raise InvalidToken(_("Token contained no recognizable user identification"))
        cached_user = cache.get(user_id)
        if cached_user:
            return cached_user, validated_token
        user = self.get_user(validated_token)
        cache.set(user_id, user, timeout=900)  
        return user, validated_token
