from rest_framework.views import APIView
from rest_framework.response import Response
from shop.models import FoodCategory, Menu, Outlet, FoodItem, ItemVariant, Addon, Cart, CartItem
from shop.api.serializers import (
    FoodCategorySerializer, 
    OutletSerializer, 
    ClientFoodCategorySerializer,
    CartItemSerializer,
    FoodItemSerializer
    )
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

class MenuAPIView(APIView):
    """
    API endpoint that returns a list of categories with nested subcategories and menu items.
    """
    permission_classes = [IsAuthenticated]
    def get(self, request, format=None):
        user = request.user
        outlet = Outlet.objects.filter(outlet_manager=user).first()
        menu = Menu.objects.filter(outlet=outlet).first()
        categories = FoodCategory.objects.filter(menu=menu)
        serializer = FoodCategorySerializer(categories, many=True)
        return Response(serializer.data)

class ClientMenuAPIView(APIView):
    """
    API endpoint that returns a list of categories with nested subcategories and menu items for a client.
    """
    permission_classes = []
    def get(self, request, menu_slug, format=None):
        menu = Menu.objects.filter(menu_slug=menu_slug).first()
        categories = FoodCategory.objects.filter(menu=menu)
       
        # Serialize the existing categories
        serializer = ClientFoodCategorySerializer(categories, many=True)
        category_data = serializer.data

        # Add the recommended category
        recommended_category = self.get_recommended_category(menu)
        if recommended_category:
            category_data.insert(0, recommended_category)

        return Response(category_data)
    
    def get_recommended_category(self, menu):
        """Create a 'Recommended' category with all featured food items."""
        featured_items = FoodItem.objects.filter(menu=menu, featured=True)
        if featured_items.exists():
            food_items_data = FoodItemSerializer(featured_items, many=True).data
            recommended_category = {
                "id": -1,  # You can choose to leave it `None` or set a specific ID
                "name": "Recommended",
                "sub_categories": [],  # No subcategories in recommended
                "food_items": food_items_data
            }
            return recommended_category
        return None

class GetOutletAPIView(APIView):
    """
    API endpoint that returns a list of outlets.
    """
    permission_classes = []
    def get(self, request, slug, format=None):
        menu = Menu.objects.filter(menu_slug=slug).first()
        outlet = menu.outlet
        serializer = OutletSerializer(outlet)
        return Response(serializer.data)
    
class CartView(APIView):
    def get(self, request, menu_slug):
        user = request.user
        menu = get_object_or_404(Menu, menu_slug=menu_slug)
        outlet = menu.outlet
        cart, created = Cart.objects.get_or_create(user=user, outlet=outlet)
        serializer = CartItemSerializer(cart.items.all(), many=True)
        return Response(serializer.data)

    def post(self, request, menu_slug):
        user = request.user
        menu = get_object_or_404(Menu, menu_slug=menu_slug)
        outlet = menu.outlet
        cart, created = Cart.objects.get_or_create(user=user, outlet=outlet)
        data = request.data

        food_item = get_object_or_404(FoodItem, id=data['food_item_id'])
        item_variant = get_object_or_404(ItemVariant, id=data['variant_id']) if data.get('variant_id') else None
        variants = item_variant.variant if item_variant else None
        addons = Addon.objects.filter(id__in=data.get('addons', []))
        quantity = data.get('quantity', 1)
        id = data.get('id')

        cart_item, item_created = CartItem.objects.get_or_create(
            id=id, cart=cart, food_item=food_item, variant=variants, defaults={'quantity': quantity}
        )

        if not item_created:
            cart_item.quantity += quantity
            cart_item.save()

        cart_item.addons.set(addons)

        serializer = CartItemSerializer(cart_item)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def delete(self, request, menu_slug, item_id):
        user = request.user
        menu = get_object_or_404(Menu, menu_slug=menu_slug)
        outlet = menu.outlet
        cart = get_object_or_404(Cart, user=user, outlet=outlet)
        cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)
        cart_item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def put(self, request, menu_slug, item_id):
        user = request.user
        menu = get_object_or_404(Menu, menu_slug=menu_slug)
        outlet = menu.outlet
        cart = get_object_or_404(Cart, user=user, outlet=outlet)
        cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)
        quantity = request.data.get('quantity', 1)

        if quantity <= 0:
            cart_item.delete()
        else:
            cart_item.quantity = quantity
            cart_item.save()

        return Response(status=status.HTTP_200_OK)
