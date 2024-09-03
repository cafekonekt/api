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
    ItemVariant
)

class VariantAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'category', 'description')


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