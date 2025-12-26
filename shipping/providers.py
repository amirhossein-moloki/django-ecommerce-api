import requests
from abc import ABC, abstractmethod
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class ShippingProviderError(Exception):
    """Custom exception for shipping provider errors."""

    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.status_code = status_code


class ShippingProvider(ABC):
    @abstractmethod
    def create_shipment(self, order):
        pass

    @abstractmethod
    def get_shipment_tracking(self, parcel_no):
        pass

    @abstractmethod
    def cancel_shipment(self, parcel_no):
        pass


class PostexShippingProvider(ShippingProvider):
    def __init__(self):
        self.api_key = getattr(settings, "POSTEX_API_KEY", None)
        if not self.api_key:
            raise ValueError("POSTEX_API_KEY is not configured in settings.")
        self.api_url = "https://api.postex.ir"

    def _get_headers(self):
        return {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
        }

    def _handle_response(self, response, context_message):
        if 200 <= response.status_code < 300:
            try:
                return response.json()
            except ValueError:
                # Handle cases where the response is successful but not valid JSON
                raise ShippingProviderError(
                    f"{context_message}: Malformed JSON response",
                    status_code=response.status_code,
                )

        try:
            error_data = response.json()
        except ValueError:
            error_data = response.text

        logger.error(
            f"{context_message} | Status: {response.status_code}, Response: {error_data}"
        )
        raise ShippingProviderError(
            f"{context_message}: {error_data}", status_code=response.status_code
        )

    def create_shipment(self, order):
        total_weight = int(
            sum(
                item.variant.product.weight * item.quantity
                for item in order.items.all()
            )
        )
        max_length = max(item.variant.product.length for item in order.items.all())
        max_width = max(item.variant.product.width for item in order.items.all())
        max_height = max(item.variant.product.height for item in order.items.all())
        is_fragile = any(item.variant.product.is_fragile for item in order.items.all())
        is_liquid = any(item.variant.product.is_liquid for item in order.items.all())

        parcels = [
            {
                "to": {
                    "contact": {
                        "name": order.address.receiver_name,
                        "mobile": order.address.receiver_phone,
                    },
                    "location": {
                        "address": order.address.full_address,
                        "city_code": order.address.city_code,
                        "postal_code": order.address.postal_code,
                    },
                },
                "parcel_items": [
                    {
                        "name": item.product_name,
                        "count": item.quantity,
                        "amount": int(item.price),
                    }
                    for item in order.items.all()
                ],
                "parcel_properties": {
                    "total_weight": total_weight,
                    "total_value": int(order.total_payable),
                    "length": int(max_length),
                    "width": int(max_width),
                    "height": int(max_height),
                    "is_fragile": is_fragile,
                    "is_liquid": is_liquid,
                },
            }
        ]
        data = {"collection_type": "pick_up", "parcels": parcels}

        url = f"{self.api_url}/api/v1/parcels/bulk"
        context = f"Error creating Postex shipment for order {order.order_id}"
        logger.info(
            f"Creating Postex shipment for order {order.order_id} with data: {data}"
        )

        try:
            response = requests.post(
                url, json=data, headers=self._get_headers(), timeout=15
            )
            return self._handle_response(response, context)
        except requests.exceptions.RequestException as e:
            logger.error(f"{context}: {e}")
            raise ShippingProviderError(f"{context}: {e}")

    def get_shipment_tracking(self, parcel_no):
        url = f"{self.api_url}/api/v1/tracking/events/{parcel_no}"
        context = f"Error getting Postex tracking for parcel_no {parcel_no}"
        logger.info(f"Getting Postex shipment tracking for parcel_no {parcel_no}")

        try:
            response = requests.get(url, headers=self._get_headers(), timeout=10)
            return self._handle_response(response, context)
        except requests.exceptions.RequestException as e:
            logger.error(f"{context}: {e}")
            raise ShippingProviderError(f"{context}: {e}")

    def get_shipping_quote(self, order):
        total_weight = int(
            sum(
                item.variant.product.weight * item.quantity
                for item in order.items.all()
            )
        )
        max_length = max(item.variant.product.length for item in order.items.all())
        max_width = max(item.variant.product.width for item in order.items.all())
        max_height = max(item.variant.product.height for item in order.items.all())

        parcels = [
            {
                "to_city_code": order.address.city_code,
                "total_weight": total_weight,
                "total_value": int(order.total_payable),
                "length": int(max_length),
                "width": int(max_width),
                "height": int(max_height),
            }
        ]
        data = {
            "collection_type": "pick_up",
            "from_city_code": settings.POSTEX_FROM_CITY_CODE,
            "parcels": parcels,
        }

        url = f"{self.api_url}/api/v1/shipping/quotes"
        context = f"Error getting Postex shipping quote for order {order.order_id}"
        logger.info(
            f"Getting Postex shipping quote for order {order.order_id} with data: {data}"
        )

        try:
            response = requests.post(
                url, json=data, headers=self._get_headers(), timeout=10
            )
            return self._handle_response(response, context)
        except requests.exceptions.RequestException as e:
            logger.error(f"{context}: {e}")
            raise ShippingProviderError(f"{context}: {e}")

    def cancel_shipment(self, parcel_no):
        url = f"{self.api_url}/api/v1/parcels/{parcel_no}"
        context = f"Error canceling Postex shipment for parcel_no {parcel_no}"
        logger.info(f"Canceling Postex shipment for parcel_no {parcel_no}")

        try:
            response = requests.delete(url, headers=self._get_headers(), timeout=10)
            return self._handle_response(response, context)
        except requests.exceptions.RequestException as e:
            logger.error(f"{context}: {e}")
            raise ShippingProviderError(f"{context}: {e}")

    def get_cities(self):
        url = f"{self.api_url}/api/v1/locality/cities/all"
        context = "Error getting Postex city list"
        logger.info("Getting Postex city list")

        try:
            response = requests.get(url, headers=self._get_headers(), timeout=10)
            return self._handle_response(response, context)
        except requests.exceptions.RequestException as e:
            logger.error(f"{context}: {e}")
            raise ShippingProviderError(f"{context}: {e}")
