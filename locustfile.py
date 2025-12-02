import random
from locust import HttpUser, task, between, TaskSet

class AuthTaskSet(TaskSet):
    def on_start(self):
        """Called when a virtual user starts executing this TaskSet."""
        # Generate a random phone number for each user
        self.phone_number = f"0912{random.randint(1000000, 9999999)}"
        self.otp_code = None

    @task
    def request_otp(self):
        """Simulate a user requesting an OTP."""
        response = self.client.post("/auth/request-otp/", json={"phone": self.phone_number})
        if response.status_code == 200:
            self.otp_code = "123456"  # Using the fixed OTP for DEBUG mode
            self.verify_otp()

    def verify_otp(self):
        """Simulate a user verifying an OTP."""
        if not self.otp_code:
            return

        response = self.client.post("/auth/verify-otp/", json={"phone": self.phone_number, "code": self.otp_code})
        if response.status_code == 200:
            self.user.access_token = response.json().get("access")
            # After successful login, interrupt this TaskSet to start shopping
            self.interrupt()

class ShoppingTaskSet(TaskSet):
    def on_start(self):
        """Called when a virtual user starts executing this TaskSet."""
        if not self.user.access_token:
            self.interrupt() # If not logged in, go back to AuthTaskSet
            return

        self.client.headers["Authorization"] = f"Bearer {self.user.access_token}"
        self.product_slugs = []

    @task(1)
    def list_products(self):
        """Simulate a user listing products."""
        response = self.client.get("/api/v1/products/")
        if response.status_code == 200:
            products = response.json().get("results", [])
            if products:
                self.product_slugs = [p["slug"] for p in products]
                self.view_product()

    def view_product(self):
        """Simulate a user viewing a product."""
        if not self.product_slugs:
            return

        product_slug = random.choice(self.product_slugs)
        self.client.get(f"/api/v1/products/{product_slug}/")
        self.add_to_cart(product_slug)


    def add_to_cart(self, product_slug):
        """Simulate a user adding a product to the cart."""
        response = self.client.get(f"/api/v1/products/{product_slug}/")
        if response.status_code == 200:
            product_id = response.json().get("id")
            if product_id:
                self.client.post(f"/api/v1/cart/add/{product_id}/")
                self.checkout()


    def checkout(self):
        """Simulate a user checking out."""
        self.client.post("/api/v1/orders/")

class WebsiteUser(HttpUser):
    host = "http://127.0.0.1:8000"
    wait_time = between(1, 5)
    tasks = {AuthTaskSet: 1, ShoppingTaskSet: 3} # Prioritize shopping tasks
    access_token = None

    def on_start(self):
        """Called when a virtual user is started."""
        self.client.headers = {"Content-Type": "application/json"}
