from django.core.management.base import BaseCommand, CommandError
from client.client import Client
from task.models import Task


class Command(BaseCommand):
    help = 'Test'

    def add_arguments(self, parser):
        pass
        # parser.add_argument('poll_ids', nargs='+', type=int)

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS(Task.objects.all()))
        self.stdout.write(self.style.SUCCESS('done'))
