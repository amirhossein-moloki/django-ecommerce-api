import pytest
from rest_framework.test import APIClient
from rest_framework import status
from django.urls import reverse
from account.models import UserAccount, Address
from account.factories import UserAccountFactory, AddressFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user():
    return UserAccountFactory()


@pytest.fixture
def another_user():
    return UserAccountFactory()


class TestAddressViewSet:
    def test_unauthenticated_user_cannot_access_addresses(self, api_client):
        url = reverse("auth:address-list")
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_addresses(self, api_client, user):
        api_client.force_authenticate(user=user)
        AddressFactory.create_batch(3, user=user)
        url = reverse("auth:address-list")
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 3

    def test_create_address(self, api_client, user):
        api_client.force_authenticate(user=user)
        url = reverse("auth:address-list")
        data = {
            "province": "Tehran",
            "city": "Tehran",
            "postal_code": "1234567890",
            "full_address": "123 Azadi St.",
            "receiver_name": "Test User",
            "receiver_phone": "09123456789",
        }
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_201_CREATED
        assert Address.objects.filter(user=user).count() == 1
        assert response.data["province"] == "Tehran"

    def test_retrieve_address(self, api_client, user):
        api_client.force_authenticate(user=user)
        address = AddressFactory(user=user)
        url = reverse("auth:address-detail", kwargs={"pk": address.pk})
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == address.id

    def test_update_address(self, api_client, user):
        api_client.force_authenticate(user=user)
        address = AddressFactory(user=user)
        url = reverse("auth:address-detail", kwargs={"pk": address.pk})
        data = {"city": "Karaj"}
        response = api_client.patch(url, data)
        assert response.status_code == status.HTTP_200_OK
        address.refresh_from_db()
        assert address.city == "Karaj"

    def test_delete_address(self, api_client, user):
        api_client.force_authenticate(user=user)
        address = AddressFactory(user=user)
        url = reverse("auth:address-detail", kwargs={"pk": address.pk})
        response = api_client.delete(url)
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Address.objects.filter(pk=address.pk).exists()

    def test_user_cannot_access_another_users_address(
        self, api_client, user, another_user
    ):
        api_client.force_authenticate(user=user)
        address = AddressFactory(user=another_user)
        url = reverse("auth:address-detail", kwargs={"pk": address.pk})
        response = api_client.get(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_set_default_address(self, api_client, user):
        api_client.force_authenticate(user=user)
        address1 = AddressFactory(user=user, is_default=True)
        address2 = AddressFactory(user=user, is_default=False)
        url = reverse("auth:address-set-default", kwargs={"pk": address2.pk})
        response = api_client.post(url)
        assert response.status_code == status.HTTP_200_OK
        address1.refresh_from_db()
        address2.refresh_from_db()
        assert not address1.is_default
        assert address2.is_default

    def test_creating_new_default_address_unsets_old_one(self, api_client, user):
        api_client.force_authenticate(user=user)
        address1 = AddressFactory(user=user, is_default=True)
        url = reverse("auth:address-list")
        data = {
            "province": "Khorasan",
            "city": "Mashhad",
            "postal_code": "9876543210",
            "full_address": "456 Ferdowsi St.",
            "receiver_name": "New Receiver",
            "receiver_phone": "09150000000",
            "is_default": True,
        }
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_201_CREATED
        address1.refresh_from_db()
        new_address = Address.objects.get(pk=response.data["id"])
        assert not address1.is_default
        assert new_address.is_default
