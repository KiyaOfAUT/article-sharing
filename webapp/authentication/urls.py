from django.urls import path, include
from .views import CachedTokenObtainPairView

urlpatterns = [
     path('login/', CachedTokenObtainPairView.as_view(), name='custom-login'),
    path('', include('djoser.urls')), 
    path('', include('djoser.urls.jwt')), 
]
