from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ArticleViewSet, RateArticleView

router = DefaultRouter()
router.register(r'', ArticleViewSet, basename='article')

urlpatterns = [
    path('', include(router.urls)),
    path('<uuid:pk>/rate/', RateArticleView.as_view(), name='rate-article'),
]