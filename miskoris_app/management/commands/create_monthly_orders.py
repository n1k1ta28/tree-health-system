from django.core.management.base import BaseCommand
from django.utils import timezone
from miskoris_app.models import Subscription, Order

class Command(BaseCommand):
    help = 'Create monthly orders for active subscriptions'

    def handle(self, *args, **options):
        today = timezone.now().date()
        # Get all active subscriptions where the paid_until date is in the future
        active_subscriptions = Subscription.objects.filter(is_active=True, paid_until__gte=today)
        
        for subscription in active_subscriptions:
            # Calculate the first day of the current month
            first_day_of_month = today.replace(day=1)
            # Check if an order already exists for this subscription this month
            existing_order = Order.objects.filter(
                forest=subscription.forest,
                created_at__gte=first_day_of_month,
                is_subscription_order=True
            ).exists()
            
            if not existing_order:
                # Create a new order if none exists for this month
                Order.objects.create(
                    forest=subscription.forest,
                    worker=None,  
                    created_at=timezone.now(),
                    status='in_progress',
                    is_subscription_order=True
                )
                self.stdout.write(self.style.SUCCESS(f'Created order for subscription {subscription.id}'))
