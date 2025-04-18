from rest_framework import status, generics, permissions, filters
from rest_framework.filters import SearchFilter
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import RetrieveAPIView, ListAPIView, CreateAPIView
from rest_framework.permissions import AllowAny, IsAuthenticatedOrReadOnly, IsAuthenticated
from rest_framework.exceptions import ValidationError
from django.contrib.auth import get_user_model, authenticate
from rest_framework_simplejwt.tokens import RefreshToken, UntypedToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from django.shortcuts import render, get_object_or_404
from django.db.models import Q
from django.http import JsonResponse
from itertools import chain
from django.core.paginator import Paginator
from django.db import IntegrityError

from .models import CustomUser, Page
from .serializers import UserSerializer

from .serializers import (
    UserRegistrationSerializer,
    UserLoginSerializer,
    PasswordResetSerializer,
    PasswordResetConfirmSerializer,
    OTPVerificationSerializer,
    ProfileUpdateSerializer,
    CommentSerializer,
    MessageSerializer,
    FriendRequestSerializer,
    LikeSerializer,
    PostSerializer,
    PageSerializer
)
from django.utils import timezone
from datetime import timedelta
from .utils import generate_otp, send_otp_email, send_password_reset_email
import uuid
from .models import Comment, Message, FriendRequest, Like, Post, CustomUser
from django.http import JsonResponse
from itertools import chain
from django.core.paginator import Paginator

from django.db import IntegrityError

