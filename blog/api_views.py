from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.middleware.csrf import get_token
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from accounts.models import Profile
from .models import Post, Tag
from .serializers import (
    PostDetailSerializer,
    PostSerializer,
    TagSerializer,
    UserSerializer,
)

PAGE_SIZE = 10


def paginate(qs, request, serializer_class):
    try:
        page = max(1, int(request.GET.get("page", 1)))
    except ValueError:
        page = 1
    total = qs.count()
    start = (page - 1) * PAGE_SIZE
    items = serializer_class(qs[start : start + PAGE_SIZE], many=True).data
    return {
        "count": total,
        "total_pages": max(1, -(-total // PAGE_SIZE)),
        "page": page,
        "results": items,
    }


# ── Dashboard ──────────────────────────────────────────────────────────────────


@api_view(["GET"])
@permission_classes([AllowAny])
def dashboard(request):
    return Response(
        {
            "latest_posts": PostSerializer(
                Post.objects.select_related("author")
                .prefetch_related("tags")
                .order_by("-created_at")[:10],
                many=True,
            ).data,
            "latest_tags": TagSerializer(
                Tag.objects.order_by("-id")[:10], many=True
            ).data,
            "latest_users": UserSerializer(
                User.objects.select_related("profile").order_by("-date_joined")[:10],
                many=True,
            ).data,
        }
    )


# ── Posts ──────────────────────────────────────────────────────────────────────


@api_view(["GET"])
@permission_classes([AllowAny])
def post_list(request):
    qs = (
        Post.objects.select_related("author")
        .prefetch_related("tags")
        .order_by("-created_at")
    )
    return Response(paginate(qs, request, PostSerializer))


@api_view(["GET"])
@permission_classes([AllowAny])
def post_detail(request, slug):
    try:
        post = (
            Post.objects.select_related("author")
            .prefetch_related("tags", "comments__author", "comments__replies__author")
            .get(slug=slug)
        )
    except Post.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    return Response(PostDetailSerializer(post).data)


# ── Tags ───────────────────────────────────────────────────────────────────────


@api_view(["GET"])
@permission_classes([AllowAny])
def tag_list(request):
    qs = Tag.objects.order_by("name")
    return Response(paginate(qs, request, TagSerializer))


@api_view(["GET"])
@permission_classes([AllowAny])
def tag_detail(request, slug):
    try:
        tag = Tag.objects.get(slug=slug)
    except Tag.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    posts_qs = (
        Post.objects.filter(tags=tag)
        .select_related("author")
        .prefetch_related("tags")
        .order_by("-created_at")
    )
    return Response(
        {
            "tag": TagSerializer(tag).data,
            **paginate(posts_qs, request, PostSerializer),
        }
    )


# ── Users ──────────────────────────────────────────────────────────────────────


@api_view(["GET"])
@permission_classes([AllowAny])
def user_list(request):
    qs = User.objects.select_related("profile").order_by("-date_joined")
    return Response(paginate(qs, request, UserSerializer))


@api_view(["GET"])
@permission_classes([AllowAny])
def user_detail(request, username):
    try:
        user = User.objects.select_related("profile").get(username=username)
    except User.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    posts_qs = (
        Post.objects.filter(author=user)
        .prefetch_related("tags")
        .order_by("-created_at")
    )
    return Response(
        {
            "user": UserSerializer(user).data,
            **paginate(posts_qs, request, PostSerializer),
        }
    )


# ── Auth ───────────────────────────────────────────────────────────────────────


@api_view(["GET"])
@permission_classes([AllowAny])
def csrf(request):
    return Response({"csrfToken": get_token(request)})


@api_view(["POST"])
@permission_classes([AllowAny])
def login_view(request):
    email = request.data.get("email", "")
    password = request.data.get("password", "")
    try:
        username = User.objects.get(email=email).username
    except User.DoesNotExist:
        return Response(
            {"detail": "Invalid credentials."}, status=status.HTTP_400_BAD_REQUEST
        )
    user = authenticate(request, username=username, password=password)
    if user is None:
        return Response(
            {"detail": "Invalid credentials."}, status=status.HTTP_400_BAD_REQUEST
        )
    login(request, user)
    return Response(UserSerializer(user).data)


@api_view(["POST"])
@permission_classes([AllowAny])
def register_view(request):
    email = request.data.get("email", "")
    username = request.data.get("username", "")
    password = request.data.get("password", "")
    if not email or not username or not password:
        return Response(
            {"detail": "email, username and password are required."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if User.objects.filter(email=email).exists():
        return Response(
            {"detail": "Email already in use."}, status=status.HTTP_400_BAD_REQUEST
        )
    if User.objects.filter(username=username).exists():
        return Response(
            {"detail": "Username already taken."}, status=status.HTTP_400_BAD_REQUEST
        )
    user = User.objects.create_user(username=username, email=email, password=password)
    Profile.objects.get_or_create(user=user)
    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout_view(request):
    logout(request)
    return Response({"detail": "Logged out."})


@api_view(["GET"])
def current_user(request):
    if not request.user.is_authenticated:
        return Response(
            {"detail": "Not authenticated."}, status=status.HTTP_401_UNAUTHORIZED
        )
    return Response(UserSerializer(request.user).data)
