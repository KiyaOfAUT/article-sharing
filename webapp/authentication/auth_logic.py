from django.core.cache import cache
from rest_framework_simplejwt.authentication import JWTAuthentication

class CachedTokenAuthentication(JWTAuthentication):
    def authenticate(self, request):
        header = self.get_header(request)  
        if not header:
            return None
        token = self.get_raw_token(header)  
        if not token:
            return None
        cached_user = cache.get(token)
        validated_token = self.get_validated_token(token)
        if cached_user:
            return cached_user, validated_token
        user = self.get_user(validated_token)
        cache.set(token, user, timeout=900)  
        return user, validated_token
