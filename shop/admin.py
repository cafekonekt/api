from django.contrib import admin
from shop.models import (
    Shop, 
    Outlet, 
    Menu, 
    Variant, 
    FoodItem, 
    FoodCategory, 
    SubCategory, 
    AddonCategory, 
    Addon, 
    Table, 
    TableArea,
    VariantCategory,
    ItemVariant,
    Order,
    OrderItem,
    Cart,
    CartItem
)

class VariantAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'category', 'description')

class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_id', 'status', 'table', 'outlet', 'total', 'created_at')

admin.site.register(Shop)
admin.site.register(Outlet)
admin.site.register(Menu)
admin.site.register(Variant, VariantAdmin)
admin.site.register(FoodItem)
admin.site.register(FoodCategory)
admin.site.register(SubCategory)
admin.site.register(AddonCategory)
admin.site.register(Addon)
admin.site.register(Table)
admin.site.register(TableArea)
admin.site.register(VariantCategory)
admin.site.register(ItemVariant)
admin.site.register(Order, OrderAdmin)
admin.site.register(OrderItem)
admin.site.register(Cart)
admin.site.register(CartItem)