User = get_user_model()

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = UserRegistrationSerializer

    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            user = serializer.save()
            
            # Generate and send OTP
            otp = generate_otp()
            user.otp = otp
            user.otp_created_at = timezone.now()
            user.save()
            
            send_otp_email(user.email, otp)
            
            return Response({
                'message': 'Registration successful. Please verify your email with the OTP sent.',
                'user_id': user.id
            }, status=status.HTTP_201_CREATED)
        except IntegrityError as e:
            # Handle unique constraint violation
            return Response({
                'error': 'A user with this email or username already exists.'
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            # Log the exception
            print(f"Error during registration: {e}")
            return Response({
                'error': 'An error occurred during registration. Please try again later.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class LoginView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            password = serializer.validated_data['password']
            
            user = authenticate(email=email, password=password)
            
            if user is not None:
                if not user.is_email_verified:
                    return Response({
                        'error': 'Please verify your email first'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                refresh = RefreshToken.for_user(user)
                return Response({
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                })
            else:
                return Response({
                    'error': 'Invalid credentials'
                }, status=status.HTTP_401_UNAUTHORIZED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

import logging

logger = logging.getLogger(__name__)

class PasswordResetView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = PasswordResetSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            try:
                user = User.objects.get(email=email)
                
                # Check if a token was created recently
                if user.otp_created_at and user.otp_created_at > timezone.now() - timedelta(minutes=0):
                    return Response({
                        'error': 'A password reset token was already sent recently. Please wait before requesting a new one.'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                token = str(uuid.uuid4())
                user.otp = token  # Using OTP field to store reset token
                user.otp_created_at = timezone.now()
                user.save()
                
                send_password_reset_email(email, token)
                
                return Response({
                    'message': 'Password reset instructions sent to your email'
                })
            except User.DoesNotExist:
                return Response({
                    'error': 'No user found with this email address'
                }, status=status.HTTP_404_NOT_FOUND)
            except Exception as e:
                logger.error(f"Error during password reset: {e}")
                return Response({
                    'error': 'An error occurred during password reset. Please try again later.'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class PasswordResetConfirmView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            token = serializer.validated_data['token']
            new_password = serializer.validated_data['new_password']
            
            try:
                user = User.objects.get(email=email)
                if user.otp == token and user.otp_created_at > timezone.now() - timedelta(hours=1):
                    user.set_password(new_password)
                    user.otp = None
                    user.otp_created_at = None
                    user.save()
                    return Response({'message': 'Password reset successful'})
                logger.error(f"Invalid or expired token for email {email}")
                return Response({'error': 'Invalid or expired token'}, status=status.HTTP_400_BAD_REQUEST)
            except User.DoesNotExist:
                logger.error(f"User not found for email {email}")
                return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
            except Exception as e:
                logger.error(f"Error during password reset confirmation for email {email}: {e}")
                return Response({'error': 'An error occurred during password reset confirmation. Please try again later.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        logger.error(f"Invalid data: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

class OTPVerificationView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = OTPVerificationSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            otp = serializer.validated_data['otp']
            try:
                user = User.objects.get(email=email)
                if user.otp == otp and user.otp_created_at > timezone.now() - timedelta(minutes=10):
                    user.is_email_verified = True
                    user.otp = None
                    user.otp_created_at = None
                    user.save()
                    
                    # Generate tokens after verification
                    refresh = RefreshToken.for_user(user)
                    return Response({
                        'message': 'Email verified successfully',
                        'refresh': str(refresh),
                        'access': str(refresh.access_token),
                    })
                return Response({'error': 'Invalid or expired OTP'}, status=status.HTTP_400_BAD_REQUEST)
            except User.DoesNotExist:
                return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ResendOTPView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        email = request.data.get('email')
        if not email:
            return Response({'error': 'Email is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = User.objects.get(email=email)
            if user.is_email_verified:
                return Response({'error': 'Email is already verified'}, status=status.HTTP_400_BAD_REQUEST)
            
            otp = generate_otp()
            user.otp = otp
            user.otp_created_at = timezone.now()
            user.save()
            
            send_otp_email(email, otp)
            
            return Response({'message': 'New OTP sent successfully'})
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

class ProfileUpdateView(generics.UpdateAPIView):
    queryset = CustomUser.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ProfileUpdateSerializer

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        if serializer.is_valid():
            self.perform_update(serializer)
            return Response(serializer.data)
        else:
            print(serializer.errors)  # Log the validation errors
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class CommentListCreateView(generics.ListCreateAPIView):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class CommentDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        return Comment.objects.filter(user=self.request.user)

    def handle_no_permission(self):
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

class PostCommentsView(generics.ListAPIView):
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        post_id = self.kwargs['post_id']
        return Comment.objects.filter(post_id=post_id).order_by('-created_at')
    
class MessageListCreateView(generics.ListCreateAPIView):
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        recipient_id = self.request.query_params.get('recipient')
        
        if recipient_id:
            # Filter for conversations between current user and specific recipient
            return Message.objects.filter(
                (Q(sender=user) & Q(recipient__id=recipient_id)) |
                (Q(recipient=user) & Q(sender__id=recipient_id))
            ).order_by('timestamp')
        else:
            # Return all messages the user is involved in
            return Message.objects.filter(
                Q(sender=user) | Q(recipient=user)
            ).order_by('timestamp')

    def perform_create(self, serializer):
        recipient_id = self.request.data.get('recipient')
        try:
            recipient = User.objects.get(id=recipient_id)
            serializer.save(sender=self.request.user, recipient=recipient)
        except User.DoesNotExist:
            raise ValidationError({"error": "Recipient does not exist."})

class MessageDetailView(generics.RetrieveDestroyAPIView):
    queryset = Message.objects.all()
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Message.objects.filter(sender=user) | Message.objects.filter(recipient=user)
    
class VerifyTokenView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        token = request.data.get('token')

        try:
            UntypedToken(token)
            return Response({'isValid': True}, status=status.HTTP_200_OK)
        except (InvalidToken, TokenError) as e:
            return Response({'isValid': False, 'error': str(e)}, status=status.HTTP_401_UNAUTHORIZED)

class FriendRequestListCreateView(generics.ListCreateAPIView):
    serializer_class = FriendRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        # Filter friend requests where the user is either the sender or the receiver
        return FriendRequest.objects.filter(
            Q(sender=user) | Q(receiver=user)
        )

    def perform_create(self, serializer):
        sender = self.request.user  # Automatically set the sender as the authenticated user
        receiver_id = self.request.data.get('receiver_id')

        # Validate that the receiver exists
        try:
            receiver = User.objects.get(id=receiver_id)
        except User.DoesNotExist:
            raise ValidationError({"error": "Receiver does not exist."})

        # Check if a friend request already exists
        if FriendRequest.objects.filter(sender=sender, receiver=receiver).exists():
            raise ValidationError({"error": "Friend request already sent."})
        if FriendRequest.objects.filter(sender=receiver, receiver=sender).exists():
            raise ValidationError({"error": "You already have a pending friend request from this user."})

        # Save the friend request
        serializer.save(sender=sender, receiver=receiver)

class FriendRequestDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = FriendRequestSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        return FriendRequest.objects.filter(
            Q(sender=user) | Q(receiver=user)
        )
    
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        
        # Only the receiver can accept or reject a friend request
        if instance.receiver != request.user:
            return Response(
                {"error": "Only the receiver can accept or reject a friend request"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Only allow updating the status field
        status_value = request.data.get('status')
        if status_value not in ['accepted', 'rejected']:
            return Response(
                {"error": "Status must be 'accepted' or 'rejected'"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        instance.status = status_value
        instance.save()
        
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

class FriendListView(generics.ListAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        # Get friends with accepted friend requests
        friends = []
        
        # Get friends where current user is the sender
        sent_requests = FriendRequest.objects.filter(
            sender=user, 
            status='accepted'
        )
        for request in sent_requests:
            friends.append(request.receiver)
            
        # Get friends where current user is the receiver
        received_requests = FriendRequest.objects.filter(
            receiver=user, 
            status='accepted'
        )
        for request in received_requests:
            friends.append(request.sender)
            
        return friends

class LikeCreateView(generics.CreateAPIView):
    serializer_class = LikeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        post_id = self.request.data.get('post')  # Use 'post' instead of 'comment'
        if Like.objects.filter(user=self.request.user, post_id=post_id).exists():
            raise ValidationError({"error": "You have already liked this post"})
        serializer.save(user=self.request.user)

class LikeDeleteView(generics.DestroyAPIView):
    serializer_class = LikeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        # Get the post_id and user_id from the URL
        post_id = self.kwargs.get('post_id')
        user_id = self.kwargs.get('user_id')

        # Ensure the authenticated user matches the user_id in the URL
        if self.request.user.id != user_id:
            raise ValidationError({"error": "You can only delete your own likes."})

        # Fetch the Like object
        try:
            return Like.objects.get(post_id=post_id, user_id=user_id)
        except Like.DoesNotExist:
            raise ValidationError({"error": "Like not found."})

class PostListCreateView(generics.ListCreateAPIView):
    serializer_class = PostSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Post.objects.all().order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class PostDetailView(APIView):
    def get(self, request, post_id):
        try:
            post = Post.objects.get(id=post_id)
            total_likes = post.likes.count()
            user_liked = post.likes.filter(user=request.user).exists()

            # Include user details
            user_data = {
                "id": post.user.id,
                "username": post.user.username,
                "avatar": post.user.avatar.url if post.user.avatar else None,
            }

            # Determine media type based on file extension
            media_type = None
            if post.media:
                if post.media.url.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp')):
                    media_type = "image"
                elif post.media.url.lower().endswith(('.mp4', '.mov', '.avi', '.mkv', '.webm')):
                    media_type = "video"

            return Response({
                "id": post.id,
                "user": user_data,  # Include user details
                "content": post.content,
                "media_url": {
                    "type": media_type,
                    "url": post.media.url if post.media else None,
                },
                "likes": total_likes,
                "user_liked": user_liked,
                "created_at": post.created_at,
                "updated_at": post.updated_at,
            })
        except Post.DoesNotExist:
            return Response({"error": "Post not found"}, status=404)
    
class FeedView(generics.ListAPIView):
    serializer_class = PostSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Return all posts, ordered by creation date (newest first)
        return Post.objects.all().order_by('-created_at')


def search_api(request):
    query = request.GET.get('q', '')
    if not query:
        return JsonResponse({'error': 'Query parameter q is required'}, status=400)
    
    # Search users and posts
    users = CustomUser.objects.search(query)
    posts = Post.objects.search(query)
    
    # Convert to dictionaries for JSON response
    user_results = [
        {
            'id': user.id,
            'type': 'user',
            'username': user.username,
            'email': user.email,
            'name': f"{user.first_name} {user.last_name}".strip()
        }
        for user in users[:20]  # Limit to first 20 results
    ]
    
    post_results = [
        {
            'id': post.id,
            'type': 'post',
            'content': post.content[:100] + '...' if len(post.content) > 100 else post.content,
            'author': post.user.username,
            'created_at': post.created_at.isoformat()
        }
        for post in posts[:20]  # Limit to first 20 results
    ]
    
    # Combine results
    results = user_results + post_results
    
    return JsonResponse({
        'query': query,
        'results': results,
        'total_users': users.count(),
        'total_posts': posts.count()
    })
    
class UserProfileView(RetrieveAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)
    
class UserPostsView(ListAPIView):
    serializer_class = PostSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        user_id = self.kwargs['user_id']
        return Post.objects.filter(user_id=user_id).order_by('-created_at')
    
class PageListView(ListAPIView):
    queryset = Page.objects.all()
    serializer_class = PageSerializer
    filter_backends = [SearchFilter]
    search_fields = ['name', 'description', 'tags', 'location']  # Allow filtering by these fields

class PageDetailView(RetrieveAPIView):
    queryset = Page.objects.all()
    serializer_class = PageSerializer
    lookup_field = 'id'  # Use 'id' to retrieve a page by its ID

    def get_serializer_context(self):
        """Pass the request context to the serializer."""
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

class PageCreateView(CreateAPIView):
    queryset = Page.objects.all()
    serializer_class = PageSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(creator=self.request.user)  # Set the creator to the logged-in user

class PageFollowToggleView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, page_id):
        try:
            page = Page.objects.get(id=page_id)
            user = request.user

            if user in page.followers.all():
                page.followers.remove(user)  # Unfollow the page
                return Response({"message": "Unfollowed the page"}, status=status.HTTP_200_OK)
            else:
                page.followers.add(user)  # Follow the page
                return Response({"message": "Followed the page"}, status=status.HTTP_200_OK)
        except Page.DoesNotExist:
            return Response({"error": "Page not found"}, status=status.HTTP_404_NOT_FOUND)
        
class PagePostListView(ListAPIView):
    serializer_class = PostSerializer

    def get_queryset(self):
        page_id = self.kwargs['page_id']
        return Post.objects.filter(page_id=page_id)  # Filter posts by page ID

class FollowedPagesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        followed_pages = Page.objects.filter(followers=user)
        serializer = PageSerializer(followed_pages, many=True, context={'request': request})
        return Response(serializer.data)
    
class AllUsersView(generics.ListAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]