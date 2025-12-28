from django.test import TestCase
from django.utils import timezone
from shop.models import Product, ProductVariant, Category
from orders.models import Order, OrderItem
from analytics.models import ProductDailyMetrics
from analytics.tasks import populate_daily_metrics
from account.models import UserAccount as User


class PopulateDailyMetricsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            phone_number="123456789", password="password"
        )
        self.category = Category.objects.create(name="Test Category")
        self.product = Product.objects.create(
            name="Test Product", category=self.category, user=self.user
        )
        self.variant = ProductVariant.objects.create(
            product=self.product, price=100, cost=50, stock=10
        )
        self.order = Order.objects.create(user=self.user)
        self.order_item = OrderItem.objects.create(
            order=self.order, variant=self.variant, price=100, quantity=2
        )
        # Manually set the order date to yesterday for the test
        self.order.order_date = timezone.now() - timezone.timedelta(days=1)
        self.order.save()

    def test_populate_daily_metrics(self):
        populate_daily_metrics()
        yesterday = timezone.now().date() - timezone.timedelta(days=1)
        metrics = ProductDailyMetrics.objects.get(
            product=self.product, date=yesterday
        )
        self.assertEqual(metrics.units_sold, 2)
        self.assertEqual(metrics.revenue, 200)
        self.assertEqual(metrics.profit, 100)
