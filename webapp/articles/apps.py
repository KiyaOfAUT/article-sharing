from django.apps import AppConfig


class ArticlesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'articles'

    def ready(self):
        from articles.views import process_tier1_ratings, process_tier2_ratings, process_tier3_ratings
        from django_celery_beat.models import PeriodicTask, IntervalSchedule

        intervals = {
            '5_minutes': {'every': 5, 'period': IntervalSchedule.MINUTES},
            '15_minutes': {'every': 15, 'period': IntervalSchedule.MINUTES},
            '20_minutes': {'every': 20, 'period': IntervalSchedule.MINUTES},
        }

        for key, params in intervals.items():
            intervals[key]['instance'], _ = IntervalSchedule.objects.get_or_create(
                every=params['every'],
                period=params['period'],
            )

        tasks = [
            {
                'name': 'Process Tier 1 Ratings',
                'task': 'articles.views.process_tier1_ratings',
                'interval': intervals['5_minutes']['instance'],
            },
            {
                'name': 'Process Tier 2 Ratings',
                'task': 'articles.views.process_tier2_ratings',
                'interval': intervals['15_minutes']['instance'],
            },
            {
                'name': 'Process Tier 3 Ratings',
                'task': 'articles.views.process_tier3_ratings',
                'interval': intervals['20_minutes']['instance'],
            },
        ]

        for task in tasks:
            PeriodicTask.objects.get_or_create(
                name=task['name'],
                defaults={
                    'task': task['task'],
                    'interval': task['interval'],
                },
            )
