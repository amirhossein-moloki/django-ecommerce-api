from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.contrib.auth.signals import user_logged_in
from .models import Profile

User = get_user_model()

def get_client_ip(request):
    """Get the client's IP address from the request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Create a profile for a new user when they are created.
    """
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """
    Save the profile whenever the user object is saved.
    """
    if hasattr(instance, 'profile'):
        instance.profile.save()

@receiver(user_logged_in)
def update_last_login_ip(sender, request, user, **kwargs):
    """
    A signal receiver which updates the last_login_ip for
    the user logging in.
    """
    user.last_login_ip = get_client_ip(request)
    user.save(update_fields=['last_login_ip'])
