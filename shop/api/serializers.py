from rest_framework import serializers
from django.conf import settings
from shop.models import (
    FoodCategory,
    SubCategory,
    FoodItem ,
    FoodTag,
    Addon,
    AddonCategory,
    Outlet,
    OperatingHours,
    OutletImage,
    ItemVariant,
    Variant,
    OrderTimelineItem,
    CartItem,
    Order,
    OrderItem,
    Table,
    TableArea,
    Menu,
    DiscountCoupon)
from authentication.api.serializers import UserSerializer
from django.db.models import Count
from django.utils import timezone

class FoodTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = FoodTag
        fields = ['id', 'name']


class AddonSerializer(serializers.ModelSerializer):
    applied_variant = serializers.SerializerMethodField()

    class Meta:
        model = Addon
        fields = ['id', 'name', 'addon_type', 'price', 'description', 'applied_variant']

    def get_applied_variant(self, obj):
        """Return the variant name."""
        return [variant.id for variant in obj.item_variant.all()] if obj.item_variant else None


class AddonCategorySerializer(serializers.ModelSerializer):
    addons = serializers.SerializerMethodField()

    class Meta:
        model = AddonCategory
        fields = ['id', 'name', 'addons']

    def get_addons(self, obj):
        """Return the addons of the category."""
        addons = Addon.objects.filter(category=obj)
        return AddonSerializer(addons, many=True).data

 
class ItemVariantSerializer(serializers.ModelSerializer):
    variant_slug = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()

    class Meta:
        model = ItemVariant
        fields = ['id', 'price', 'name', 'variant_slug']

    def get_name(self, obj):
        """Return the variant name."""
        return '-'.join([str(variant.name) for variant in obj.variant.all()])
    
    def get_variant_slug(self, obj):
        """Return the sorted variant IDs joined by a dash."""
        return '-'.join([str(variant.id) for variant in sorted(obj.variant.all(), key=lambda v: v.id)])


class FoodItemSerializer(serializers.ModelSerializer):
    addons = AddonSerializer(many=True, read_only=True)
    tags = FoodTagSerializer(many=True, read_only=True)
    food_subcategory = serializers.SerializerMethodField()
    food_category = serializers.SerializerMethodField()
    rating = serializers.SerializerMethodField()
    variant = serializers.SerializerMethodField()
    steps = serializers.SerializerMethodField()
    item_variants = ItemVariantSerializer(many=True, read_only=True)    
    price = serializers.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        model = FoodItem
        fields = [
            'id',
            'name',
            'food_type',
            'food_category',
            'food_subcategory',
            'description',
            'price',
            'image_url',
            'in_stock',
            'featured',
            'addons',
            'tags',
            'prepration_time',
            'slug',
            'rating',
            'steps',
            'variant',
            'item_variants']

    def get_food_category(self, obj):
        """Return the category name if it exists, else None."""
        return obj.food_category.name if obj.food_category else None

    def get_food_subcategory(self, obj):
        """Return the subcategory name if it exists, else None."""
        return obj.food_subcategory.name if obj.food_subcategory else None

    def get_variant(self, obj):
        # Fetch all variant categories associated with the food item
        categories = obj.variant.all()
        # Fetch all item variants for the food item
        item_variants = ItemVariant.objects.filter(food_item=obj)
        # If there are no variants, return None
        if not categories.exists():
            return None
        # Get the first variant category
        category = categories.first()
        # Find all options under this category
        options = Variant.objects.filter(category=category)


        # Build a list to hold the options data
        options_data = []
        for option in options:
            # List to hold the included categories
            included_categories = [category]
            # List to hold the included options
            included_options = [option]
            # Get the related item variant for the current option
            num_included = len(included_options)
            related_item_variant = item_variants.filter(variant__in=included_options).annotate(num_included=Count('variant')).filter(num_included=num_included).first()

            # Check if there are next-level variants for the current option
            next_variants_data = None
            if related_item_variant:
                # Get the nested options for the next variant
                next_variants_data = self._build_next_variant_data(included_categories, included_options, categories, item_variants)
            
                # Build option data
                option_data = {
                    "id": option.id,
                    "name": option.name,
                    "price": float(related_item_variant.price) if len(categories) == 1 else None,  # Only show price at the final level
                    "variant": next_variants_data
                }
                options_data.append(option_data)

        # Build the structure for the current variant category
        variant_data = {
            "id": category.id,
            "name": category.name,
            "options": options_data
        }
        
        return variant_data

    def get_steps(self, obj):
        """Return the preparation steps."""
        return len(obj.variant.all())

    def _build_next_variant_data(self, included_categories, included_options, categories, item_variants):
        """Helper method to recursively build the next variant options."""
        if len(included_categories) == len(categories):
            return None

        # Find the next category that has not been included yet
        next_category = None
        for category in categories:
            if category not in included_categories:
                next_category = category
                break
        if not next_category:
            return None

        options = Variant.objects.filter(category=next_category)
        included_categories.append(next_category)

        options_data = []
        for option in options:
            included_options.append(option)
            num_included = len(included_options)
            related_item_variant = item_variants.filter(variant__in=included_options).annotate(num_included=Count('variant')).filter(num_included=num_included).first()

            next_variants_data = None
            if related_item_variant:
                next_variants_data = self._build_next_variant_data(included_categories, included_options, categories, item_variants)
            
                option_data = {
                    "id": option.id,
                    "name": option.name,
                    "price": float(related_item_variant.price) if len(categories) == len(included_categories) else None,  # Show price only at the final level
                    "variant": next_variants_data
                }
                options_data.append(option_data)
            included_options.pop()
        
        return {
            "id": next_category.id,
            "name": next_category.name,
            "options": options_data
        }

    def get_rating(self, obj):
        """Return the average rating of the food item."""
        return 4.5
    
    def to_representation(self, instance):
        """Override to_representation to handle empty addons."""
        representation = super().to_representation(instance)
        if not instance.addons.exists():
            representation['addons'] = None
        if not instance.variant.exists():
            representation['variants'] = None
        return representation


