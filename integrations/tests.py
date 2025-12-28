from django.test import TestCase, RequestFactory
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status
from account.factories import UserFactory
from shop.factories import ProductFactory, ProductVariantFactory
from .models import IntegrationSettings
from .services import generate_product_feed_data


class IntegrationServiceTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.product1 = ProductFactory()
        self.variant1 = ProductVariantFactory(product=self.product1, stock=10)

        self.product2 = ProductFactory()
        self.variant2 = ProductVariantFactory(
            product=self.product2, stock=0
        )  # Out of stock

        self.product3 = ProductFactory(deleted_at=timezone.now())  # Soft-deleted
        self.variant3 = ProductVariantFactory(product=self.product3, stock=5)

    def test_generate_product_feed_data(self):
        request = self.factory.get("/")
        feed_data = generate_product_feed_data(request)

        self.assertEqual(len(feed_data), 1)
        self.assertEqual(feed_data[0]["id"], self.variant1.sku)


class IntegrationFeedTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.settings = IntegrationSettings.load()
        self.product = ProductFactory()
        ProductVariantFactory(product=self.product, stock=5)

    def test_feed_disabled(self):
        self.settings.torob_enabled = False
        self.settings.save()
        url = reverse("integrations:torob_feed") + f"?token={self.settings.feed_token}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_feed_invalid_token(self):
        self.settings.torob_enabled = True
        self.settings.save()
        url = reverse("integrations:torob_feed") + "?token=invalid-token"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_feed_success(self):
        self.settings.torob_enabled = True
        self.settings.save()
        url = reverse("integrations:torob_feed") + f"?token={self.settings.feed_token}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "application/xml")
        self.assertContains(response, f"<id>{self.product.variants.first().sku}</id>")


class IntegrationToggleAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin_user = UserFactory(is_staff=True, is_superuser=True)
        self.normal_user = UserFactory()
        self.settings = IntegrationSettings.load()
        self.url = reverse("integrations:toggle_integration")

    def test_toggle_permission_denied_for_anonymous(self):
        response = self.client.post(self.url, {"name": "torob", "enabled": True})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_toggle_permission_denied_for_normal_user(self):
        self.client.force_authenticate(user=self.normal_user)
        response = self.client.post(self.url, {"name": "torob", "enabled": True})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_toggle_success_for_admin(self):
        self.client.force_authenticate(user=self.admin_user)
        self.assertFalse(self.settings.torob_enabled)

        response = self.client.post(self.url, {"name": "torob", "enabled": True})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.settings.refresh_from_db()
        self.assertTrue(self.settings.torob_enabled)

    def test_toggle_invalid_data(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.post(
            self.url, {"name": "invalid_platform", "enabled": True}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
