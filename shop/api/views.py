from rest_framework.views import APIView
from rest_framework.response import Response
from shop.models import (
    FoodCategory,
    Menu,
    Outlet,
    FoodItem,
    ItemVariant,
    Addon,
    AddonCategory,
    Cart,
    CartItem,
    OrderItem,
    Table,
    Order,
    TableArea)
from shop.api.serializers import (
    FoodCategorySerializer,
    OutletSerializer,
    CartItemSerializer,
    FoodItemSerializer,
    OrderSerializer,
    CheckoutSerializer,
    TableSerializer,
    AreaSerializer,
    AddonCategorySerializer,
    )
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.permissions import AllowAny
from rest_framework.decorators import permission_classes
from django.shortcuts import get_object_or_404
from django.db import transaction, IntegrityError
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from rest_framework.decorators import api_view

from cashfree_pg.models.create_order_request import CreateOrderRequest
from cashfree_pg.api_client import Cashfree
from cashfree_pg.models.customer_details import CustomerDetails
from cashfree_pg.models.order_meta import OrderMeta

import datetime
import json

# Cashfree API credentials
Cashfree.XClientId = settings.CASHFREE_CLIENT_ID
Cashfree.XClientSecret = settings.CASHFREE_SECRET_KEY
Cashfree.XEnvironment = Cashfree.SANDBOX
x_api_version = "2023-08-01"


class FoodCategoryListCreateView(APIView):
    permission_classes = []

    def get(self, request, menu_slug):
        menu = get_object_or_404(Menu, menu_slug=menu_slug)
        categories = FoodCategory.objects.filter(menu=menu)
        serializer = FoodCategorySerializer(categories, many=True)
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