class CartItemSerializer(serializers.ModelSerializer):
    food_item = FoodItemSerializer()
    addons = AddonSerializer(many=True)
    variant = serializers.SerializerMethodField()
    totalPrice = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = ['id', 'item_id', 'food_item', 'variant', 'quantity', 'addons', 'totalPrice']

    def get_totalPrice(self, obj):
        """Return the total price of the cart item."""
        return obj.get_total_price()

    def get_variant(self, obj):
        """Return the variant name."""
        if obj.variant:
            return {
                "name": '-'.join([str(variant.name) for variant in obj.variant.variant.all()]),
                "price": float(obj.variant.price)
            }


class SubCategorySerializer(serializers.ModelSerializer):
    food_items = FoodItemSerializer(many=True, read_only=True)

    class Meta:
        model = SubCategory
        fields = ['id', 'name', 'food_items']


class FoodCategorySerializer(serializers.ModelSerializer):
    sub_categories = SubCategorySerializer(many=True, read_only=True)
    food_items = serializers.SerializerMethodField()

    class Meta:
        model = FoodCategory
        fields = ['id', 'name', 'sub_categories', 'food_items', 'active', 'image_url', 'slug']

    def get_food_items(self, obj):
        """Return food items directly under this category (those without a subcategory)."""
        return FoodItemSerializer(obj.food_items.filter(food_subcategory__isnull=True), many=True).data


