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
    Payouts,
    TableArea,
    OrderTimelineItem,
    DiscountCoupon,)
from authentication.models import CustomUser
from shop.api.serializers import (
    FoodCategorySerializer,
    OutletSerializer,
    CustomerOutletSerializer,
    OwnerOutletSerializer,
    CartItemSerializer,
    FoodItemSerializer,
    OrderSerializer,
    CheckoutSerializer,
    TableSerializer,
    AreaSerializer,
    AddonCategorySerializer,
    DiscountCouponDetailSerializer,
    DiscountCouponSerializer,)
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny
from django.shortcuts import get_object_or_404
from django.db import transaction, IntegrityError
from django.db.models import Q
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.utils.dateparse import parse_date
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from authentication.utils import RoleBasedSerializer

from cashfree_pg.models.create_order_request import CreateOrderRequest
from cashfree_pg.api_client import Cashfree
from cashfree_pg.models.customer_details import CustomerDetails
from cashfree_pg.models.order_meta import OrderMeta

from project.utils import send_notification_to_user
from django.db.models import Count, Sum
from django.utils import timezone
from django.db import models

from django.core.cache import cache
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

CUSTOMER = 'customer'
OWNER = 'owner'

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
        # Get the current user
        user = request.user
        user_outlet_ids = Outlet.objects.filter(outlet_manager=user).values_list('id', flat=True)

        # Key for cache
        cache_key = f"dashboard_data_{user.id}"
        cache_timeout = 6 * 60 * 60  # 6 hours in seconds

        # Try to get cached data
        demoData = cache.get(cache_key)

        if not demoData:
            # Compute data if not cached
            today = timezone.now().date()
            start_of_today = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
            start_of_last_week = today - timedelta(days=7)
            start_of_week_before_last = start_of_last_week - timedelta(days=7)
            start_of_month = today.replace(day=1)

            todays_revenue = Order.objects.filter(
                outlet_id__in=user_outlet_ids,
                created_at__gte=start_of_today,
                payment_status='success',
            ).aggregate(total=Sum('total'))['total'] or 0

            total_orders_last_week = Order.objects.filter(
                outlet_id__in=user_outlet_ids,
                created_at__date__gte=start_of_week_before_last,
                created_at__date__lt=start_of_last_week,
                payment_status='success',
            ).count()
            
            total_orders_this_month = Order.objects.filter(
                outlet_id__in=user_outlet_ids,
                created_at__month=today.month,
                created_at__year=today.year,
                payment_status='success',
            ).count()

            total_revenue = Order.objects.filter(
                outlet_id__in=user_outlet_ids,
                payment_status='success'
            ).aggregate(total=Sum('total'))['total'] or 0

            total_days = Order.objects.filter(
                outlet_id__in=user_outlet_ids,
                payment_status='success',
            ).values('created_at__date').distinct().count()

            average_revenue = total_revenue / total_days if total_days else 0

            orders_data = (
                Order.objects.filter(
                    outlet_id__in=user_outlet_ids,
                    payment_status='success',
                ).values('created_at__date')
                .annotate(orderCount=Count('order_id'))
                .order_by('created_at__date')
            )[:7]
            
            revenue_data = (
                Order.objects.filter(
                    outlet_id__in=user_outlet_ids,
                    payment_status='success',
                ).values('created_at__date')
                .annotate(dailyRevenue=Sum('total'))
                .order_by('created_at__date')
            )[:7]

            orders = [
                {'date': order['created_at__date'].strftime('%Y-%m-%d'), 'orderCount': order['orderCount']}
                for order in orders_data
            ]
            revenue = [
                {'date': revenue['created_at__date'].strftime('%Y-%m-%d'), 'revenue': float(revenue['dailyRevenue'])}
                for revenue in revenue_data
            ]
            
            user_outlet_ids = Outlet.objects.filter(outlet_manager=user).values_list('id', flat=True)
            
            new_users_this_month = CustomUser.objects.filter(
                order__outlet_id__in=user_outlet_ids,
                # order__created_at__gte=start_of_month,
            ).annotate(
                order_count_in_month=Count('order', filter=Q(order__created_at__gte=start_of_month, order__outlet_id__in=user_outlet_ids))
            ).filter(
                order_count_in_month=1
            ).distinct().count()
            
            print('new_users_this_month')
            print(new_users_this_month)
            
            active_users_this_month = CustomUser.objects.filter(
                order__outlet_id__in=user_outlet_ids,
                # order__created_at__month=today.month,
                # order__created_at__year=today.year,
            ).annotate(
                previous_orders=Count('order', filter=Q(order__created_at__lt=start_of_month, order__outlet_id__in=user_outlet_ids))
            ).filter(
                previous_orders__gt=0
            ).distinct().count()
            
            print('active_users_this_month')
            print(active_users_this_month)
            
            # Data to cache
            demoData = {
                # graph
                'orders': orders,
                'revenue': revenue,
                # stats
                'total_revenue': total_revenue,
                'new_users_this_month': new_users_this_month,
                'active_users_this_month': active_users_this_month,
                'total_orders_this_month': total_orders_this_month,
                'todaysRevenue': round(float(todays_revenue), 2),
                'totalOrdersLastWeek': total_orders_last_week,
                'averageRevenue': round(float(average_revenue), 2),
            }

            # Cache the data for 24 hours
            cache.set(cache_key, demoData, cache_timeout)

        # Fetch today's total orders (not cached)
        start_of_today = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        todays_orders = Order.objects.filter(
            outlet_id__in=user_outlet_ids,
            created_at__gte=start_of_today
        ).count()

        # Add today's orders to the response data
        demoData['todaysOrders'] = todays_orders

        return Response(demoData, status=status.HTTP_200_OK)


