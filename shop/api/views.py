from rest_framework.views import APIView
from rest_framework.response import Response
from shop.models import FoodCategory, Menu, Outlet
from shop.api.serializers import FoodCategorySerializer

class MenuAPIView(APIView):
    """
    API endpoint that returns a list of categories with nested subcategories and menu items.
    """
    def get(self, request, pk, format=None):
        menu = Menu.objects.filter(pk=pk).first()
        categories = FoodCategory.objects.filter(menu=menu)
        serializer = FoodCategorySerializer(categories, many=True)
        return Response(serializer.data)

class GetOutletAPIView(APIView):
    """
    API endpoint that returns a list of outlets.
    """
    def get(self, request, format=None):
        outlets = Outlet.objects.all()
        serializer = OutletSerializer(outlets, many=True)
        return Response(serializer.data)