from django.db import models
from authentication.models import CustomUser

class Shop(models.Model):
    name = models.CharField(max_length=100)
    owner = models.CharField(max_length=100)
    logo_url = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['name']

class Outlet(models.Model):
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    location = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['name']

class OutletUser(models.Model):
    outlet = models.ForeignKey(Outlet, on_delete=models.CASCADE, related_name='users')
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='outlet_user_profile')
    is_manager = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.email or self.user.phone_number} - {self.outlet.name}"

    class Meta:
        ordering = ['outlet', 'user']

class Menu(models.Model):
    outlet = models.ForeignKey(Outlet, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['name']

class Variant(models.Model):
    name = models.CharField(max_length=50)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']

class Addon(models.Model):
    name = models.CharField(max_length=100)
    category = models.ForeignKey('AddonCategory', on_delete=models.CASCADE, related_name='addons', blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['name']

class AddonCategory(models.Model):
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['name']

class FoodItem(models.Model):
    FOODTYPE_CHOICES = [
        ('veg', 'Veg'),
        ('egg', 'Egg'),
        ('nonveg', 'Non-Veg')
    ]
    menu = models.ForeignKey(Menu, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    food_type = models.CharField(max_length=10, choices=FOODTYPE_CHOICES)
    food_category = models.ForeignKey('FoodCategory', on_delete=models.CASCADE, related_name='food_items')
    food_subcategory = models.ForeignKey('SubCategory', on_delete=models.CASCADE, related_name='food_items', blank=True, null=True)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image_url = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    addons = models.ManyToManyField(Addon, related_name='food_items', blank=True)
    tags = models.ManyToManyField('FoodTag', related_name='food_items', blank=True)
    prepration_time = models.PositiveIntegerField(default=30)

    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['name']


class FoodTag(models.Model):
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['name']

class FoodCategory(models.Model):
    menu = models.ForeignKey(Menu, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['name']

class SubCategory(models.Model):
    category = models.ForeignKey(FoodCategory, on_delete=models.CASCADE, related_name='sub_categories')
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['name']

class Cart(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    outlet = models.ForeignKey(Outlet, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.email or self.user.phone_number} - {self.outlet.name}"
    
    class Meta:
        ordering = ['user']

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    food_item = models.ForeignKey(FoodItem, on_delete=models.CASCADE, related_name='cart_items')
    variant = models.ForeignKey(Variant, on_delete=models.CASCADE, blank=True, null=True)
    quantity = models.PositiveIntegerField()
    addons = models.ManyToManyField(Addon, related_name='cart_items', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.food_item.name} - {self.quantity}"
    
    class Meta:
        ordering = ['food_item']

class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ]
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    outlet = models.ForeignKey(Outlet, on_delete=models.CASCADE)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    food_item = models.ForeignKey(FoodItem, on_delete=models.CASCADE)
    variant = models.ForeignKey(Variant, on_delete=models.CASCADE, blank=True, null=True)
    quantity = models.PositiveIntegerField()
    addons = models.ManyToManyField(Addon, related_name='order_items', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.food_item.name} - {self.quantity}"
    
    class Meta:
        ordering = ['food_item']