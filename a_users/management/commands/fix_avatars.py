# fix_avatars.py
from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.files import File
from a_users.models import CustomUser
from PIL import Image, ImageDraw
import os
import random
import tempfile

class Command(BaseCommand):
    help = 'Fix missing avatars for users'

    def create_avatar_file(self, username, user_id):
        """Create a placeholder avatar and return as Django File object"""
        colors = [
            (255, 99, 132), (54, 162, 235), (255, 206, 86),
            (75, 192, 192), (153, 102, 255), (255, 159, 64),
            (255, 69, 0), (148, 0, 211), (0, 191, 255),
            (0, 255, 127), (255, 215, 0), (0, 255, 255),
        ]
        
        color = colors[user_id % len(colors)]
        
        # Create image
        img = Image.new('RGB', (200, 200), color=color)
        draw = ImageDraw.Draw(img)
        
        # Get initials (first 2 chars)
        initials = username[:2].upper() if username else str(user_id)[:2]
        
        # Draw text
        draw.text((65, 70), initials, fill=(255, 255, 255))
        
        # Add a border
        draw.rectangle([(0, 0), (199, 199)], outline=(255, 255, 255), width=2)
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp:
            img.save(tmp, format='PNG')
            tmp_path = tmp.name
        
        return tmp_path

    def handle(self, *args, **options):
        self.stdout.write("🔍 Checking for missing avatars...")
        self.stdout.write("=" * 50)
        
        # Get media root
        media_root = settings.MEDIA_ROOT
        avatars_dir = os.path.join(media_root, 'avatars')
        os.makedirs(avatars_dir, exist_ok=True)
        
        fixed_count = 0
        total_users = CustomUser.objects.count()
        
        for user in CustomUser.objects.all():
            needs_fix = False
            
            # Check if avatar exists and is valid
            if user.avatar:
                avatar_path = os.path.join(media_root, str(user.avatar))
                if not os.path.exists(avatar_path):
                    needs_fix = True
                    self.stdout.write(self.style.WARNING(f"❌ Missing avatar for: {user.username}"))
            else:
                needs_fix = True
                self.stdout.write(f"📝 No avatar for: {user.username}")
            
            if needs_fix:
                try:
                    # Create new avatar
                    tmp_path = self.create_avatar_file(user.username, user.id)
                    
                    # Open the file and save to model
                    filename = f"avatar_{user.id}.png"
                    with open(tmp_path, 'rb') as f:
                        from django.core.files.base import ContentFile
                        user.avatar.save(filename, ContentFile(f.read()), save=True)
                    
                    # Clean up temp file
                    os.unlink(tmp_path)
                    
                    self.stdout.write(self.style.SUCCESS(f"✅ Created avatar for: {user.username}"))
                    fixed_count += 1
                    
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"❌ Failed to create avatar for {user.username}: {e}"))
        
        self.stdout.write("=" * 50)
        self.stdout.write(self.style.SUCCESS(f"✅ Completed! Fixed {fixed_count} avatars"))
        self.stdout.write(f"   Total users: {total_users}")
        self.stdout.write(f"   Avatars directory: {avatars_dir}")