from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework.authtoken.models import Token
from authentication.api.serializers import LoginSerializer, SendOTPSerializer, VerifyOTPSerializer
from rest_framework.views import APIView
from rest_framework import status
from authentication.models import CustomUser
from django.http import JsonResponse
from rest_framework.permissions import IsAuthenticated

@api_view(['GET'])
def getRoutes(request):
    routes = [
        '/api/token/',
        '/api/token/refresh/',
        '/api/token/verify/',

        '/api/auth/register/',
        '/api/auth/login/',
        '/api/auth/logout/',
        
        '/api/auth/users/',
        '/api/auth/user/<str:pk>/',
        '/api/auth/user/<str:pk>/update/',
        '/api/auth/user/<str:pk>/delete/',
        ]    
    return Response(routes)


class LoginView(APIView):
    permission_classes = []  # No permission required to access this view
    def post(self, request, *args, **kwargs):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data  # Get the validated data

        user = CustomUser.objects.get(email=validated_data['email'])

        response = JsonResponse({
            'user': {
                'email': user.email,
                'role': user.role,
                'phone_number': user.phone_number,
            },
            'tokens': validated_data['tokens']
        }, status=status.HTTP_200_OK)
        return response
    

class ValidateToken(APIView):
    authentication_classes = [IsAuthenticated]
    def post(self, request):
        token = request.headers.get('Authorization').split(' ')[1]
        if not token:
            return Response({"error": "Token is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user = Token.objects.get(key=token).user
            return Response({
                "valid": True,
                "user_id": user.pk,
                "role": user.role
            }, status=status.HTTP_200_OK)
        except Token.DoesNotExist:
            return Response({"valid": False}, status=status.HTTP_200_OK)    


class SendOTPView(APIView):
    permission_classes = []
    def post(self, request, *args, **kwargs):
        serializer = SendOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        otp_code = serializer.send_otp()
        return Response({"detail": "OTP sent successfully.", "otp": otp_code}, status=status.HTTP_200_OK)


class VerifyOTPView(APIView):
    permission_classes = []
    def post(self, request, *args, **kwargs):
        serializer = VerifyOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = CustomUser.objects.get(phone_number=serializer.validated_data['phone_number'])
        tokens = serializer.create_tokens()

        response = JsonResponse({
            'user': {
                'email': user.email,
                'name': user.name,
                'role': user.role,
                'phone_number': user.phone_number,
            },
            'tokens': tokens
        }, status=status.HTTP_200_OK)
        return response

class UpdateUserView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, *args, **kwargs):
        user = request.user
        user_data = request.data
        user.name = user_data.get('name', user.name)
        user.email = user_data.get('email', user.email)
        user.phone_number = user_data.get('phone_number', user.phone_number)
        user.save()
        return Response({"detail": "User updated successfully."}, status=status.HTTP_200_OK)

