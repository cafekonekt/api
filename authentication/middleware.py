from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse
from rest_framework.status import HTTP_403_FORBIDDEN
from rest_framework_simplejwt.authentication import JWTAuthentication

class ABACMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # Extract user and attributes from JWT
        user = JWTAuthentication().authenticate(request)
        if user is None:
            return JsonResponse({"error": "Authentication required"}, status=HTTP_403_FORBIDDEN)
        
        request.user = user[0]
        user_attributes = {
            "role": request.user.role,
            "outlet_id": request.headers.get("X-Outlet-ID"),
        }

        # Check permissions (simplified example)
        if not self.is_authorized(request, user_attributes):
            return JsonResponse({"error": "Permission denied"}, status=HTTP_403_FORBIDDEN)

    def is_authorized(self, request, user_attributes):
        # Example: Only outlet managers can update orders
        if request.method == "PUT" and "live-orders" in request.path:
            return user_attributes["role"] == "outlet_manager"
        return True
