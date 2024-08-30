from rest_framework import serializers
from rest_framework import viewsets
from shop.models import FoodCategory, SubCategory, FoodItem , FoodTag, Addon, Outlet

class FoodTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = FoodTag
        fields = ['id', 'name']

class AddonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Addon
        fields = ['id', 'name', 'price', 'description']

class FoodItemSerializer(serializers.ModelSerializer):
    addons = AddonSerializer(many=True, read_only=True)
    tags = FoodTagSerializer(many=True, read_only=True)
    food_subcategory = serializers.SerializerMethodField()
    status_color = serializers.SerializerMethodField()
    food_category = serializers.SerializerMethodField()

    class Meta:
        model = FoodItem
        fields = ['id', 'name', 'food_type', 'food_category', 'food_subcategory', 'description', 'price', 'image_url', 'addons', 'tags', 'prepration_time', 'status_color']

    def get_food_category(self, obj):
        """Return the category name if it exists, else None."""
        return obj.food_category.name if obj.food_category else None

    def get_food_subcategory(self, obj):
        """Return the subcategory name if it exists, else None."""
        return obj.food_subcategory.name if obj.food_subcategory else None

    def get_status_color(self, obj):
        """Return the status color based on food_type."""
        if obj.food_type == 'veg':
            return 'text-green-500'
        elif obj.food_type == 'egg':
            return 'text-yellow-500'
        elif obj.food_type == 'nonveg':
            return 'text-red-500'
        return 'text-green-500' 

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


class OutletSerializer(serializers.ModelSerializer):
    class Meta:
        model = Outlet
        fields = ['id', 'name', 'address', 'phone', 'image_url']
