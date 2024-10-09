from rest_framework.views import APIView
from rest_framework.response import Response
from authentication.models import WebPushInfo
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
    TableArea,
    DiscountCoupon)
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
    DiscountCouponDetailSerializer)
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.permissions import AllowAny
from django.shortcuts import get_object_or_404
from django.db import transaction, IntegrityError
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.utils.decorators import method_decorator

from cashfree_pg.models.create_order_request import CreateOrderRequest
from cashfree_pg.api_client import Cashfree
from cashfree_pg.models.customer_details import CustomerDetails
from cashfree_pg.models.order_meta import OrderMeta

from project.utils import send_notification_to_user
from django.db.models import Count, Sum
from django.utils import timezone

from datetime import timedelta
import datetime
import json

# Cashfree API credentials
Cashfree.XClientId = settings.CASHFREE_CLIENT_ID
Cashfree.XClientSecret = settings.CASHFREE_SECRET_KEY
Cashfree.XEnvironment = Cashfree.PRODUCTION
if settings.DEBUG:
    Cashfree.XEnvironment = Cashfree.SANDBOX
x_api_version = "2023-08-01"


class WebPushSubscriptionView(APIView):
    permission_classes = []
    def post(self, request):
        user = request.user
        subscription_data = request.data
        web_push_info, created = WebPushInfo.objects.get_or_create(
            user=user,
            endpoint=subscription_data['endpoint'],
        )
        web_push_info.p256dh = subscription_data['keys']['p256dh']
        web_push_info.auth = subscription_data['keys']['auth']
        web_push_info.save()
        return Response({'message': 'Subscription saved successfully.'}, status=status.HTTP_201_CREATED)

class TestNotificationView(APIView):
    permission_classes = []
    def post(self, request):
        user = request.user
        payload = json.dumps({"title": "Test Notification", "body": "This is a test message."})
        send_notification_to_user(user, payload)
        return Response({'message': 'Notification sent.'}, status=status.HTTP_200_OK)
                        

