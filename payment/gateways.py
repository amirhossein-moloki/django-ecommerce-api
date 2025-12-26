import requests
from abc import ABC, abstractmethod
from django.conf import settings
import logging
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class PaymentGateway(ABC):
    @abstractmethod
    def create_payment_request(self, amount, order_id, callback_url):
        pass

    @abstractmethod
    def verify_payment(self, payload_or_authority):
        pass


class ZibalGatewayError(Exception):
    """Custom exception for Zibal gateway errors."""

    pass


class ZibalGateway(PaymentGateway):
    def __init__(self):
        self.merchant_id = getattr(settings, "ZIBAL_MERCHANT_ID", None)
        self.api_url = "https://gateway.zibal.ir/v1"

        # Configure retry mechanism
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "POST", "OPTIONS"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session = requests.Session()
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def create_payment_request(self, amount, order_id, callback_url):
        headers = {"Content-Type": "application/json"}
        data = {
            "merchant": self.merchant_id,
            "amount": amount,
            "orderId": str(order_id),
            "callbackUrl": callback_url,
        }
        logger.info(f"Creating Zibal payment request for order {order_id}: {data}")
        try:
            response = self.session.post(
                f"{self.api_url}/request", json=data, headers=headers, timeout=5
            )
            response.raise_for_status()
            response_data = response.json()
            logger.info(
                f"Zibal payment request response for order {order_id}: {response_data}"
            )
            if response_data.get("result") != 100:
                raise ZibalGatewayError(
                    f"Zibal request failed with result {response_data.get('result')}: {response_data.get('message')}"
                )
            return response_data
        except requests.exceptions.RequestException as e:
            logger.error(
                f"Error creating Zibal payment request for order {order_id}: {e}"
            )
            raise ZibalGatewayError(
                f"Network error creating payment request for order {order_id}"
            ) from e

    def verify_payment(self, payload_or_authority):
        headers = {"Content-Type": "application/json"}
        data = {
            "merchant": self.merchant_id,
            "trackId": payload_or_authority,
        }
        logger.info(
            f"Verifying Zibal payment for trackId {payload_or_authority}: {data}"
        )
        try:
            response = self.session.post(
                f"{self.api_url}/verify", json=data, headers=headers, timeout=5
            )
            response.raise_for_status()
            response_data = response.json()
            logger.info(
                f"Zibal payment verification response for trackId {payload_or_authority}: {response_data}"
            )
            return response_data
        except requests.exceptions.RequestException as e:
            logger.error(
                f"Error verifying Zibal payment for trackId {payload_or_authority}: {e}"
            )
            raise ZibalGatewayError(
                f"Network error verifying payment for trackId {payload_or_authority}"
            ) from e
