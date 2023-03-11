from django.urls import path

from apps.users.views import UsernameCountView, MobileCountView, RegisterView, LoginView, LogoutView, \
    EmailView, VerifyEmailView, CenterView, ChangePasswordView

urlpatterns = [
    path('usernames/<username:username>/count/', UsernameCountView.as_view()),
    path('mobiles/<mobile:mobile>/count/', MobileCountView.as_view()),
    path('register/', RegisterView.as_view()),
    path('login/', LoginView.as_view()),
    path('logout/', LogoutView.as_view()),
    path('info/', CenterView.as_view()),
    path('emails/', EmailView.as_view()),
    path('emails/verification/', VerifyEmailView.as_view()),
    path('password/', ChangePasswordView.as_view()),
]
