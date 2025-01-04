from rest_framework import serializers
from .models import Article

class ArticleSerializer(serializers.ModelSerializer):
    average_rating = serializers.SerializerMethodField()
    number_of_user_rates = serializers.SerializerMethodField()

    class Meta:
        model = Article
        fields = ['id', 'title', 'description', 'average_rating', 'number_of_user_rates']

    def get_average_rating(self, obj):
        if obj.count_of_rates > 0:
            return obj.sum_of_rating / obj.count_of_rates
        return 0

    def get_number_of_user_rates(self, obj):
        return obj.count_of_rates