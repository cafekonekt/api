def fix_image_urls():
    food_items = FoodItem.objects.all()
    fixed_count = 0

    for item in food_items:
        if item.image:
            # Regenerate the correct image URL
            correct_url = f"https://api.tacoza.co{settings.MEDIA_URL.rstrip('/')}/{item.image.name}"
    
            # Check if the URL is incorrect and update
            if item.image_url != correct_url:
                item.image_url = correct_url
                item.save(update_fields=['image_url'])  # Only update the image_url field
                fixed_count += 1

    print(f"Fixed image URLs for {fixed_count} FoodItem records.")