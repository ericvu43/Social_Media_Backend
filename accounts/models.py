from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.conf import settings
from django.db.models import Q, Manager

class Page(models.Model):
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_pages'
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    type = models.CharField(
        max_length=50,
        choices=[
            ('Business', 'Business'),
            ('Organization', 'Organization'),
            ('Event', 'Event'),
            ('Education', 'Education'),
            ('Fan Page', 'Fan Page'),
            ('Other', 'Other'),
        ],
        default='Other'
    )
    tags = models.JSONField(blank=True, null=True)  # Store tags as a list of strings
    location = models.CharField(max_length=255, blank=True, null=True)
    profile_image = models.ImageField(upload_to='page_profile_images/', blank=True, null=True)  # Profile image
    cover_image = models.ImageField(upload_to='page_cover_images/', blank=True, null=True)  # Cover image
    email = models.EmailField(blank=True, null=True)  # Email field
    phone_number = models.CharField(max_length=15, blank=True, null=True)  # Phone number field
    website = models.URLField(blank=True, null=True)  # Website field
    accepts_donations = models.BooleanField(default=False)  # Accepts donations field
    created_at = models.DateTimeField(auto_now_add=True)
    followers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='followed_pages',
        blank=True
    )

    def __str__(self):
        return f"Page: {self.name} by {self.creator.email}"

    def __str__(self):
        return f"Page: {self.name} by {self.creator.email}"

# Custom manager for the CustomUser model
class CustomUserManager(BaseUserManager):
    """
    Custom manager for CustomUser to handle user creation.
    """
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra_fields)

    def search(self, query):
        return self.filter(
            Q(username__icontains=query) |
            Q(email__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query)
        )

class PostManager(Manager):
    def search(self, query):
        return self.filter(
            Q(content__icontains=query)
        )

class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=150, blank=True, null=True)  
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)  
    bio = models.TextField(blank=True, null=True)  
    is_email_verified = models.BooleanField(default=False)
    otp = models.CharField(max_length=6, null=True, blank=True)
    otp_created_at = models.DateTimeField(null=True, blank=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = [] 
    
    objects = CustomUserManager()

    def __str__(self):
        return self.email

class Comment(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    post = models.ForeignKey('Post', on_delete=models.CASCADE, related_name='comments')  # Link to the Post model
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Comment by {self.user.email} on {self.created_at}' 

class Message(models.Model):
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='sent_messages', on_delete=models.CASCADE)
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='received_messages', on_delete=models.CASCADE)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Message from {self.sender.email} to {self.recipient.email} at {self.timestamp}'

class FriendRequest(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    )
    
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='sent_requests', on_delete=models.CASCADE)
    receiver = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='received_requests', on_delete=models.CASCADE)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('sender', 'receiver')
    
    def __str__(self):
        return f"{self.sender.email} -> {self.receiver.email} ({self.status})"

class Like(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    post = models.ForeignKey('Post', on_delete=models.CASCADE, related_name='likes', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'post')
    
    def __str__(self):
        return f"{self.user.email} liked {self.post}"

class Post(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    page = models.ForeignKey('Page', on_delete=models.SET_NULL, related_name='posts', null=True, blank=True)  # Optional page association
    content = models.TextField(blank=True)  # Allow blank content for media-only posts
    media = models.FileField(upload_to='media/', null=True, blank=True)  # Use a single folder name
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        if self.page:
            return f"Post by {self.user.email} on {self.created_at} in Page: {self.page.name}"
        return f"Post by {self.user.email} on {self.created_at}"