class FoodItemListCreateView(APIView):
    def get(self, request):
        user = request.user
        outlet = Outlet.objects.filter(outlet_manager=user).first()
        menu = Menu.objects.filter(outlet=outlet).first()
        categories = FoodCategory.objects.filter(menu=menu)
        serializer = FoodCategorySerializer(categories, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = FoodItemSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class FoodItemDetailView(APIView):
    def get(self, request, id):
        food_item = get_object_or_404(FoodItem, id=id)
        serializer = FoodItemSerializer(food_item)
        return Response(serializer.data)
    
    def put(self, request, id):
        food_item = get_object_or_404(FoodItem, id=id)
        serializer = FoodItemSerializer(food_item, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, id):
        food_item = get_object_or_404(FoodItem, id=id)
        food_item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AddonCategoryListCreateView(APIView):
    def get(self, request):
        addon_categories = AddonCategory.objects.all()
        serializer = AddonCategorySerializer(addon_categories, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        serializer = AddonCategorySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AddonCategoryDetailView(APIView):
    def get(self, request, id):
        addon_category = get_object_or_404(AddonCategory, id=id)
        serializer = AddonCategorySerializer(addon_category)
        return Response(serializer.data)

    def put(self, request, id):
        addon_category = get_object_or_404(AddonCategory, id=id)
        serializer = AddonCategorySerializer(addon_category, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, id):
        addon_category = get_object_or_404(AddonCategory, id=id)
        addon_category.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CartView(APIView):
    def get(self, request, menu_slug):
        user = request.user
        menu = get_object_or_404(Menu, menu_slug=menu_slug)
        outlet = menu.outlet
        cart = self.get_cart(user, outlet)
        serializer = CartItemSerializer(cart.items.all(), many=True)
        return Response(serializer.data)

    def post(self, request, menu_slug):
        user = request.user
        menu = get_object_or_404(Menu, menu_slug=menu_slug)
        outlet = menu.outlet
        cart = self.get_cart(user, outlet)

        data = request.data
        food_item = get_object_or_404(FoodItem, id=data['food_item_id'])
        item_variant = get_object_or_404(ItemVariant, id=data['variant_id']) if data.get('variant_id') else None
        variants = item_variant.variant if item_variant else None
        addons = Addon.objects.filter(id__in=data.get('addons', []))
        quantity = data.get('quantity', 1)
        id = data.get('id')

        cart_item, item_created = CartItem.objects.get_or_create(
            item_id=id, cart=cart, food_item=food_item, variant=variants, defaults={'quantity': quantity}
        )
        if not item_created:
            cart_item.quantity += quantity
            cart_item.save()

        cart_item.addons.set(addons)

        # Return all the cart items
        serializer = CartItemSerializer(cart.items.all(), many=True)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def get_cart(self, user, outlet):
        try:
            with transaction.atomic():  # Ensure atomic transaction
                cart, created = Cart.objects.get_or_create(user=user, outlet=outlet)
        except IntegrityError:
            # Handle duplicate cart creation here (optional)
            cart = Cart.objects.filter(user=user, outlet=outlet).first()
        return cart

    def delete(self, request, menu_slug, item_id):
        user = request.user
        menu = get_object_or_404(Menu, menu_slug=menu_slug)
        outlet = menu.outlet
        cart = get_object_or_404(Cart, user=user, outlet=outlet)
        cart_item = get_object_or_404(CartItem, item_id=item_id, cart=cart)
        cart_item.delete()

        # Return all the cart items
        serializer = CartItemSerializer(cart.items.all(), many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, menu_slug, item_id):
        user = request.user
        menu = get_object_or_404(Menu, menu_slug=menu_slug)
        outlet = menu.outlet
        cart = get_object_or_404(Cart, user=user, outlet=outlet)
        cart_item = get_object_or_404(CartItem, item_id=item_id, cart=cart)
        quantity = request.data.get('quantity', 1)

        if quantity <= 0:
            cart_item.delete()
        else:
            cart_item.quantity = quantity
            cart_item.save()

        # Return all the cart items
        serializer = CartItemSerializer(cart.items.all(), many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class CheckoutAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, menu_slug):
        user = request.user

        # Get the cart
        menu = get_object_or_404(Menu, menu_slug=menu_slug)
        outlet = menu.outlet
        cart = get_object_or_404(Cart, user=user, outlet=outlet)
        cart_items = CartItem.objects.filter(cart=cart)

        if cart_items.count() == 0:
            return Response({"detail": "Cart is empty."}, status=status.HTTP_400_BAD_REQUEST)

        order_type = request.data.get('order_type', 'dine_in')
        table_id = request.data.get('table_id', None)
        if order_type == 'dine_in' and not table_id:
            return Response({"detail": "Table number is required for dine-in orders."}, status=status.HTTP_400_BAD_REQUEST)

        table = None
        if table_id:
            table = get_object_or_404(Table, table_id=table_id)

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

        # Create the order in your database
        order_serializer = CheckoutSerializer(data=order_data)
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

        # Clear the cart
        cart.delete()

        customer_details = CustomerDetails(
                    customer_id=user.get_user_id(),
                    customer_phone=user.phone_number[3:],
                    customer_name=user.get_full_name(),
                    customer_email=user.email
                )

        create_order_request = CreateOrderRequest(
            order_id=str(order.order_id),
            order_amount=float(total_price),
            order_currency="INR",
            customer_details=customer_details
        )

        order_meta = OrderMeta()
        order_meta.return_url = f"https://app.tacoza.co/order/{order.order_id}"
        order_meta.notify_url = f"https://api.tacoza.co/api/shop/cashfree/webhook/"
        order_meta.payment_methods = "cc,dc,upi"
        create_order_request.order_meta = order_meta

        # try:
        api_response = Cashfree().PGCreateOrder(x_api_version, create_order_request, None, None)
        print(api_response, 'response')
        order.payment_id = api_response.data.cf_order_id
        order.payment_session_id = api_response.data.payment_session_id
        order.save()
        # Return the payment session id to the client to initiate payment
        return Response({
            "order_id": api_response.data.order_id,
            "payment_session_id": api_response.data.payment_session_id
        }, status=status.HTTP_201_CREATED)

        # except Exception as e:
        #     return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@method_decorator(csrf_exempt, name='dispatch')
class CashfreeWebhookView(APIView):
    permission_classes = [AllowAny]  # Allow webhook to be accessed without authentication

    def post(self, request, *args, **kwargs):
        print(request.body, 'request')
        print(request.data, 'headers')
        # Get raw request data
        body = request.data
        
        decoded_body = request.body.decode('utf-8')

        timestamp = request.headers.get('x-webhook-timestamp')
        signature = request.headers.get('x-webhook-signature')

        # try:
        # Verify the signature using Cashfree SDK
        cashfree = Cashfree()
        cashfree.PGVerifyWebhookSignature(signature, decoded_body, timestamp)

        # Process payment data
        order_id = body['data']['order']['order_id']
        transaction_status = body['data']['payment']['payment_status']

        # Handle payment success
        if transaction_status == "SUCCESS":
            # Update order status to 'paid'
            order = Order.objects.get(order_id=order_id)
            order.payment_status = 'success'
            order.save()
            
            menu = Menu.objects.get(outlet=order.outlet)

            # Notify the shop owner via Django Channels
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f'seller_{menu.menu_slug}',
                {
                    'type': 'seller_notification',
                    'message': OrderSerializer(order).data
                }
            )
        elif transaction_status == "PENDING":
            order = Order.objects.get(order_id=order_id)
            order.payment_status = 'pending'
            order.save()
        else:
            order = Order.objects.get(order_id=order_id)
            order.payment_status = 'failed'
            order.save()

        return JsonResponse({"status": "success"})

        # except Exception as e:
        #     print(e, 'error')
        #     return JsonResponse({"error": str(e)}, status=400)


class PaymentStatusAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, order_id):
        try:
            api_response = Cashfree().PGOrderFetchPayments(x_api_version, order_id, None)
            print(api_response.data)
            return Response(api_response.data)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class OrderList(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, menu_slug=None, order_id=None):
        user = request.user
        if user.role == 'owner':
            outlet = Outlet.objects.filter(outlet_manager=user).first()
            orders = Order.objects.filter(outlet=outlet).order_by('-created_at')
        else:
            orders = Order.objects.filter(user=user).order_by('-created_at')
        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)


class OrderDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, order_id):
        user = request.user
        order = get_object_or_404(Order, order_id=order_id)
        if user.role == 'owner' and order.outlet.outlet_manager != user:
            return Response({"detail": "You are not authorized to view this order."}, status=status.HTTP_403_FORBIDDEN)
        elif user.role == 'customer' and order.user != user:
            return Response({"detail": "You are not authorized to view this order."}, status=status.HTTP_403_FORBIDDEN)
        serializer = OrderSerializer(order)
        return Response(serializer.data)


class LiveOrders(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        user = request.user
        outlet = Outlet.objects.filter(outlet_manager=user).first()
        # return all orders of current date categorised by status
        orders = Order.objects.filter(outlet=outlet, created_at__date=datetime.datetime.now().date()).order_by('-created_at')
        serializer = OrderSerializer(orders, many=True)
        live_orders = {
            "newOrders": [],
            "preparing": [],
            "completed": []
        }
        for order in serializer.data:
            if order['status'] == 'pending':
                live_orders['newOrders'].append(order)
            elif order['status'] == 'processing':
                live_orders['preparing'].append(order)
            elif order['status'] == 'completed':
                live_orders['completed'].append(order)
        return Response(live_orders, status=status.HTTP_200_OK)

    def put(self, request, order_id):
        user = request.user
        order = get_object_or_404(Order, order_id=order_id)
        if order.outlet.outlet_manager != user:
            return Response({"detail": "You are not authorized to update this order."}, status=status.HTTP_403_FORBIDDEN)
        data = request.data

        if data['status'] == 'completed':
            order.status = 'completed'
            order.updated_at = datetime.datetime.now()
            order.save()
            return Response({"message": "Order completed successfully."}, status=status.HTTP_200_OK)

        elif data['status'] == 'processing':
            order.status = 'processing'
            order.updated_at = datetime.datetime.now()
            order.save()
            return Response({"message": "Order is being prepared."}, status=status.HTTP_200_OK)

        elif data['status'] == 'pending':
            order.status = 'pending'
            order.updated_at = datetime.datetime.now()
            order.save()
            return Response({"message": "Order is pending."}, status=status.HTTP_200_OK)

        return Response({"detail": "Invalid status."}, status=status.HTTP_400_BAD_REQUEST)


class OutletListView(APIView):
    permission_classes = []
    
    def get(self, request, menu_slug):
        menu = get_object_or_404(Menu, menu_slug=menu_slug)
        outlet = menu.outlet
        serializer = OutletSerializer(outlet)
        return Response(serializer.data)


class OutletListCreateView(APIView):
    def get(self, request):
        outlets = Outlet.objects.all()
        serializer = OutletSerializer(outlets, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = OutletSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class OutletDetailView(APIView):
    def get(self, request, menu_slug):
        menu = get_object_or_404(Menu, menu_slug=menu_slug)
        outlet = menu.outlet
        serializer = OutletSerializer(outlet)
        return Response(serializer.data)

    def put(self, request, id):
        outlet = get_object_or_404(Outlet, id=id)
        serializer = OutletSerializer(outlet, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, id):
        outlet = get_object_or_404(Outlet, id=id)
        outlet.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class TableListView(APIView):
    permission_classes = []

    def get(self, request, menu_slug):
        menu = get_object_or_404(Menu, menu_slug=menu_slug)
        tables = Table.objects.filter(outlet=menu.outlet)
        serializer = TableSerializer(tables, many=True)
        return Response(serializer.data)
    

class TableListCreateView(APIView):
    def get(self, request):
        try:
            user = request.user
            tables = Table.objects.filter(outlet__outlet_manager=user)
            serializer = TableSerializer(tables, many=True)
            return Response(serializer.data)
        except Exception as e:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def post(self, request):
        try:
            user = request.user
            data = request.data
            outlet = Outlet.objects.filter(outlet_manager=user).first()
            name = data.get('name')
            capacity = data.get('capacity')
            area = data.get('area')
            area = TableArea.objects.filter(id=area).first()
            table = Table.objects.create(outlet=outlet, name=name, capacity=capacity, area=area)
            serializer = TableSerializer(table)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TableDetailGetView(APIView):
    permission_classes = []

    def get(self, request, table_id):
        table = get_object_or_404(Table, table_id=table_id)
        serializer = TableSerializer(table)
        return Response(serializer.data)


class TableDetailView(APIView):
    def put(self, request, table_id):
        table = get_object_or_404(Table, id=table_id)
        serializer = TableSerializer(table, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, table_id):
        table = get_object_or_404(Table, id=table_id)
        table.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AreaListCreateView(APIView):
    def get(self, request):
        areas = TableArea.objects.all()
        serializer = AreaSerializer(areas, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        try :
            outlet = Outlet.objects.filter(outlet_manager=request.user).first()
            area = TableArea.objects.create(outlet=outlet, **request.data)
            serializer = AreaSerializer(area)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AreaDetailView(APIView):
    def get(self, request, id):
        area = get_object_or_404(TableArea, id=id)
        serializer = AreaSerializer(area)
        return Response(serializer.data)

    def put(self, request, id):
        area = get_object_or_404(TableArea, id=id)
        serializer = AreaSerializer(area, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, id):
        area = get_object_or_404(TableArea, id=id)
        area.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class SocketSeller(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        user = request.user
        outlet = Outlet.objects.filter(outlet_manager=user).first()
        menu = Menu.objects.filter(outlet=outlet).first()
        url = f'/ws/sellers/{menu.menu_slug}'
        return Response({"url": url}, status=status.HTTP_200_OK)