class FoodCategoryListCreateView(APIView):
    permission_classes = []

    def get(self, request, menu_slug):
        menu = get_object_or_404(Menu, menu_slug=menu_slug)
        categories = FoodCategory.objects.filter(menu=menu).order_by('order', 'name')
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
        categories = FoodCategory.objects.filter(menu=menu).order_by('order', 'name')
        serializer = FoodCategorySerializer(categories, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = FoodItemSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class FoodItemByCategory(APIView):
    permission_classes = []
    def get(self, request, slug):
        category = get_object_or_404(FoodCategory, slug=slug)
        print(category, 'category')
        food_items = FoodItem.objects.filter(food_category=category)
        print(food_items, 'food_items')
        serializer = FoodItemSerializer(food_items, many=True)
        return Response(serializer.data)

class FoodItemDetailView(APIView):
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def get(self, request, slug):
        food_item = get_object_or_404(FoodItem, slug=slug)
        serializer = FoodItemSerializer(food_item)
        return Response(serializer.data)
    
    def put(self, request, slug):
        # try:
        print(request.FILES, request.data.get('image'), 'image')
        food_item = get_object_or_404(FoodItem, slug=slug)
        fields_to_update = ['name', 'food_type', 'description', 'price', 'image', 'featured', 'in_stock', 'tags']

        for key, value in request.data.items():
            if key in fields_to_update and key != 'image':
                setattr(food_item, key, value)
        
        # Handle image update separately
        if 'image' in request.FILES:
            food_item.image = request.FILES['image']
        
        food_item.save()
        serializer = FoodItemSerializer(food_item)
        return Response(serializer.data)
        
        # except Exception as e:
        #     return Response("Invalid data", status=status.HTTP_400_BAD_REQUEST)

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

         # Create or update the OrderTimelineItem for "Order Placed"
        timeline_item, created = OrderTimelineItem.objects.get_or_create(
            order=order,
            stage="Order Placed",
            defaults={
                'content': "Order has been placed successfully.",
                'done': True
            }
        )
        if not created:
            timeline_item.updated_at = timezone.now()
            timeline_item.save()

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

        if payment_method == 'cash' or payment_method == 'upi':
            menu = Menu.objects.get(outlet=order.outlet)
            channel_layer = get_channel_layer()
            order_data = OrderSerializer(order).data

            async_to_sync(channel_layer.group_send)(
                f'seller_{menu.menu_slug}',
                {
                    'type': 'seller_notification',
                    'message': order_data
                }
            )

            # notify outlet owner
            owner = menu.outlet.outlet_manager
            payload = json.dumps({
                "title": "New Order", 
                "body": "You have received a new order.", 
                "url": "https://seller.tacoza.co/orders"})
            send_notification_to_user(owner, payload)

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

        # Create or update the OrderTimelineItem for "Payment Initiated"
        timeline_item, created = OrderTimelineItem.objects.get_or_create(
            order=order,
            stage="Payment Initiated",
            defaults={
                'content': "Payment has been initiated.",
                'done': True
            }
        )
        if not created:
            timeline_item.updated_at = timezone.now()
            timeline_item.save()

        # Return the payment session id to the client to initiate payment
        return Response({
            "order_id": api_response.data.order_id,
            "payment_session_id": api_response.data.payment_session_id
        }, status=status.HTTP_201_CREATED)

        # except Exception as e:
        #     return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@method_decorator(csrf_exempt, name='dispatch')
class CashfreeWebhookView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        decoded_body = request.body.decode('utf-8')
        timestamp = request.headers.get('x-webhook-timestamp')
        signature = request.headers.get('x-webhook-signature')

        # try:
        cashfree = Cashfree()
        cashfree.PGVerifyWebhookSignature(signature, decoded_body, timestamp)

        body = request.data
        order_id = body['data']['order']['order_id']
        transaction_status = body['data']['payment']['payment_status']

        order = get_object_or_404(Order, order_id=order_id)
        stage = ""
        content = ""

        # Handle payment status
        if transaction_status == "SUCCESS":
            order.payment_status = 'success'
            order.payment_method = body['data']['payment']['payment_group']
            stage = "Payment Success"
            content = "Payment has been completed successfully."
        elif transaction_status == "PENDING":
            order.payment_status = 'pending'
            stage = "Payment Pending"
            content = "Payment is pending."
        else:
            order.payment_status = 'failed'
            stage = "Payment Failed"
            content = "Payment has failed."

        order.save()

        # Create or update the OrderTimelineItem for the payment status
        timeline_item, created = OrderTimelineItem.objects.get_or_create(
            order=order,
            stage=stage,
            defaults={
                'content': content,
                'done': True
            }
        )
        if not created:
            timeline_item.content = content
            timeline_item.updated_at = timezone.now()
            timeline_item.save()

        # Notify the shop owner if payment was successful
        if transaction_status == "SUCCESS":
            menu = Menu.objects.get(outlet=order.outlet)
            channel_layer = get_channel_layer()
            order_data = OrderSerializer(order).data

            async_to_sync(channel_layer.group_send)(
                f'seller_{menu.menu_slug}',
                {
                    'type': 'seller_notification',
                    'message': order_data
                }
            )

            # notify outlet owner
            owner = menu.outlet.outlet_manager
            payload = json.dumps({
                "title": "New Order", 
                "body": "You have received a new order.", 
                "url": "https://seller.tacoza.co/orders"})
            send_notification_to_user(owner, payload)

        return JsonResponse({"status": "success"})


class PaymentStatusAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, order_id):
        try:
            api_response = Cashfree().PGOrderFetchPayments(x_api_version, order_id, None)
            print(api_response.data)
            return Response(api_response.data)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class SettelmentStatusAPIView(APIView):

    def get(self, request, days):
        user = request.user
        outlet = Outlet.objects.filter(outlet_manager=user).first()
        current_date = timezone.now().date()

        print(outlet, 'outlet')
        # Get orders that are at least 3 days old and payment_status is 'success'
        days_ago = current_date - timedelta(days=days)
        print(days_ago, 'days_ago')
        successful_orders = Order.objects.filter(
            outlet=outlet,
            payment_status='success',
            created_at__date__gte=days_ago,
        ).exclude(payment_method='cash')
        
        print(successful_orders, 'successful_orders')

        # Aggregate by day and calculate total amount
        orders_by_day = successful_orders.values('created_at__date').annotate(total_amount=Sum('total'))
        print(orders_by_day)
        
        formatted_orders = [
            {"date": str(order['created_at__date']), "totalPayment": order['total_amount']}
            for order in orders_by_day
        ]
        
        payouts_by_day = {}
        # Iterate over each day's orders and create/update Payout instance
        for order_group in orders_by_day:
            payout_date = order_group['created_at__date']
            total_amount = order_group['total_amount']
            payout = Payouts.objects.filter(date=payout_date, outlet=outlet).first()
            # Check if a Payouts entry exists for this date
            if not payout:
                # Create a new Payouts entry
                payout = Payouts.objects.create(
                    outlet=outlet,
                    date=payout_date,
                    amount=total_amount,
                    status='pending'  # Initially set to pending
                )
            payouts_by_day[f"{payout_date}"] = {
                "amount": payout.amount,
                "status": payout.status
            }
            print(payout_date, 'payout_date')
        
        return Response({"orders_by_day": formatted_orders, "payouts_by_day": payouts_by_day}, status=status.HTTP_200_OK)


