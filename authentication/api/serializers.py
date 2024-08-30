from rest_framework import serializers
from django.contrib.auth import authenticate
from django.utils.translation import gettext_lazy as _
from authentication.models import CustomUser
from rest_framework import serializers


class CustomAuthTokenSerializer(serializers.Serializer):
    username = serializers.CharField(label=_("Email or Phone Number"), write_only=True)
    password = serializers.CharField(label=_("Password"), style={'input_type': 'password'}, trim_whitespace=False)

    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')

        if username and password:
            user = authenticate(request=self.context.get('request'), username=username, password=password)

            if not user:
                msg = _('Unable to log in with provided credentials.')
                raise serializers.ValidationError(msg, code='authorization')
        else:
            msg = _('Must include "username" and "password".')
            raise serializers.ValidationError(msg, code='authorization')

        attrs['user'] = user
        return attrs


class FirebaseOTPSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=15)
    otp = serializers.CharField(max_length=6, required=False)
    firebase_token = serializers.CharField(required=False)

    def validate(self, data):
        phone_number = data.get('phone_number')
        otp = data.get('otp')
        firebase_token = data.get('firebase_token')

        if not phone_number:
            raise serializers.ValidationError("Phone number is required.")
        if not (otp or firebase_token):
            raise serializers.ValidationError("Either OTP or Firebase token is required.")
        
        return data
