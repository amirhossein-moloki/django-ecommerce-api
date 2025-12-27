from django.http import HttpResponse, Http404
from django.views import View
from django.template.loader import render_to_string
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAdminUser

from .models import IntegrationSettings
from .services import generate_product_feed_data
from .serializers import IntegrationToggleSerializer


class BaseFeedView(View):
    """
    A base view for handling common logic for Torob and Emalls feeds.
    """
    platform_name = None  # Should be 'torob' or 'emalls'

    def get(self, request, *args, **kwargs):
        settings = IntegrationSettings.load()

        # Check if the platform is enabled
        is_enabled = getattr(settings, f"{self.platform_name}_enabled", False)
        if not is_enabled:
            raise Http404(f"{self.platform_name.capitalize()} feed is disabled.")

        # Validate the token
        token = request.GET.get('token')
        if not token or str(settings.feed_token) != token:
            return HttpResponse("Forbidden: Invalid or missing token.", status=403)

        # Generate feed data
        products = generate_product_feed_data(request)

        # Render XML content
        xml_content = render_to_string(f'integrations/{self.platform_name}_feed.xml', {'products': products})

        return HttpResponse(xml_content, content_type='application/xml')


class TorobFeedView(BaseFeedView):
    """
    Generates the XML feed for Torob.
    """
    platform_name = 'torob'


class EmallsFeedView(BaseFeedView):
    """
    Generates the XML feed for Emalls.
    """
    platform_name = 'emalls'


class IntegrationToggleAPIView(APIView):
    """
    API view for admin users to enable or disable integrations.

    Example POST request body:
    {
        "name": "torob",
        "enabled": true
    }
    """
    permission_classes = [IsAdminUser]

    def post(self, request, *args, **kwargs):
        settings = IntegrationSettings.load()
        serializer = IntegrationToggleSerializer(instance=settings, data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