# Custom pagination class
class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10  # Default items per page
    page_size_query_param = 'page_size'
    max_page_size = 100


class OrderList(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = OrderSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    ordering_fields = ['created_at']

    def get_queryset(self):
        user = self.request.user
        queryset = Order.objects.all()

        # Filtering based on user role
        if user.role == 'owner':
            outlet = Outlet.objects.filter(outlet_manager=user).first()
            queryset = queryset.filter(outlet=outlet)
        else:
            queryset = queryset.filter(user=user)
            
        print(queryset, 'queryset')
        # Date filtering
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        specific_date = self.request.query_params.get('date')
        
        print(start_date, end_date, specific_date, 'dates')
        
        if start_date and end_date:
            # Filter for a date range
            queryset = queryset.filter(created_at__date__gte=start_date, created_at__date__lte=end_date)
        elif specific_date:
            # Filter for a specific date
            queryset = queryset.filter(created_at__date=parse_date(specific_date))
        
        
        print(queryset, 'queryset')

        return queryset 


class OrderDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, order_id):
        user = request.user
        order = get_object_or_404(Order, order_id=order_id)
        try:
            api_response = Cashfree().PGOrderFetchPayments(x_api_version, order_id, None)
            print(api_response.data)
        except:
            print("Something Wrong")

        if user.role == 'owner' and order.outlet.outlet_manager != user:
            return Response({"detail": "You are not authorized to view this order."}, status=status.HTTP_403_FORBIDDEN)
        elif user.role == 'customer' and order.user != user:
            return Response({"detail": "You are not authorized to view this order."}, status=status.HTTP_403_FORBIDDEN)
        serializer = OrderSerializer(order)
        return Response(serializer.data)

    # to update payment status
    def put(self, request, order_id):
        user = request.user
        order = get_object_or_404(Order, order_id=order_id)
        if order.outlet.outlet_manager != user:
            return Response({"detail": "You are not authorized to update this order."}, status=status.HTTP_403_FORBIDDEN)

        data = request.data
        payment_status = data.get('status')
        if payment_status not in ['success', 'pending', 'cancelled']:
            return Response({"detail": "Invalid status."}, status=status.HTTP_400_BAD_REQUEST)

        if payment_status == 'cancelled':
            order.status = 'cancelled'
            order.save()

            # Create or update the OrderTimelineItem for "Order Cancelled"
            timeline_item, created = OrderTimelineItem.objects.get_or_create(
                order=order,
                stage="Order Cancelled",
                defaults={
                    'content': "Order has been cancelled.",
                    'done': True
                }
            )
            if not created:
                timeline_item.updated_at = timezone.now()
                timeline_item.save()

            # Notify the user
            payload = json.dumps({
                "title": "Order Cancelled",
                "body": "Your order has been cancelled.",
                "url": f"https://app.tacoza.co/order/{order.order_id}"
            })
            send_notification_to_user(order.user, payload)
            return Response({"message": "Order cancelled successfully."}, status=status.HTTP_200_OK)

        order.payment_status = payment_status
        order.save()

        if payment_status == 'success':
            # Create or update the OrderTimelineItem for "Payment Success"
            timeline_item, created = OrderTimelineItem.objects.get_or_create(
                order=order,
                stage="Payment Success",
                defaults={
                    'content': "Payment recived.",
                    'done': True
                }
            )
            if not created:
                timeline_item.updated_at = timezone.now()
                timeline_item.save()
        return Response({"message": "Payment status updated successfully."}, status=status.HTTP_200_OK)


