from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from .models import CustomUser, Comment, Message, FriendRequest, Like, Post, Page
from django.conf import settings

User = get_user_model()

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ('email', 'username', 'bio', 'password', 'password2')

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')
        user = User.objects.create_user(**validated_data)
        return user

class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()

class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()

class PasswordResetConfirmSerializer(serializers.Serializer):
    email = serializers.EmailField()
    token = serializers.CharField()
    new_password = serializers.CharField(validators=[validate_password])

class OTPVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6) 


class ProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'email' , 'bio', 'avatar']

class MessageSerializer(serializers.ModelSerializer):
    sender = serializers.ReadOnlyField(source='sender.email')
    recipient = serializers.ReadOnlyField(source='recipient.email')

    class Meta:
        model = Message
        fields = ['id', 'sender', 'recipient', 'content', 'timestamp']

class FriendRequestSerializer(serializers.ModelSerializer):
    sender = serializers.ReadOnlyField(source='sender.email')
    receiver = serializers.ReadOnlyField(source='receiver.email')
    receiver_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = FriendRequest
        fields = ['id', 'sender', 'receiver', 'receiver_id', 'status', 'created_at', 'updated_at']
        read_only_fields = ['status']
    
    def create(self, validated_data):
        receiver_id = validated_data.pop('receiver_id')
        receiver = User.objects.get(id=receiver_id)
        validated_data['receiver'] = receiver
        return super().create(validated_data)

class LikeSerializer(serializers.ModelSerializer):
    user = serializers.ReadOnlyField(source='user.email')
    
    class Meta:
        model = Like
        fields = ['id', 'user', 'post', 'created_at']

from rest_framework import serializers
from .models import Post

class PostSerializer(serializers.ModelSerializer):
    media_url = serializers.SerializerMethodField()  # Add a field to return the media URL

    class Meta:
        model = Post
        fields = ['id', 'user', 'page', 'content', 'media', 'media_url', 'created_at', 'updated_at']

    def get_media_url(self, obj):
        if obj.media:
            media_type = "image" if obj.media.name.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')) else "video"
            request = self.context.get('request')  # Get the request object from the serializer context
            base_url = request.build_absolute_uri('/') if request else settings.MEDIA_URL
            return {
                "type": media_type,
                "url": f"{base_url.rstrip('/')}{obj.media.url}"  # Construct the absolute URL
            }
        return None

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'email' , 'bio', 'avatar', 'is_email_verified']

class CommentSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)  # Use the nested UserSerializer

    class Meta:
        model = Comment
        fields = ['id', 'user', 'post', 'content', 'created_at', 'updated_at']

class PageSerializer(serializers.ModelSerializer):
    creator = serializers.ReadOnlyField(source='creator.email')  # Include the creator's email
    followers_count = serializers.IntegerField(source='followers.count', read_only=True)  # Count of followers
    is_following = serializers.SerializerMethodField()  # Add this field

    class Meta:
        model = Page
        fields = [
            'id', 'creator', 'name', 'description', 'type', 'tags',
            'location', 'profile_image', 'cover_image', 'email',
            'phone_number', 'website', 'accepts_donations', 'created_at', 'followers_count',
            'is_following'
        ]

    def get_is_following(self, obj):
        """Check if the current user is following the page."""
        user = self.context['request'].user
        if user.is_authenticated:
            return user in obj.followers.all()
        return False