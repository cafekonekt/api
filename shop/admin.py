from django.contrib import admin
from shop.models import Shop, Outlet, OutletUser, Menu, Variant, FoodItem, FoodCategory, SubCategory, AddonCategory

admin.site.register(Shop)
admin.site.register(Outlet)
admin.site.register(OutletUser)
admin.site.register(Menu)
admin.site.register(Variant)
admin.site.register(FoodItem)
admin.site.register(FoodCategory)
admin.site.register(SubCategory)
admin.site.register(AddonCategory)
