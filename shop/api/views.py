from rest_framework.views import APIView
from rest_framework.response import Response
from shop.models import (
    FoodCategory, 
    Menu, 
    Outlet, 
    FoodItem, 
    ItemVariant, 
    Addon, 
    Cart, 
    CartItem,
    OrderItem,
    Table,
    Order)
from shop.api.serializers import (
    FoodCategorySerializer, 
    OutletSerializer, 
    ClientFoodCategorySerializer,
    CartItemSerializer,
    FoodItemSerializer,
    OrderSerializer,
    CheckoutSerializer,
    TableSerializer
    )
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db import transaction
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync


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
    def get(self, request, menu_slug, format=None):
        menu = Menu.objects.filter(menu_slug=menu_slug).first()
        outlet = menu.outlet
        serializer = OutletSerializer(outlet)
        return Response(serializer.data)
    
class GetTableAPIView(APIView):
    """
    API endpoint that returns a list of tables in an outlet.
    """
    permission_classes = []
    def get(self, request, menu_slug, format=None):
        menu = Menu.objects.filter(menu_slug=menu_slug).first()
        outlet = menu.outlet
        tables = Table.objects.filter(outlet=outlet)
        serializer = TableSerializer(tables, many=True)
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

        # Return all the cart items
        serializer = CartItemSerializer(cart.items.all(), many=True)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def delete(self, request, menu_slug, item_id):
        user = request.user
        menu = get_object_or_404(Menu, menu_slug=menu_slug)
        outlet = menu.outlet
        cart = get_object_or_404(Cart, user=user, outlet=outlet)
        cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)
        cart_item.delete()
        return Response({"message": "Item removed from cart."}, status=status.HTTP_200_OK)

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

        return Response({"message": "Cart updated successfully."}, status=status.HTTP_200_OK)

class CheckoutAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, menu_slug):
        user = request.user
        
        # Get the cart
        menu = get_object_or_404(Menu, menu_slug=menu_slug)
        outlet = menu.outlet
        cart = get_object_or_404(Cart, user=user, outlet=outlet)
        cart_items = cart.items.all()
        
        if not cart_items.exists():
            return Response({"detail": "Cart is empty."}, status=status.HTTP_400_BAD_REQUEST)
        
        order_type = request.data.get('order_type', 'dine_in')
        table_id = request.data.get('table_id', None)
        if order_type == 'dine-in' and not table_id:
            return Response({"detail": "Table number is required for dine-in orders."}, status=status.HTTP_400_BAD_REQUEST)
        
        table=None
        if table_id:
            table = get_object_or_404(Table, id=table_id)

        cooking_instructions = request.data.get('cooking_instructions', None)

        # Prepare order data
        total_price = sum(item.get_total_price() for item in cart_items)
        order_data = {
            "user": user,
            "outlet": cart.outlet,
            "total": total_price,
            "status": "pending",
            "order_type": order_type,
            "table": table,
            "cooking_instructions": cooking_instructions
        }

        print(order_data, 'order_data')

        # Create the order
        order_serializer = CheckoutSerializer(data=order_data)
        print(order_serializer.is_valid(), 'order_serializer')
        print(order_serializer.errors, 'order_serializer.errors')

        order_serializer.is_valid(raise_exception=True)
        order = Order.objects.create(**order_data)
        
        # Create OrderItems from CartItems
        for cart_item in cart_items:
            order_item = OrderItem(
                order=order,
                food_item=cart_item.food_item,
                variant=cart_item.variant,
                quantity=cart_item.quantity
            )
            order_item.save()
            order_item.addons.set(cart_item.addons.all())
        
        # Optionally clear the cart
        cart.delete()  

        # Notify the kitchen staff
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'seller_{menu_slug}',
            {
                'type': 'seller_notification',
                'message': f'New order received: {order.order_id}'
            }
        )

        # async_to_sync(channel_layer.group_send)(
        #     f'order_{order.id}',
        #     {
        #         'type': 'order_update',
        #         'message': f'Your order {order.id} is now being processed.'
        #     }
        # )

        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)

class OrderAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, menu_slug=None):
        user = request.user
        if menu_slug:
            menu = get_object_or_404(Menu, menu_slug=menu_slug)
            if user.role == 'owner':
                print('owner')
                orders = Order.objects.filter(outlet=menu.outlet).order_by('-created_at')
            else:
                orders = Order.objects.filter(outlet=menu.outlet, user=user).order_by('-created_at')
        else:
            orders = Order.objects.filter(user=user).order_by('-created_at')
        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)