class LiveOrders(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        outlet = Outlet.objects.filter(outlet_manager=user).first()

        # return all orders of current date categorized by status, with payment_status 'success' or payment_method 'cash'
        orders = Order.objects.filter(
            outlet=outlet,
            created_at__date=datetime.datetime.now().date(),
            payment_status='success'  # Payment status condition
        ).order_by('-created_at') | Order.objects.filter(
            outlet=outlet,
            created_at__date=datetime.datetime.now().date(),
            payment_method='cash'  # Payment method condition
        ).order_by('-created_at') | Order.objects.filter(
            outlet=outlet,
            created_at__date=datetime.datetime.now().date(),
            outlet__outlet_type='lite'
        ).order_by('-created_at')

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
        status_map = {
            'completed': 'Order Completed',
            'processing': 'Order Processing',
            'pending': 'Order Placed'
        }

        new_status = data.get('status')
        if new_status not in status_map:
            return Response({"detail": "Invalid status."}, status=status.HTTP_400_BAD_REQUEST)

        # Update the order status and timestamps
        order.status = new_status
        order.updated_at = timezone.now()
        
        order.save()

        # Define the corresponding stage and content
        stage = status_map[new_status]
        content = {
            'completed': "Order has been completed.",
            'processing': "Order is being prepared.",
            'pending': "Order has been placed successfully."
        }[new_status]

        # Check if an OrderTimelineItem with the same stage already exists
        timeline_item, created = OrderTimelineItem.objects.get_or_create(
            order=order,
            stage=stage,
            defaults={
                'content': content,
                'done': True
            }
        )

        # If the timeline item already exists, update its timestamp and content if needed
        if not created:
            timeline_item.content = content
            timeline_item.updated_at = timezone.now()
            timeline_item.save()

        # Prepare the notification payload
        payload = json.dumps({
            "title": stage,
            "body": content,
            "url": f"https://app.tacoza.co/order/{order.order_id}"
        })
        
        # Send a notification to the user
        send_notification_to_user(order.user, payload)

        # Return a success response
        return Response({"message": f"Order {new_status} successfully."}, status=status.HTTP_200_OK)


class OutleDetailView(APIView):
    permission_classes = []

    def get(self, request, menu_slug):
        menu = get_object_or_404(Menu, menu_slug=menu_slug)
        outlet = menu.outlet
        serializer = OutletSerializer(outlet)
        return Response(serializer.data)


class OutletsListAPIView(APIView):
    permission_classes = []

    def get(self, request):
        outlets = Outlet.objects.all()
        serializer = OutletSerializer(outlets, many=True)
        return Response(serializer.data)


class OutletListCreateView(APIView):
    def get(self, request):
        user = request.user
        role_serializer_map = {
            CUSTOMER: CustomerOutletSerializer,
            OWNER: OwnerOutletSerializer,
        }
        outlet = Outlet.objects.filter(outlet_manager=user).first()
        role_based_serializer = RoleBasedSerializer(role_serializer_map)
        # Get the serializer class based on the user's role
        serializer_class = role_based_serializer.get_serializer_class(user.role)
        if not serializer_class:
            return Response({"error": "You are not authorized to view this data."}, status=status.HTTP_403_FORBIDDEN)
        serializer = serializer_class(outlet)
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
        user = request.user
        coupons = DiscountCoupon.objects.filter(outlet__outlet_manager=user)
        serializer = DiscountCouponDetailSerializer(coupons, many=True)
        return Response(serializer.data)


class ApplicableOffersAPIView(APIView):

    def get(self, request):
        user = request.user
        cart = Cart.objects.get(user=user)  # Assuming a user can only have one active cart

        print(timezone.now().date())
        print(DiscountCoupon.objects.first().valid_from)
        # Get all active discount coupons that haven't expired and haven't reached their use limit.
        coupons = DiscountCoupon.objects.filter(
            valid_from__gte=timezone.now().date(),
            valid_to__lte=timezone.now().date()
        )

        print(coupons)

        # Create the serializer with context data
        # serializer = DiscountCouponSerializer(coupons, many=True, context={'user': user, 'cart': cart})
        # serialized_data = serializer.data

        # # Filter to find the best offer based on applicability and discount value
        # applicable_offers = [offer for offer in serialized_data if offer['is_applicable']]
        # best_offer = max(applicable_offers, key=lambda x: x['discount_value'], default=None)

        # return Response({
        #     'offers': serialized_data,
        #     'best_offer': best_offer
        # })
        return Response({"offers": [], "best_offer": None})
