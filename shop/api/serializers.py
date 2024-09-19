from rest_framework import serializers
from rest_framework import viewsets
from shop.models import (
    FoodCategory, 
    SubCategory, 
    FoodItem , 
    FoodTag,
    Addon, 
    AddonCategory,
    Outlet, 
    OutletImage,
    ItemVariant,
    CartItem,
    Order,
    OrderItem,
    Table,
    TableArea,
    Menu)
from django.conf import settings

class FoodTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = FoodTag
        fields = ['id', 'name']

class AddonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Addon
        fields = ['id', 'name', 'price', 'description']

class AddonCategorySerializer(serializers.ModelSerializer):
    addons = serializers.SerializerMethodField()
    class Meta:
        model = AddonCategory
        fields = ['id', 'name', 'addons']
    
    def get_addons(self, obj):
        """Return the addons of the category."""
        addons = Addon.objects.filter(category=obj)
        return AddonSerializer(obj.addons.filter(category=obj), many=True).data
    
class ItemVariantSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    class Meta:
        model = ItemVariant
        fields = ['id', 'name', 'price']
    
    def get_name(self, obj):
        """Return the variant name."""
        return obj.variant.name

class FoodItemSerializer(serializers.ModelSerializer):
    addons = AddonSerializer(many=True, read_only=True)
    tags = FoodTagSerializer(many=True, read_only=True)
    food_subcategory = serializers.SerializerMethodField()
    status_color = serializers.SerializerMethodField()
    food_category = serializers.SerializerMethodField()
    rating = serializers.SerializerMethodField()
    variants = serializers.SerializerMethodField()

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
            'addons', 
            'tags', 
            'prepration_time', 
            'status_color', 
            'rating',
            'variants']

    def get_food_category(self, obj):
        """Return the category name if it exists, else None."""
        return obj.food_category.name if obj.food_category else None

    def get_food_subcategory(self, obj):
        """Return the subcategory name if it exists, else None."""
        return obj.food_subcategory.name if obj.food_subcategory else None
    
    def get_variants(self, obj):
        """Return the variants of the food item."""
        variants = ItemVariant.objects.filter(food_item=obj)
        if variants:
            return { "name": obj.variant.name, "type": ItemVariantSerializer(variants, many=True).data}
        return None

    def get_status_color(self, obj):
        """Return the status color based on food_type."""
        if obj.food_type == 'veg':
            return 'text-green-500'
        elif obj.food_type == 'egg':
            return 'text-yellow-500'
        elif obj.food_type == 'nonveg':
            return 'text-red-500'
        return 'text-green-500' 
    
    def get_rating(self, obj):
        """Return the average rating of the food item."""
        return 4.5

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
        item_variant = ItemVariant.objects.filter(food_item=obj.food_item, variant=obj.variant).first()
        if obj.variant:
            return {
                "name": obj.variant.name,
                "price": item_variant.price
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
        fields = ['id', 'name', 'sub_categories', 'food_items']

    def get_food_items(self, obj):
        """Return food items directly under this category (those without a subcategory)."""
        return FoodItemSerializer(obj.food_items.filter(food_subcategory__isnull=True), many=True).data

class ClientFoodCategorySerializer(serializers.ModelSerializer):
    sub_categories = SubCategorySerializer(many=True, read_only=True)
    food_items = serializers.SerializerMethodField()

    class Meta:
        model = FoodCategory
        fields = ['id', 'name', 'sub_categories', 'food_items']

    def get_food_items(self, obj):
        """Return food items directly under this category (those without a subcategory)."""
        return FoodItemSerializer(obj.food_items.filter(food_subcategory__isnull=True), many=True).data

class OutletSerializer(serializers.ModelSerializer):
    SERVICE_CHOICES = [
        ('dine_in', 'Dine-In'),
        ('takeaway', 'Takeaway'),
        ('delivery', 'Delivery')
    ]
    logo = serializers.SerializerMethodField()
    services = serializers.ListField(
        child=serializers.ChoiceField(choices=[choice[0] for choice in SERVICE_CHOICES])
    )
    gallery = serializers.SerializerMethodField()

    class Meta:
        model = Outlet
        fields = ['id', 'name', 'description', 'address', 'location', 'minimum_order_value', 'average_preparation_time', 'email', 'phone', 'whatsapp', 'logo', 'gallery', 'shop', 'services', 'slug']
        depth = 2

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
        return representation

    def to_internal_value(self, data):
        """Convert the list of services to a comma-separated string before saving."""
        internal_value = super().to_internal_value(data)
        internal_value['services'] = ','.join(internal_value['services'])
        return internal_value

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
        return obj.variant.name if obj.variant else None
    
    def get_totalPrice(self, obj):
        """Return the total price of the order item."""
        return obj.get_total_price()

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True)
    user = serializers.SerializerMethodField()
    table = serializers.SerializerMethodField()
    total = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ['order_id', 'payment_session_id', 'user', 'outlet', 'items', 'table', 'cooking_instructions', 'order_type', 'total', 'status', 'created_at', 'updated_at']
        depth = 2

    def get_total(self, obj):
        return float(obj.total)

    def get_user(self, obj):
        """Return the user name."""
        return obj.user.name
    
    def get_table(self, obj):
        """Return the table name."""
        return obj.table.name if obj.table else None
    
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
