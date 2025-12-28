from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.utils import timezone
from shop.models import Product, ProductVariant, Category
from analytics.models import ProductDailyMetrics
from account.models import UserAccount as User
from decimal import Decimal


class AnalyticsAPITest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            phone_number="123456789", password="password", is_staff=True
        )
        self.category = Category.objects.create(name="Test Category")
        self.product = Product.objects.create(
            name="Test Product", category=self.category, user=self.user
        )
        self.variant = ProductVariant.objects.create(
            product=self.product, price=100, cost=50, stock=10
        )
        self.yesterday = timezone.now().date() - timezone.timedelta(days=1)
        self.metrics = ProductDailyMetrics.objects.create(
            product=self.product,
            date=self.yesterday,
            units_sold=2,
            revenue=Decimal("200.00"),
            profit=Decimal("100.00"),
        )
        self.client.force_authenticate(user=self.user)

    def test_overview_endpoint(self):
        url = reverse("analytics-overview")
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_revenue"], Decimal("200.00"))
        self.assertEqual(response.data["total_profit"], Decimal("100.00"))
        self.assertEqual(response.data["total_units_sold"], 2)

    def test_products_endpoint(self):
        url = reverse("analytics-products")
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["product_name"], "Test Product")
        self.assertEqual(response.data[0]["total_revenue"], "200.00")
