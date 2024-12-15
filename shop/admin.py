from django.contrib import admin
from shop.models import (
    Shop,
    Outlet,
    OperatingHours,
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
    Payouts,
    OrderItem,
    Cart,
    CartItem,
    DiscountCoupon,
    OrderTimelineItem,
    ItemRelation,
    OutletDocument
)
from import_export import resources
from import_export.admin import ImportExportModelAdmin

###################
class FoodItemResource(resources.ModelResource):
    class Meta:
        model = FoodItem

class FoodItemAdmin(ImportExportModelAdmin):
    list_display = ('id', 'name', 'food_category', 'menu', 'price')
    resource_class = FoodItemResource
###################
class FoodCategoryResource(resources.ModelResource):
    class Meta:
        model = FoodCategory

class FoodCategoryAdmin(ImportExportModelAdmin):
    list_display = ('id', 'name', 'menu')
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
###################
class ItemRelationAdmin(admin.ModelAdmin):
    # Add the search fields to enable searching by item1's or item2's name.
    search_fields = ['item1__name', 'item2__name']
    list_display = ('item1', 'item2', 'score', 'relation_type', 'interaction_count', 'last_updated')
    list_filter = ('relation_type',)
    ordering = ('-score',)
###################

admin.site.register(Shop)
admin.site.register(Outlet)
admin.site.register(OperatingHours)
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
admin.site.register(Payouts)
admin.site.register(OrderItem)
admin.site.register(Cart)
admin.site.register(CartItem)
admin.site.register(DiscountCoupon)
admin.site.register(OrderTimelineItem)
admin.site.register(ItemRelation, ItemRelationAdmin)
admin.site.register(OutletDocument)
