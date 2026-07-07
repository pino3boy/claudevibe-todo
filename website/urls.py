from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register_user, name='register'),
    path('login/', views.login_user, name='login'),
    path('logout/', views.logout_user, name='logout'),
    path('profile/', views.profile, name='profile'),
    path('day/<int:year>/<int:month>/<int:day>/', views.day_view, name='day'),
    path('task/<int:task_id>/delete/', views.delete_task, name='delete_task'),
]