class OutletSerializer(serializers.ModelSerializer):
    SERVICE_CHOICES = [
        ('dine_in', 'Dine-In'),
        ('takeaway', 'Takeaway'),
        ('delivery', 'Delivery')
    ]
    TYPE_CHOICES = [
        ('veg', 'Veg'),
        ('nonveg', 'Non-Veg'),
        ('egg', 'Egg')
    ]
    PAYMENT_CHOICES = [
        ('cash', 'Cash'),
        ('online', 'Online')
    ]
    logo = serializers.SerializerMethodField()
    services = serializers.ListField(
        child=serializers.ChoiceField(choices=[choice[0] for choice in SERVICE_CHOICES])
    )
    type = serializers.ListField(
        child=serializers.ChoiceField(choices=[choice[0] for choice in TYPE_CHOICES])
    )
    payment_methods = serializers.ListField(
        child=serializers.ChoiceField(choices=[choice[0] for choice in PAYMENT_CHOICES])
    )
    gallery = serializers.SerializerMethodField()
    rating = serializers.SerializerMethodField()
    menu_slug = serializers.SerializerMethodField()

    class Meta:
        model = Outlet
        fields = [
            'id',
            'name',
            'payment_link',
            'rating',
            'menu_slug',
            'description',
            'address',
            'location',
            'minimum_order_value',
            'average_preparation_time',
            'email',
            'phone',
            'whatsapp',
            'logo',
            'gallery',
            'shop',
            'services',
            'type',
            'payment_methods',
            'slug']
        depth = 2

    def get_menu_slug(self, obj):
        """Return the menu slug."""
        menu = Menu.objects.filter(outlet=obj).first()
        return menu.menu_slug if menu else None

    def get_logo(self, obj):
        """Return the image URL if it exists, else None."""
        if obj.logo:
            return f"https://api.tacoza.co{obj.logo.url}"
        return None

    def get_gallery(self, obj):
        """Return the image URLs of the gallery."""
        images = OutletImage.objects.filter(outlet=obj)
        return [f"https://api.tacoza.co{image.image.url}" for image in images]

    def to_representation(self, instance):
        """Convert the comma-separated string back into a list for representation."""
        representation = super().to_representation(instance)
        representation['services'] = instance.services.split(',')
        representation['type'] = instance.type.split(',')
        representation['payment_methods'] = instance.payment_methods.split(',')
        return representation
    
    def get_rating(self, obj):
        """Return the average rating of the outlet."""
        return 4.5

    def to_internal_value(self, data):
        """Convert the list of services to a comma-separated string before saving."""
        internal_value = super().to_internal_value(data)
        internal_value['services'] = ','.join(internal_value['services'])
        return internal_value


class OwnerOutletSerializer(OutletSerializer):
    operational_timings = serializers.SerializerMethodField()
    is_open = serializers.SerializerMethodField()

    class Meta(OutletSerializer.Meta):
        model = Outlet
        fields = [
            'id',
            'name',
            'payment_link',
            'rating',
            'menu_slug',
            'description',
            'address',
            'location',
            'minimum_order_value',
            'average_preparation_time',
            'email',
            'phone',
            'whatsapp',
            'logo',
            'gallery',
            'shop',
            'services',
            'type',
            'payment_methods',
            'slug',
            'outlet_type',
            'operational_timings',
            'is_open',
            'name'
        ]
    
    def get_operational_timings(self, obj):
        """Return the operational timings."""
        timings = OperatingHours.objects.filter(outlet=obj)
        return [{
            "day": timing.day_of_week,
            "active": timing.active,
            "opening_time": timing.opening_time,
            "closing_time": timing.closing_time
        } for timing in timings]
        
    def get_is_open(self, obj):
        """Return whether the outlet is open."""
        return obj.is_open()


class CustomerOutletSerializer(OutletSerializer):
    class Meta(OutletSerializer.Meta):
        model = Outlet


class OrderItemSerializer(serializers.ModelSerializer):
    food_item = FoodItemSerializer()
    addons = AddonSerializer(many=True)
    variant = serializers.SerializerMethodField()
    totalPrice = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = ['id', 'food_item', 'variant', 'quantity', 'addons', 'totalPrice']

    def get_variant(self, obj):
        """Return the variant name."""
        if not obj.variant:
            return None
        return '-'.join([str(variant.name) for variant in obj.variant.variant.all()])

    def get_totalPrice(self, obj):
        """Return the total price of the order item."""
        return obj.get_total_price()