class DashboardDataAPIView(APIView):
    def get(self, request, *args, **kwargs):
        # Get the current date
        today = timezone.now().date()
        
        # Calculate the start of today and last week
        start_of_today = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        start_of_last_week = today - timedelta(days=7)
        start_of_week_before_last = start_of_last_week - timedelta(days=7)

        # Fetch today's total orders and revenue
        todays_orders = Order.objects.filter(created_at__gte=start_of_today).count()
        todays_revenue = Order.objects.filter(created_at__gte=start_of_today).aggregate(total=Sum('total'))['total'] or 0

        # Fetch total orders last week (week before the current 7 days)
        total_orders_last_week = Order.objects.filter(
            created_at__date__gte=start_of_week_before_last,
            created_at__date__lt=start_of_last_week
        ).count()

        # Calculate average revenue (total revenue divided by total number of days in the current 'orders' data)
        total_revenue = Order.objects.aggregate(total=Sum('total'))['total'] or 0
        total_days = Order.objects.values('created_at__date').distinct().count()
        average_revenue = total_revenue / total_days if total_days else 0

        # Fetch order counts and revenues grouped by date.
        orders_data = (
            Order.objects.values('created_at__date')
            .annotate(orderCount=Count('order_id'))
            .order_by('created_at__date')
        )
        
        revenue_data = (
            Order.objects.values('created_at__date')
            .annotate(dailyRevenue=Sum('total'))
            .order_by('created_at__date')
        )

        # Formatting data to match the required structure.
        orders = [
            {'date': order['created_at__date'].strftime('%Y-%m-%d'), 'orderCount': order['orderCount']}
            for order in orders_data
        ]
        revenue = [
            {'date': revenue['created_at__date'].strftime('%Y-%m-%d'), 'dailyRevenue': float(revenue['dailyRevenue'])}
            for revenue in revenue_data
        ]

        # Structure data as expected in the frontend.
        demoData = {
            'orders': orders,
            'revenue': revenue,
            'todaysOrders': todays_orders,
            'todaysRevenue': float(todays_revenue),
            'totalOrdersLastWeek': total_orders_last_week,
            'averageRevenue': float(average_revenue),
        }
        return Response(demoData, status=status.HTTP_200_OK)


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
    def get(self, request, slug):
        food_item = get_object_or_404(FoodItem, slug=slug)
        serializer = FoodItemSerializer(food_item)
        return Response(serializer.data)
    
    def put(self, request, slug):
        try:
            food_item = get_object_or_404(FoodItem, slug=slug)
            for key, value in request.data.items():
                setattr(food_item, key, value)
                food_item.save()
            serializer = FoodItemSerializer(food_item)
            return Response(serializer.data)
        except Exception as e:
            return Response("Invalid data", status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, slug):
        food_item = get_object_or_404(FoodItem, slug=slug)
        food_item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AddonCategoryListCreateView(APIView):
    def get(self, request):
        user = request.user
        outlet = Outlet.objects.filter(outlet_manager=user).first()
        menu = Menu.objects.filter(outlet=outlet).first()
        addon_categories = AddonCategory.objects.filter(menu=menu)
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
        addons = Addon.objects.filter(id__in=data.get('addons', []))
        quantity = data.get('quantity', 1)
        id = data.get('id')

        cart_item, item_created = CartItem.objects.get_or_create(
            item_id=id, cart=cart, food_item=food_item, variant=item_variant, defaults={'quantity': quantity}
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
        payment_method = request.data.get('payment_method')
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
            "cooking_instructions": cooking_instructions,
            "payment_method": payment_method
        }

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

        if payment_method == 'cash':
            return Response({
                "order_id": order.order_id,
                "payment_session_id": None
            }, status=status.HTTP_201_CREATED)

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
        create_order_request.order_meta = order_meta

        # try:
        api_response = Cashfree().PGCreateOrder(x_api_version, create_order_request, None, None)
        order.payment_id = api_response.data.cf_order_id
        order.payment_session_id = api_response.data.payment_session_id
        order.save()
        
        # notify outlet owner
        owner = menu.outlet.outlet_manager
        payload = json.dumps({
            "title": "New Order", 
            "body": "You have received a new order.", 
            "url": "/order"})
        send_notification_to_user(owner, payload)
        # Notify the shop owner via Django Channels
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'seller_{menu.menu_slug}',
            {
                'type': 'seller_notification',
                'message': OrderSerializer(order).data
            }
        )
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
        decoded_body = request.body.decode('utf-8')
        timestamp = request.headers.get('x-webhook-timestamp')
        signature = request.headers.get('x-webhook-signature')

        # try:
        # Verify the signature using Cashfree SDK
        cashfree = Cashfree()
        cashfree.PGVerifyWebhookSignature(signature, decoded_body, timestamp)

        # Get raw request data
        body = request.data
        # Process payment data
        order_id = body['data']['order']['order_id']
        transaction_status = body['data']['payment']['payment_status']

        # Handle payment success
        if transaction_status == "SUCCESS":
            # Update order status to 'paid'
            order = Order.objects.get(order_id=order_id)
            order.payment_status = 'success'
            order.payment_method = body['data']['payment']['payment_group']
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
            "new": [],
            "preparing": [],
            "completed": []
        }
        for order in serializer.data:
            if order['status'] == 'pending':
                live_orders['new'].append(order)
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
            payload = json.dumps({
                "title": "Order Completed", 
                "body": "Your order has been completed.", 
                "url": f"/order/{order.order_id}"})
            send_notification_to_user(order.user, payload)
            return Response({"message": "Order completed successfully."}, status=status.HTTP_200_OK)

        elif data['status'] == 'processing':
            order.status = 'processing'
            order.updated_at = datetime.datetime.now()
            order.prep_start_time = datetime.datetime.now()
            order.save()
            payload = json.dumps({
                "title": "Order Processing", 
                "body": "Your order is being prepared.", 
                "url": f"/order/{order.order_id}"})
            send_notification_to_user(order.user, payload)
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
        user = request.user
        outlet = Outlet.objects.filter(outlet_manager=user).first()
        serializer = OutletSerializer(outlet)
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

    def delete(self, request, table_id):
        table = get_object_or_404(Table, table_id=table_id)
        table.delete()
        return Response({"detail": "Table deleted successfully."}, status=status.HTTP_200_OK)


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
        user = request.user
        outlet = Outlet.objects.filter(outlet_manager=user).first() 
        areas = TableArea.objects.filter(outlet=outlet)
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


class DiscountCouponListCreateView(APIView):
    def post(self, request):
        user = request.user
        outlet = Outlet.objects.filter(outlet_manager=user).first()
        if not outlet:
            return Response({"detail": "You are not authorized to create a discount coupon."}, status=status.HTTP_403_FORBIDDEN)
        serializer = DiscountCouponDetailSerializer(data={**request.data, "outlet": outlet.id})
        print(serializer)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def get(self, request):
        coupons = DiscountCoupon.objects.all()
        serializer = DiscountCouponDetailSerializer(coupons, many=True)
        return Response(serializer.data)
