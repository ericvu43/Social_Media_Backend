from rest_framework import status, generics, permissions, filters
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import RetrieveAPIView, ListAPIView
from rest_framework.permissions import AllowAny, IsAuthenticatedOrReadOnly, IsAuthenticated
from rest_framework.exceptions import ValidationError
from django.contrib.auth import get_user_model, authenticate
from rest_framework_simplejwt.tokens import RefreshToken, UntypedToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

from .models import CustomUser
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
    PostSerializer
)
from django.utils import timezone
from datetime import timedelta
from .utils import generate_otp, send_otp_email, send_password_reset_email
import uuid
from .models import Comment, Message, FriendRequest, Like, Post
from django.db.models import Q

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
    queryset = User.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ProfileUpdateSerializer

    def get_object(self):
        return self.request.user
    
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
        return Message.objects.filter(sender=user) | Message.objects.filter(recipient=user)

    def perform_create(self, serializer):
        serializer.save(sender=self.request.user)

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
        return FriendRequest.objects.filter(
            Q(sender=user) | Q(receiver=user)
        )
    
    def perform_create(self, serializer):
        serializer.save(sender=self.request.user)

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
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        # Get IDs of users who have accepted friend requests with the current user
        friend_ids = FriendRequest.objects.filter(
            (Q(sender=user) | Q(receiver=user)) & Q(status='accepted')
        ).values_list(
            'sender_id' if Q(receiver=user) else 'receiver_id', flat=True
        )
        return User.objects.filter(id__in=friend_ids)

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
    
    def get_queryset(self):
        return Like.objects.filter(user=self.request.user)

class PostListCreateView(generics.ListCreateAPIView):
    serializer_class = PostSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Post.objects.all().order_by('-created_at')
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class PostDetailView(APIView):
    def get(self, request, post_id):
        post = Post.objects.get(id=post_id)
        total_likes = post.likes.count()
        user_liked = post.likes.filter(user=request.user).exists()
        return Response({
            "id": post.id,
            "content": post.content,
            "likes": total_likes,
            "user_liked": user_liked,
        })

class FeedView(generics.ListAPIView):
    serializer_class = PostSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        
        # Get IDs of friends
        friend_ids = FriendRequest.objects.filter(
            (Q(sender=user) | Q(receiver=user)) & Q(status='accepted')
        ).values_list(
            'sender_id' if Q(receiver=user) else 'receiver_id', flat=True
        )
        
        # Get posts from friends and the user's own posts
        return Post.objects.filter(
            Q(user__in=friend_ids) | Q(user=user)
        ).order_by('-created_at')
    
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