class OrderTimelineSerializer(serializers.Serializer):
    class Meta:
        model = OrderTimelineItem
        ordering = ['created_at']
        fields = ['stage', 'done', 'content', 'created_at']


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True)
    user = UserSerializer()
    table = serializers.SerializerMethodField()
    total = serializers.SerializerMethodField()
    outlet = OutletSerializer()
    order_timeline = serializers.SerializerMethodField()
    created_at = serializers.SerializerMethodField()
    updated_at = serializers.SerializerMethodField()
    avg_preparation_time = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'order_id',
            'payment_session_id',
            'order_timeline',
            'user',
            'outlet',
            'items',
            'table',
            'cooking_instructions',
            'order_type',
            'total',
            'status',
            'payment_status',
            'payment_method',
            'avg_preparation_time',
            'created_at',
            'updated_at'
        ]

    def get_total(self, obj):
        return float(obj.total)

    def get_order_timeline(self, obj):
        """Return the order timeline."""
        order_timelines = OrderTimelineItem.objects.filter(order=obj)
        return [{
            "stage": order_timeline.stage,
            "done": order_timeline.done,
            "content": order_timeline.content,
            "created_at": order_timeline.created_at.isoformat()  # Convert to ISO 8601 string
        } for order_timeline in order_timelines]

    def get_created_at(self, obj):
        """Return the created_at as an ISO 8601 string."""
        return obj.created_at.isoformat() if obj.created_at else None

    def get_updated_at(self, obj):
        """Return the updated_at as an ISO 8601 string."""
        return obj.updated_at.isoformat() if obj.updated_at else None

    def get_user(self, obj):
        """Return the user name."""
        return obj.user.name

    def get_table(self, obj):
        """Return the table name."""
        return obj.table.name if obj.table else None
    
    def get_avg_preparation_time(self, obj):
        """Return the average preparation time of the order."""
        return obj.outlet.average_preparation_time


class CheckoutSerializer(serializers.Serializer):
    class Meta:
        model = Order
        fields = ["user", "outlet", "total", "status", "order_type", "table", "cooking_instructions"]


class TableSerializer(serializers.ModelSerializer):
    area = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()
    outlet = serializers.SerializerMethodField()

    class Meta:
        model = Table
        fields = ['table_id', 'name', 'outlet', 'area', 'capacity', 'url']

    def get_area(self, obj):
        """Return the area name of the table."""
        return obj.area.name if obj.area else None

    def get_url(self, obj):
        """Return the URL of the table."""
        return obj.get_url()

    def get_outlet(self, obj):
        """Return the outlet name of the table."""
        return obj.outlet.name if obj.outlet else None


class AreaSerializer(serializers.ModelSerializer):
    outlet = OutletSerializer()
    class Meta:
        model = TableArea
        fields = ['id', 'name', 'outlet']


class DiscountCouponDetailSerializer(serializers.ModelSerializer):
    is_active = serializers.SerializerMethodField()
    usage = serializers.SerializerMethodField()
    class Meta:
        model = DiscountCoupon
        fields = ['id', 
                  'outlet',
                  'coupon_code', 
                  'discount_type', 
                  'discount_value', 
                  'minimum_order_value', 
                  'max_order_value', 
                  'use_limit',
                  'use_limit_per_user',
                  'valid_from', 
                  'application_type',
                  'valid_to', 
                  'usage',
                  'is_active']
    
    def get_usage(self, obj):
        """Return the usage count of the coupon."""
        return obj.get_usage_count()

    def get_is_active(self, obj):
        """Calculate if the coupon is active."""
        today = timezone.now().date()
        return obj.valid_from <= today <= obj.valid_to


class DiscountCouponSerializer(serializers.ModelSerializer):
    is_applicable = serializers.SerializerMethodField()
    is_active = serializers.SerializerMethodField()

    class Meta:
        model = DiscountCoupon
        fields = [
            'coupon_code',
            'discount_type',
            'discount_value',
            'minimum_order_value',
            'max_order_value',
            'application_type',
            'is_applicable',
            'is_active',
        ]

    def get_is_applicable(self, obj):
        """
        Checks if the coupon is applicable for the user and their cart.
        """
        user = self.context['user']
        cart = self.context['cart']
        return obj.is_applicable(user, cart)

    def get_is_active(self, obj):
        """
        Checks if the coupon is active based on the cart's total value and usage limits.
        """
        cart = self.context['cart']
        cart_total = sum([item.get_total_price() for item in cart.items.all()])

        # Check if the coupon is within usage limits
        if obj.get_usage_count() >= obj.use_limit:
            return False

        # Check if the cart total is within the minimum and maximum order value limits
        return obj.minimum_order_value <= cart_total <= obj.max_order_value
