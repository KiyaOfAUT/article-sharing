from django.db import models
import uuid
from django.contrib.auth.models import User

class Article(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    description = models.TextField()
    sum_of_rating = models.IntegerField(default=0)
    count_of_rates = models.IntegerField(default=0)

    def __str__(self):
        return self.title

class ArticleRating(models.Model):
    article = models.ForeignKey(Article, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.IntegerField()

    class Meta:
        unique_together = ('article', 'user')
        indexes = [
            models.Index(fields=['user', 'article']),
        ]

    def __str__(self):
        return f'{self.user.username} rated {self.article.title} with {self.rating}'