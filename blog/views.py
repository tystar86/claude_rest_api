from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render

from .models import Post, Tag


def dashboard(request):
    context = {
        "latest_posts": Post.objects.select_related("author").order_by("-created_at")[
            :10
        ],
        "latest_tags": Tag.objects.order_by("-id")[:10],
        "latest_users": User.objects.order_by("-date_joined")[:10],
    }
    return render(request, "blog/dashboard.html", context)


def post_list(request):
    posts = Post.objects.select_related("author").order_by("-created_at")
    paginator = Paginator(posts, 10)
    page = paginator.get_page(request.GET.get("page"))
    return render(request, "blog/post_list.html", {"page_obj": page})


def post_detail(request, slug):
    post = get_object_or_404(
        Post.objects.select_related("author").prefetch_related(
            "tags", "comments__author"
        ),
        slug=slug,
    )
    return render(request, "blog/post_detail.html", {"post": post})


def tag_list(request):
    tags = Tag.objects.order_by("name")
    paginator = Paginator(tags, 10)
    page = paginator.get_page(request.GET.get("page"))
    return render(request, "blog/tag_list.html", {"page_obj": page})


def tag_detail(request, slug):
    tag = get_object_or_404(Tag, slug=slug)
    posts = (
        Post.objects.filter(tags=tag).select_related("author").order_by("-created_at")
    )
    paginator = Paginator(posts, 10)
    page = paginator.get_page(request.GET.get("page"))
    return render(request, "blog/tag_detail.html", {"tag": tag, "page_obj": page})


def user_list(request):
    users = User.objects.select_related("profile").order_by("-date_joined")
    paginator = Paginator(users, 10)
    page = paginator.get_page(request.GET.get("page"))
    return render(request, "blog/user_list.html", {"page_obj": page})


def user_detail(request, username):
    u = get_object_or_404(User.objects.select_related("profile"), username=username)
    posts = Post.objects.filter(author=u).order_by("-created_at")
    paginator = Paginator(posts, 10)
    page = paginator.get_page(request.GET.get("page"))
    return render(
        request, "blog/user_detail.html", {"profile_user": u, "page_obj": page}
    )
