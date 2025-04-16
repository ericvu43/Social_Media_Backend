from django.urls import path
from .views import (
    RegisterView, 
    LoginView, 
    PasswordResetView, 
    PasswordResetConfirmView,
    OTPVerificationView,
    ResendOTPView,
    ProfileUpdateView,
    CommentListCreateView,
    CommentDetailView,
    MessageListCreateView,
    MessageDetailView,
    VerifyTokenView,
    FriendRequestListCreateView,
    FriendRequestDetailView,
    FriendListView,
    LikeCreateView,
    LikeDeleteView,
    PostListCreateView,
    PostDetailView,
    FeedView,
    UserProfileView,
    CurrentUserView,
    UserPostsView,
    PostCommentsView,
    PageListView,
    PageDetailView,
    PageCreateView,
    PageFollowToggleView,
    PagePostListView,
    FollowedPagesView,
    AllUsersView,
)
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('password-reset/', PasswordResetView.as_view(), name='password-reset'),
    path('password-reset/confirm/', PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
    path('verify-otp/', OTPVerificationView.as_view(), name='verify-otp'),
    path('resend-otp/', ResendOTPView.as_view(), name='resend-otp'),
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('profile/', ProfileUpdateView.as_view(), name='profile-update'),
    path('comments/', CommentListCreateView.as_view(), name='comment-list-create'),
    path('comments/<int:pk>/', CommentDetailView.as_view(), name='comment-detail'),
    path('posts/<int:post_id>/comments/', PostCommentsView.as_view(), name='post-comments'),
    path('messages/', MessageListCreateView.as_view(), name='message-list-create'),
    path('messages/<int:pk>/', MessageDetailView.as_view(), name='message-detail'),
    path('verify-token/', VerifyTokenView.as_view(), name='verify-token'),

    path('friend-requests/', FriendRequestListCreateView.as_view(), name='friend-request-list-create'),
    path('friend-requests/<int:pk>/', FriendRequestDetailView.as_view(), name='friend-request-detail'),
    path('friends/', FriendListView.as_view(), name='friend-list'),
    path('likes/', LikeCreateView.as_view(), name='like-create'),
    path('likes/<int:post_id>/<int:user_id>/', LikeDeleteView.as_view(), name='like-delete'),
    path('posts/', PostListCreateView.as_view(), name='post-list-create'),
    path('posts/<int:post_id>/', PostDetailView.as_view(), name='post-detail'),
    path('feed/', FeedView.as_view(), name='feed'),

    path('users/', AllUsersView.as_view(), name='all-users'),
    path('users/<int:pk>/', UserProfileView.as_view(), name='user-profile'),
    path('users/me/', CurrentUserView.as_view(), name='current-user'),

    path('users/<int:user_id>/posts/', UserPostsView.as_view(), name='user-posts'),

    path('pages/', PageListView.as_view(), name='page-list'),  # List all pages
    path('pages/<int:id>/', PageDetailView.as_view(), name='page-detail'),  # Retrieve a single page
    path('pages/create/', PageCreateView.as_view(), name='page-create'),  # Create a page
    path('pages/<int:page_id>/follow/', PageFollowToggleView.as_view(), name='page-follow-toggle'),  # Follow/unfollow a page
    path('pages/<int:page_id>/posts/', PagePostListView.as_view(), name='page-post-list'),  # List posts for a page
    path('pages/followed/', FollowedPagesView.as_view(), name='followed-pages'),  # List followed pages
]