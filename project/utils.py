from django.conf import settings
from django.forms.models import model_to_dict
from pywebpush import webpush, WebPushException

def _process_subscription_info(subscription):
    """Process the subscription data for sending the push notification."""
    subscription_data = model_to_dict(subscription, exclude=["id", "user"])
    return {
        "endpoint": subscription_data["endpoint"],
        "keys": {
            "p256dh": subscription_data["p256dh"],
            "auth": subscription_data["auth"]
        }
    }

def _send_notification(subscription, payload, ttl=0):
    """Send a push notification to a single subscription."""
    subscription_data = _process_subscription_info(subscription)
    vapid_settings = getattr(settings, 'WEBPUSH_SETTINGS', {})
    vapid_private_key = vapid_settings.get('VAPID_PRIVATE_KEY')
    vapid_admin_email = vapid_settings.get('VAPID_ADMIN_EMAIL')
    vapid_data = {
        'vapid_private_key': vapid_private_key,
        'vapid_claims': {"sub": f"mailto:{vapid_admin_email}"}
    }
    try:
        response = webpush(subscription_info=subscription_data, data=payload, ttl=ttl, **vapid_data)
        print(f"Notification sent to {subscription.endpoint}, response: {response}")
    except WebPushException as e:
        if e.response.status_code == 410:
            subscription.delete()
        else:
            raise e

def send_notification_to_user(user, payload, ttl=0):
    """Send a notification to a specific user."""
    for subscription in user.webpush_info.all():
        _send_notification(subscription, payload, ttl)

def send_notification_to_group(group_name, payload, ttl=0):
    """Send a notification to all users in a specific group."""
    from .models import Group
    group = Group.objects.get(name=group_name)
    for push_info in group.push_information.select_related("subscription"):
        _send_notification(push_info.subscription, payload, ttl)

def send_broadcast_notification(payload, ttl=0):
    """Send a notification to all users."""
    from .models import WebPushInfo
    for subscription in WebPushInfo.objects.all():
        _send_notification(subscription, payload, ttl)
