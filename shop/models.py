from django.db import models
from authentication.models import CustomUser
import uuid
import re

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
    SERVICE_CHOICES = [
        ('dine_in', 'Dine-In'),
        ('takeaway', 'Takeaway'),
        ('delivery', 'Delivery')
    ]
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)

    address = models.TextField(null=True, blank=True)
    location = models.CharField(max_length=100)

    logo = models.ImageField(upload_to='outlet_logos/', blank=True, null=True)
    minimum_order_value = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    average_preparation_time = models.PositiveIntegerField(default=30)
    services = models.CharField(max_length=100, default='dine_in')
    
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=15)
    whatsapp = models.CharField(max_length=15, null=True, blank=True)

    slug = models.SlugField(max_length=100, unique=True, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    outlet_manager = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='outlets', blank=True, null=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # slug should be all lowercase and separated by hyphens and alphanumeric
        shop_name = re.sub(r'[^a-zA-Z0-9]', '', self.shop.name.lower().replace(' ', '-'))
        outlet_name = re.sub(r'[^a-zA-Z0-9]', '', self.name.lower().replace(' ', '-'))
        self.slug = f"{shop_name}-{outlet_name}"
        super(Outlet, self).save(*args, **kwargs)
    
    class Meta:
        ordering = ['name']

class OutletImage(models.Model):
    outlet = models.ForeignKey(Outlet, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='outlet_images/')  # Folder where images will be stored
    caption = models.CharField(max_length=255, blank=True, null=True)  # Optional caption for the image
    order = models.PositiveIntegerField(default=0)  # Order of the image in the gallery
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'uploaded_at']  # Images ordered by custom order, then upload time

    def __str__(self):
        return f"Image {self.id} for {self.outlet.name}"

class OperatingHours(models.Model):
    DAYS_OF_WEEK = [
        ('Monday', 'Monday'),
        ('Tuesday', 'Tuesday'),
        ('Wednesday', 'Wednesday'),
        ('Thursday', 'Thursday'),
        ('Friday', 'Friday'),
        ('Saturday', 'Saturday'),
        ('Sunday', 'Sunday'),
    ]

    outlet = models.ForeignKey(Outlet, on_delete=models.CASCADE, related_name='operating_hours')
    day_of_week = models.CharField(max_length=9, choices=DAYS_OF_WEEK)
    opening_time = models.TimeField()
    closing_time = models.TimeField()

    class Meta:
        unique_together = ('outlet', 'day_of_week')  # Ensures no duplicate entries for the same day of the week

    def __str__(self):
        return f"{self.outlet.name} - {self.day_of_week}: {self.opening_time} to {self.closing_time}"

class Menu(models.Model):
    menu_slug = models.SlugField(max_length=100, unique=True, primary_key=True)
    outlet = models.ForeignKey(Outlet, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.menu_slug

    class Meta:
        ordering = ['created_at']

class VariantCategory(models.Model):
    name = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']

class Variant(models.Model):
    name = models.CharField(max_length=50)
    category = models.ForeignKey('VariantCategory', on_delete=models.CASCADE, related_name='variants', blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']

class ItemVariant(models.Model):
    food_item = models.ForeignKey('FoodItem', on_delete=models.CASCADE, related_name='item_variants')
    variant = models.ForeignKey('Variant', on_delete=models.CASCADE, related_name='item_variants')
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.food_item.name} - {self.variant.name}"
    
    class Meta:
        ordering = ['food_item']

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
    featured = models.BooleanField(default=False)

    addons = models.ManyToManyField(Addon, related_name='food_items', blank=True)
    variant = models.ForeignKey(VariantCategory, on_delete=models.CASCADE, related_name='food_items', blank=True, null=True)
    tags = models.ManyToManyField('FoodTag', related_name='food_items', blank=True)
    
    prepration_time = models.PositiveIntegerField(default=30)
    slug = models.SlugField(max_length=100, unique=True, blank=True, null=True)

    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['name']

    def save(self, *args, **kwargs):
        # slug should be all lowercase and separated by hyphens and alphanumeric
        menu_slug = self.menu.menu_slug
        name = re.sub(r'[^a-zA-Z0-9]', '', self.name.lower().replace(' ', '-'))
        self.slug = f"{menu_slug}-{name}"
        super(FoodItem, self).save(*args, **kwargs)

class FoodTag(models.Model):
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['name']

class FoodCategory(models.Model):
    menu = models.ForeignKey('Menu', on_delete=models.CASCADE)
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
    id = models.CharField(max_length=100, primary_key=True)
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    food_item = models.ForeignKey(FoodItem, on_delete=models.CASCADE, related_name='cart_items')
    variant = models.ForeignKey(Variant, on_delete=models.CASCADE, blank=True, null=True)
    quantity = models.PositiveIntegerField()
    addons = models.ManyToManyField(Addon, related_name='cart_items', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.food_item.name} - {self.quantity}"
    
    def get_total_price(self):
        price = self.food_item.price
        if self.variant:
            # get price from ItemVariant for selected variant
            price = ItemVariant.objects.get(food_item=self.food_item, variant=self.variant).price
        for addon in self.addons.all():
            price += addon.price
        return price * self.quantity

    class Meta:
        ordering = ['food_item']

class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ]
    ORDER_TYPE_CHOICES = [
        ('dine_in', 'Dine-In'),
        ('takeaway', 'Takeaway'),
        ('delivery', 'Delivery')
    ]
    order_id = models.CharField(max_length=100, default=uuid.uuid4, editable=False, primary_key=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    outlet = models.ForeignKey(Outlet, on_delete=models.CASCADE)
    table = models.ForeignKey('Table', on_delete=models.CASCADE, blank=True, null=True)
    cooking_instructions = models.TextField(blank=True, null=True)
    order_type = models.CharField(max_length=10, choices=ORDER_TYPE_CHOICES, default='dine-in')
    total = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
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

    def get_total_price(self):
        price = self.food_item.price
        if self.variant:
            # get price from ItemVariant for selected variant
            price = ItemVariant.objects.get(food_item=self.food_item, variant=self.variant).price
        for addon in self.addons.all():
            price += addon.price
        return price * self.quantity

class Table(models.Model):
    id = models.CharField(max_length=100, primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    outlet = models.ForeignKey(Outlet, on_delete=models.CASCADE)
    capacity = models.PositiveIntegerField()
    area = models.ForeignKey('TableArea', on_delete=models.CASCADE, related_name='tables')
    slug = models.SlugField(max_length=100, unique=True, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.outlet.name}"
    
    def save(self, *args, **kwargs):
        outlet_name = re.sub(r'[^a-zA-Z0-9]', '', self.outlet.name.lower().replace(' ', '-'))
        name = re.sub(r'[^a-zA-Z0-9]', '', self.name.lower().replace(' ', '-'))
        area = re.sub(r'[^a-zA-Z0-9]', '', self.area.name.lower().replace(' ', '-')) if self.area else ''
        self.slug = f"{outlet_name}-{area}-{name}"
        super(Table, self).save(*args, **kwargs)
    
    class Meta:
        ordering = ['name']

class TableArea(models.Model):
    outlet = models.ForeignKey(Outlet, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['name']
