from django.urls import path, include
from .views import CachedTokenObtainPairView

urlpatterns = [
     path('auth/login/', CachedTokenObtainPairView.as_view(), name='custom-login'),
    path('auth/', include('djoser.urls')),  # Djoser endpoints for user management
    path('auth/', include('djoser.urls.jwt')),  # JWT-specific endpoints
]
