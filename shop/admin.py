from django.contrib import admin
from shop.models import (
    Shop, 
    Outlet, 
    OutletImage,
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
    CartItem,
    DiscountCoupon,
)
from import_export import resources
from import_export.admin import ImportExportModelAdmin

###################
class FoodItemResource(resources.ModelResource):
    class Meta:
        model = FoodItem

class FoodItemAdmin(ImportExportModelAdmin):
    resource_class = FoodItemResource
###################
class FoodCategoryResource(resources.ModelResource):
    class Meta:
        model = FoodCategory

class FoodCategoryAdmin(ImportExportModelAdmin):
    resource_class = FoodCategoryResource
###################
class SubCategoryResource(resources.ModelResource):
    class Meta:
        model = SubCategory

class SubCategoryAdmin(ImportExportModelAdmin):
    resource_class = SubCategoryResource
###################
class VariantResource(resources.ModelResource):
    class Meta:
        model = Variant

class VariantAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'category')
    resource_class = VariantResource
###################
class ItemVariantResource(resources.ModelResource):
    class Meta:
        model = ItemVariant

class ItemVariantAdmin(ImportExportModelAdmin):
    resource_class = ItemVariantResource
###################
class AddonResource(resources.ModelResource):
    class Meta:
        model = Addon

class AddonAdmin(ImportExportModelAdmin):
    resource_class = AddonResource
###################
class VariantCategoryResource(resources.ModelResource):
    class Meta:
        model = VariantCategory

class VariantCategoryAdmin(ImportExportModelAdmin):
    resource_class = VariantCategoryResource
###################
class AddonCategoryResource(resources.ModelResource):
    class Meta:
        model = AddonCategory

class AddonCategoryAdmin(ImportExportModelAdmin):
    resource_class = AddonCategoryResource


admin.site.register(Shop)
admin.site.register(Outlet)
admin.site.register(OutletImage)
admin.site.register(Menu)
admin.site.register(FoodItem, FoodItemAdmin)
admin.site.register(FoodCategory, FoodCategoryAdmin)
admin.site.register(Variant, VariantAdmin)
admin.site.register(ItemVariant, ItemVariantAdmin)
admin.site.register(SubCategory, SubCategoryAdmin)
admin.site.register(Addon, AddonAdmin)
admin.site.register(AddonCategory, AddonCategoryAdmin)
admin.site.register(VariantCategory, VariantCategoryAdmin)
admin.site.register(Table)
admin.site.register(TableArea)
admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(Cart)
admin.site.register(CartItem)
admin.site.register(DiscountCoupon)
