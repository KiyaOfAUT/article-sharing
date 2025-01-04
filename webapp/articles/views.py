from rest_framework.response import Response
from django.core.cache import cache
from rest_framework import status
from .serializers import ArticleSerializer
from .models import Article, ArticleRating
from rest_framework import viewsets
from django.db.models.signals import post_save
from django.dispatch import receiver
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from celery import shared_task
import numpy as np

@shared_task
def process_tier1_ratings():
    keys = cache.keys('tier1_ratings_batch_*')
    for key in keys:
        article_id = key.split('_')[-1]
        data = cache.get(key, {"create": [], "update": []})
        cache.delete(key)

        create_ratings = list(map(int, data["create"]))
        update_ratings = list(map(int, data["update"]))

        article = Article.objects.filter(pk=article_id).first()
        if article:
            article.sum_of_rating += sum(create_ratings)
            article.count_of_rates += len(create_ratings)
            article.sum_of_rating += sum(update_ratings)
            article.save()


@shared_task
def process_tier2_ratings():
    keys = cache.keys('tier2_ratings_batch_*')
    for key in keys:
        article_id = key.split('_')[-1]
        data = cache.get(key, {"create": [], "update": []})
        cache.delete(key)

        create_ratings = list(map(int, data["create"]))
        update_ratings = list(map(int, data["update"]))

        article = Article.objects.filter(pk=article_id).first()
        if article:
            current_avg = article.sum_of_rating / article.count_of_rates if article.count_of_rates else 0

            # Handle newly created ratings
            if create_ratings:
                batch_total = sum(create_ratings)
                batch_count = len(create_ratings)
                batch_avg = batch_total / batch_count
                batch_variance = np.var(create_ratings)
                weight = 1 / (1 + abs(batch_avg - current_avg) + batch_variance)
                weighted_total = batch_total * weight

                article.sum_of_rating += weighted_total
                article.count_of_rates += batch_count
                article.save()
                current_avg = article.sum_of_rating / article.count_of_rates

            # Handle updated ratings (no count increment)
            if update_ratings:
                batch_total = sum(update_ratings)
                batch_count = len(update_ratings)
                batch_avg = batch_total / batch_count
                batch_variance = np.var(update_ratings)
                weight = 1 / (1 + abs(batch_avg - current_avg) + batch_variance)
                weighted_total = batch_total * weight

                article.sum_of_rating += weighted_total
                article.save()


@shared_task
def process_tier3_ratings():
    keys = cache.keys('tier3_ratings_batch_*')
    for key in keys:
        article_id = key.split('_')[-1]
        data = cache.get(key, {"create": [], "update": []})
        cache.delete(key)

        create_ratings = list(map(int, data["create"]))
        update_ratings = list(map(int, data["update"]))

        article = Article.objects.filter(pk=article_id).first()
        if article:
            current_avg = article.sum_of_rating / article.count_of_rates if article.count_of_rates else 0

            # Handle newly created ratings (Bayesian + smoothing)
            if create_ratings:
                batch_total = sum(create_ratings)
                batch_count = len(create_ratings)
                batch_avg = batch_total / batch_count
                batch_variance = np.var(create_ratings)
                prior_weight = 500
                weight = 1 / (1 + abs(batch_avg - current_avg) + batch_variance)

                smoothed_total = (
                    (current_avg * prior_weight + batch_avg * batch_count * weight)
                    / (prior_weight + batch_count * weight)
                ) * batch_count * weight

                article.sum_of_rating += smoothed_total
                article.count_of_rates += batch_count
                article.save()
                current_avg = article.sum_of_rating / article.count_of_rates

            # Handle updated ratings (no rate count increment)
            if update_ratings:
                batch_total = sum(update_ratings)
                batch_count = len(update_ratings)
                batch_avg = batch_total / batch_count
                batch_variance = np.var(update_ratings)
                prior_weight = 500
                weight = 1 / (1 + abs(batch_avg - current_avg) + batch_variance)

                smoothed_total = (
                    (current_avg * prior_weight + batch_avg * batch_count * weight)
                    / (prior_weight + batch_count * weight)
                ) * batch_count * weight

                article.sum_of_rating += smoothed_total
                article.save()


        
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
        current_rating = None
        if rating is None or not (0 <= rating <= 5):
            return Response({"error": "Invalid rating. Must be an integer between 1 and 5."}, status=status.HTTP_400_BAD_REQUEST)
        user_rating_obj = ArticleRating.objects.filter(user=request.user, article_id=pk).first()
        if not user_rating_obj:
            user_rating_obj = ArticleRating(user=request.user, article_id=pk, rating=rating)
            user_rating_obj.save()
        else:
            current_rating = user_rating_obj.rating
            user_rating_obj.rating = rating
            user_rating_obj.save()
        cache_key = f'user_{request.user.id}_ratings'
        user_ratings = cache.get(cache_key, {})
        user_rating_cached = user_ratings.get(pk)
        if user_rating_cached is None:
            if len(user_ratings) > 10:
                del user_ratings[list(user_ratings.keys())[0]]
                user_ratings[pk] = rating
                cache.set(cache_key, user_ratings, timeout=60*15)
        article = cache.get(f'article_{pk}')
        article_object = None
        if not article:
            try:
                article_object = Article.objects.get(pk=pk)
                article = ArticleSerializer(article_object).data
                cache.set(f'article_{pk}', article, timeout=60*2)
            except Article.DoesNotExist:
                return Response({"error": "Article not found"}, status=status.HTTP_404_NOT_FOUND)
        if article["number_of_user_rates"] < 100:
            if not article_object:
                article_object = Article.objects.get(pk=pk)
            if current_rating:
                article_object.sum_of_rating -= current_rating
                article_object.sum_of_rating += rating
            else:
                article_object.sum_of_rating += rating
                article_object.count_of_rates += 1
            article_object.save()
        elif 100 <= article["number_of_user_rates"] < 1000:
            cache_key = f'tier1_ratings_batch_{pk}'
            existing_ratings = cache.get(cache_key, {"create":[], "update":[]})
            if current_rating:
                existing_ratings["update"].append(rating-current_rating)
            else:
                existing_ratings["create"].append(rating)
            cache.set(cache_key, existing_ratings, 60*5)
        elif 1000 <= article["number_of_user_rates"] < 10000:
            cache_key = f'tier2_ratings_batch_{pk}'
            existing_ratings = cache.get(cache_key, {"create":[], "update":[]})
            if current_rating:
                existing_ratings["update"].append(rating-current_rating)
            else:
                existing_ratings["create"].append(rating)
            cache.set(cache_key, existing_ratings, 60*10)
        else:
            cache_key = f'tier3_ratings_batch_{pk}'
            existing_ratings = cache.get(cache_key, {"create":[], "update":[]})
            if current_rating:
                existing_ratings["update"].append(rating-current_rating)
            else:
                existing_ratings["create"].append(rating)
            cache.set(cache_key, existing_ratings, 60*20)

        return Response({"message": "Rating submitted successfully"}, status=status.HTTP_200_OK)

    def put(self, request, pk=None):
        return self.post(request, pk)
