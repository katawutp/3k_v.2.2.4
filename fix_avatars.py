# fix_avatars.py
import os
from PIL import Image, ImageDraw, ImageFont
from django.conf import settings
from a_users.models import CustomUser  # or your user model
import random

def create_placeholder_avatar(user_id, username):
    """Create a placeholder avatar with initials"""
    # Create a colored background
    colors = [
        (255, 99, 132), (54, 162, 235), (255, 206, 86),
        (75, 192, 192), (153, 102, 255), (255, 159, 64),
        (255, 0, 0), (0, 255, 0), (0, 0, 255)
    ]
    color = random.choice(colors)
    
    # Create image
    img = Image.new('RGB', (200, 200), color=color)
    draw = ImageDraw.Draw(img)
    
    # Get initials
    initials = username[:2].upper() if username else str(user_id)
    
    # Add text
    try:
        font = ImageFont.load_default()
        draw.text((70, 80), initials, fill=(255, 255, 255))
    except:
        draw.text((70, 80), initials, fill=(255, 255, 255))
    
    # Save
    avatar_path = os.path.join(settings.MEDIA_ROOT, 'avatars', f'placeholder_{user_id}.png')
    os.makedirs(os.path.dirname(avatar_path), exist_ok=True)
    img.save(avatar_path)
    return f'avatars/placeholder_{user_id}.png'

def fix_missing_avatars():
    """Fix missing avatars for users"""
    from a_users.models import CustomUser
    
    fixed_count = 0
    for user in CustomUser.objects.all():
        if user.avatar:
            avatar_path = os.path.join(settings.MEDIA_ROOT, str(user.avatar))
            if not os.path.exists(avatar_path):
                print(f"Missing avatar for user {user.username}: {user.avatar}")
                # Create placeholder
                new_avatar = create_placeholder_avatar(user.id, user.username)
                user.avatar = new_avatar
                user.save(update_fields=['avatar'])
                fixed_count += 1
                print(f"✅ Created placeholder for {user.username}")
    
    print(f"\nFixed {fixed_count} missing avatars")

if __name__ == "__main__":
    fix_missing_avatars()