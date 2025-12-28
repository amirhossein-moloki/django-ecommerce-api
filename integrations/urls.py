from django.urls import path
from .views import TorobFeedView, EmallsFeedView, IntegrationToggleAPIView

app_name = "integrations"

urlpatterns = [
    path("feeds/torob.xml", TorobFeedView.as_view(), name="torob_feed"),
    path("feeds/emalls.xml", EmallsFeedView.as_view(), name="emalls_feed"),
    path(
        "api/integrations/toggle/",
        IntegrationToggleAPIView.as_view(),
        name="toggle_integration",
    ),
]
