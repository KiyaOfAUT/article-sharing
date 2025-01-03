from django.urls import path
from .views import MockView

urlpatterns = [
    path('mock/', MockView.as_view(), name='mock_view'),
]