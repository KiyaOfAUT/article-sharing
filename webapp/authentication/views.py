from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.views import TokenViewBase
from django.core.cache import cache

class CachedTokenObtainPairView(TokenViewBase):

    _serializer_class = api_settings.TOKEN_OBTAIN_SERIALIZER

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)

        if response.status_code == 200:
            access_token = response.data.get('access')
            refresh_token = response.data.get('refresh')
            user = self.get_user(request.data)
            if access_token and user:
                cache.set(user.id, user, timeout=900)

        return response

    def get_user(self, validated_data):

        from django.contrib.auth import authenticate
        user = authenticate(
            username=validated_data.get("username"),
            password=validated_data.get("password"),
        )
        return user
