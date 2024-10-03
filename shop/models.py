from django.db import models
from authentication.models import CustomUser
from shortener.models import ShortenedURL
from django.conf import settings
from django.utils import timezone
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
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)

    address = models.TextField(null=True, blank=True)
    location = models.CharField(max_length=100)

    logo = models.ImageField(upload_to='outlet_logos/', blank=True, null=True)
    minimum_order_value = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    average_preparation_time = models.PositiveIntegerField(default=30)
    services = models.CharField(max_length=100, default='dine_in')
    type = models.CharField(max_length=100, default='veg')
    payment_methods = models.CharField(max_length=100, default='online')
    
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

class Addon(models.Model):
    ADDONTYPE_CHOICES = [
        ('veg', 'Veg'),
        ('egg', 'Egg'),
        ('nonveg', 'Non-Veg')
    ]
    name = models.CharField(max_length=100)
    menu = models.ForeignKey('Menu', on_delete=models.CASCADE, related_name='addons')
    addon_type = models.CharField(max_length=10, choices=ADDONTYPE_CHOICES, default="veg")
    category = models.ForeignKey('AddonCategory', on_delete=models.CASCADE, related_name='addons', blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    in_stock = models.BooleanField(default=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    item_variant = models.ManyToManyField("ItemVariant", related_name='addons', blank=True, null=True)
    

    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['name']

class AddonCategory(models.Model):
    menu = models.ForeignKey('Menu', on_delete=models.CASCADE, related_name='addon_categories')
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['name']

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
    category = models.ForeignKey(VariantCategory, on_delete=models.CASCADE, related_name='options')
    created_at = models.DateTimeField(default=timezone.now)  # Added default value
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']

class ItemVariant(models.Model):
    food_item = models.ForeignKey('FoodItem', on_delete=models.CASCADE, related_name='item_variants')
    variant = models.ManyToManyField('Variant', related_name='item_variants')
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.food_item.name} - {[variant.name for variant in self.variant.all()]} - {float(self.price)}"
    
    class Meta:
        ordering = ['food_item']

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
    image = models.ImageField(upload_to='food_items/', blank=True, null=True)
    image_url = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    featured = models.BooleanField(default=False)
    in_stock = models.BooleanField(default=True)
    addons = models.ManyToManyField(Addon, related_name='food_items', blank=True)
    variant = models.ManyToManyField(VariantCategory, related_name='food_items', blank=True, null=True)
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
        
        if self.image and not self.image_url:
            self.image_url = f"https://api.tacoza.co{settings.MEDIA_URL}{self.image.name}"
        
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
        unique_together = ('user', 'outlet')

class CartItem(models.Model):
    id = models.AutoField(primary_key=True)
    item_id = models.CharField(max_length=100)
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    food_item = models.ForeignKey(FoodItem, on_delete=models.CASCADE, related_name='cart_items')
    variant = models.ForeignKey(ItemVariant, on_delete=models.CASCADE, blank=True, null=True)
    quantity = models.PositiveIntegerField()
    addons = models.ManyToManyField(Addon, related_name='cart_items', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.food_item.name} - {self.quantity}"
    
    def get_total_price(self):
        price = self.food_item.price
        if self.variant:
            price += self.variant.price
        for addon in self.addons.all():
            price += addon.price
        return price * self.quantity

    class Meta:
        ordering = ['food_item']
        unique_together = (('cart', 'item_id'))

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
    PAYMENT_STATUS_CHOICES = [
        ('active', 'Active'),
        ('paid', 'Paid'),
        ('expired', 'Expired'),
        ('terminated', 'Terminated'),
        ('termination_requested', 'Termination Requested')
    ]
    TRANSCATION_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed')
    ]
    order_id = models.CharField(max_length=500, default=uuid.uuid4, editable=False, primary_key=True)
    payment_id = models.CharField(max_length=500, blank=True, null=True)
    payment_session_id = models.CharField(max_length=500, blank=True, null=True)
    transaction_id = models.CharField(max_length=500, blank=True, null=True)
    
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    
    outlet = models.ForeignKey(Outlet, on_delete=models.CASCADE)
    table = models.ForeignKey('Table', on_delete=models.CASCADE, blank=True, null=True)
    cooking_instructions = models.TextField(blank=True, null=True)
    order_type = models.CharField(max_length=10, choices=ORDER_TYPE_CHOICES, default='dine-in')
    total = models.DecimalField(max_digits=10, decimal_places=2)
    
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    payment_status = models.CharField(max_length=30, choices=PAYMENT_STATUS_CHOICES, default='active')
    transaction_status = models.CharField(max_length=10, choices=TRANSCATION_STATUS_CHOICES, default='pending')
    
    created_at = models.DateTimeField(auto_now_add=True)
    prep_start_time = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.order_id
        
    class Meta:
        ordering = ['-created_at']
        
    def get_total_price(self):
        items = OrderItem.objects.filter(order=self)
        total = float(sum([item.get_total_price() for item in items]))
        return total

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    food_item = models.ForeignKey(FoodItem, on_delete=models.CASCADE)
    variant = models.ForeignKey(ItemVariant, on_delete=models.CASCADE, blank=True, null=True)
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
        return float(price * self.quantity)

class Table(models.Model):
    table_id = models.CharField(max_length=100, unique=True, default=uuid.uuid4)
    name = models.CharField(max_length=100)
    outlet = models.ForeignKey(Outlet, on_delete=models.CASCADE)
    capacity = models.PositiveIntegerField()
    area = models.ForeignKey('TableArea', on_delete=models.CASCADE, related_name='tables')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    url = models.ForeignKey(ShortenedURL, on_delete=models.CASCADE, blank=True, null=True)

    def __str__(self):
        return f"{self.name} - {self.outlet.name}"
    
    def get_url(self):
        if self.url:
            return f"https://api.tacoza.co/{self.url.short_code}"
        menu = Menu.objects.get(outlet=self.outlet)
        short_url = ShortenedURL.objects.create(original_url=f"https://app.tacoza.co/{menu.menu_slug}/{self.table_id}")
        self.url = short_url
        self.save()
        return f"https://api.tacoza.co/{short_url.short_code}"
        
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

class DiscountCoupon(models.Model):
    DISCOUNT_TYPE_CHOICES = [
        ('percentage', 'Percentage'),
        ('flat', 'Flat')
    ]
    coupon_code = models.CharField(max_length=100, unique=True)
    outlet = models.ForeignKey(Outlet, on_delete=models.CASCADE, null=True, blank=True)

    discount_type = models.CharField(max_length=10, choices=DISCOUNT_TYPE_CHOICES, default='percentage')
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)

    minimum_order_value = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    max_order_value = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    use_limit = models.PositiveIntegerField(default=1)
    use_limit_per_user = models.PositiveIntegerField(default=1)

    products = models.ManyToManyField(FoodItem, related_name='coupons', blank=True)

    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.coupon_code
    
    class Meta:
        ordering = ['created_at']
