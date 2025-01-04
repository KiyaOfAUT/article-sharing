from rest_framework.response import Response
from django.core.cache import cache
from rest_framework import status
from .serializers import ArticleSerializer
from .models import Article, ArticleRating
from rest_framework import viewsets
from django.db.models.signals import post_save
from django.dispatch import receiver
from rest_framework import mixins, generics
from rest_framework.permissions import IsAuthenticated

@receiver(post_save, sender=Article)
def invalidate_article_cache(sender, instance, **kwargs):
    cache.delete(f'article_{instance.pk}')

class ArticleViewSet(viewsets.ViewSet):
    permission_classes = []

    def list(self, request):
        articles = cache.get('posts')
        if not articles:
            article_objects = Article.objects.all()
            serializer = ArticleSerializer(article_objects, many=True)
            articles = serializer.data
            cache.set('posts', articles, timeout=60*1)
        return Response(articles, status=status.HTTP_200_OK)

    def retrieve(self, request, pk=None):
        article = cache.get(f'article_{pk}')
        if not article:
            try:
                article_object = Article.objects.get(pk=pk)
                article = ArticleSerializer(article_object).data
                cache.set(f'article_{pk}', article, timeout=60*2)
            except Article.DoesNotExist:
                return Response({"error": "Article not found"}, status=status.HTTP_404_NOT_FOUND)
        user_rating = None
        if request.user.is_authenticated:
            cache_key = f'user_{request.user.id}_ratings'
            user_ratings = cache.get(cache_key, {})
            user_rating = user_ratings.get(pk)
            if user_rating is None:
                user_rating_obj = ArticleRating.objects.filter(user=request.user, article_id=pk).first()
                user_rating = user_rating_obj.rating if user_rating_obj else None
                if len(user_ratings) > 10:
                    del user_ratings[list(user_ratings.keys())[0]]
                user_ratings[pk] = user_rating
                cache.set(cache_key, user_ratings, timeout=60*15)
        return Response({"article": article, "user_rating": user_rating}, status=status.HTTP_200_OK)

class RateArticleView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk=None):
        rating = int(request.data.get('rating'))
        if rating is None or not (0 <= rating <= 5):
            return Response({"error": "Invalid rating. Must be an integer between 1 and 5."}, status=status.HTTP_400_BAD_REQUEST)
        user_rating, created = ArticleRating.objects.update_or_create(
            user=request.user,
            article_id=pk,
            defaults={'rating': rating}
        )
        cache_key = f'user_{request.user.id}_ratings'
        user_ratings = cache.get(cache_key, {})
        user_rating_cached = user_ratings.get(pk)
        if user_rating_cached is None:
            if len(user_ratings) > 10:
                del user_ratings[list(user_ratings.keys())[0]]
            user_ratings[pk] = rating
            cache.set(cache_key, user_ratings, timeout=60*15)

        # Update the article's rating (to be implemented)
        
        return Response({"message": "Rating submitted successfully"}, status=status.HTTP_200_OK)

    def put(self, request, pk=None):
        return self.post(request, pk)
