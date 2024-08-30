from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from authentication.api.serializers import CustomAuthTokenSerializer
import pyrebase
from django.conf import settings
from rest_framework.views import APIView
from rest_framework import status
from firebase_admin import auth as firebase_auth
from authentication.api.serializers import FirebaseOTPSerializer

# firebase_config = {
#   'apiKey': "AIzaSyAspmZiwJzWBaURl-hZvk_Vnl4Mbb7-zoM",
#   'authDomain': "yumyum-5c5ad.firebaseapp.com",
#   'projectId': "yumyum-5c5ad",
#   'storageBucket': "yumyum-5c5ad.appspot.com",
#   'messagingSenderId': "839971540285",
#   'appId': "1:839971540285:web:b942d0ed7c1d3d913d0954",
#   'measurementId': "G-7VY3VDV984"
# };

# firebase = pyrebase.initialize_app(firebase_config)
# firebase_auth_instance = firebase.auth()


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


class SendOTPView(APIView):
    def post(self, request):
        serializer = FirebaseOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone_number = serializer.validated_data['phone_number']
        
        # Generate OTP using Firebase
        try:
            firebase_auth_instance.sign_in_with_phone_number(phone_number)
            return Response({"message": "OTP sent successfully."}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class VerifyOTPView(APIView):
    def post(self, request):
        serializer = FirebaseOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        firebase_token = serializer.validated_data.get('firebase_token')

        try:
            decoded_token = firebase_auth.verify_id_token(firebase_token)
            phone_number = decoded_token['phone_number']
            
            # Check if user exists or create a new one
            user, created = CustomUser.objects.get_or_create(phone_number=phone_number)
            if created:
                user.set_unusable_password()  # Set an unusable password for users logging in with OTP
                user.save()

            # Generate a Django Token for authenticated sessions
            token, _ = Token.objects.get_or_create(user=user)
            
            return Response({
                "token": token.key,
                "user_id": user.pk,
                "role": user.role
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class CustomAuthToken(ObtainAuthToken):
    serializer_class = CustomAuthTokenSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)
        return Response({
            'token': token.key,
            'user_id': user.pk,
            'role': user.role,
        })