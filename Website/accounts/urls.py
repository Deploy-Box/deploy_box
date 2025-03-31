from typing import List, Union
from django.urls import URLPattern, URLResolver, path
from . import views

urlpatterns: List[Union[URLPattern, URLResolver]] = [
    path('authorize/', views.oauth_authorize, name='oauth_authorize'),
    path('callback/', views.oauth_callback, name='oauth_callback'),
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup, name='signup'),
    path('logout/', views.logout_view, name='logout'),
]
