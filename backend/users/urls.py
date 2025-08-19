from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'users', views.UserViewSet, basename='user')

app_name = 'users'

urlpatterns = [
    path('', include(router.urls)),
    
    # Auth endpoints
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('profile/', views.ProfileView.as_view(), name='profile'),
    
    # Email verification
    path('verify-email/', views.VerifyEmailView.as_view(), name='verify-email'),
    path('resend-verification/', views.ResendVerificationView.as_view(), name='resend-verification'),
    
    # Password reset
    path('password-reset/', views.PasswordResetView.as_view(), name='password-reset'),
    path('password-reset-confirm/', views.PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
    
    # Onboarding
    path('onboarding-progress/', views.OnboardingProgressView.as_view(), name='onboarding-progress'),
    
    # Personality test
    path('personality-test/', views.PersonalityTestView.as_view(), name='personality-test'),
    path('personality-test/session/', views.PersonalityTestSessionView.as_view(), name='personality-test-session'),
    path('personality-test/answer/', views.PersonalityTestAnswerView.as_view(), name='personality-test-answer'),
    path('personality-test/submit/', views.SubmitPersonalityTestView.as_view(), name='submit-personality-test'),
    
    # Passion selection

    
    # Social auth
    path('social/google/', views.GoogleOAuth2LoginView.as_view(), name='google-login'),
    path('social/apple/', views.AppleOAuth2LoginView.as_view(), name='apple-login'),
    path('user-interests/', views.UserInterestsView.as_view(), name='user-interests'),
    
    # Stripe et réservations
    path('create-payment-intent/', views.CreatePaymentIntentView.as_view(), name='create-payment-intent'),
    path('confirm-payment/', views.ConfirmPaymentView.as_view(), name='confirm-payment'),
    path('reservations/', views.ReservationView.as_view(), name='reservations'),
    path('reservations/<int:reservation_id>/', views.ReservationDetailView.as_view(), name='reservation-detail'),
    path('admin/reservations/', views.AdminReservationsView.as_view(), name='admin-reservations'),
    path('admin/create-group/', views.CreateGroupView.as_view(), name='admin-create-group'),
    path('admin/groups/', views.AdminGroupsView.as_view(), name='admin-groups'),
    path('admin/users/<int:user_id>/profile/', views.UserProfileDetailView.as_view(), name='admin-user-profile'),
    path('admin/users-management/', views.AdminUsersManagementView.as_view(), name='admin-users-management'),
    
    # Gestion des réservations et tickets
    path('reservations/<int:reservation_id>/cancel/', views.ReservationCancelView.as_view(), name='reservation-cancel'),
    path('reservations/tickets/', views.UserTicketsView.as_view(), name='user-tickets'),
    path('reservations/use-ticket/', views.UseTicketView.as_view(), name='use-ticket'),
    path('create-reservation/', views.CreateReservationView.as_view(), name='create-reservation'),
    
    # Invitations d'amis
    path('invitations/create/', views.CreateFriendInvitationView.as_view(), name='create-friend-invitation'),
    path('invitations/<str:invitation_token>/', views.InvitationDetailsView.as_view(), name='invitation-details'),
    path('invitations/<str:invitation_token>/accept/', views.AcceptInvitationView.as_view(), name='accept-invitation'),
    path('invited-user/process/', views.ProcessInvitedUserView.as_view(), name='process-invited-user'),
    
    # Tickets
    path('tickets/', views.UserTicketsView.as_view(), name='user-tickets'),
    
    # Abonnements
    path('subscription/', views.UserSubscriptionView.as_view(), name='user-subscription'),
    path('subscription/check-status/', views.CheckSubscriptionStatusView.as_view(), name='check-subscription-status'),
    
    # Admin Dashboard
    # Réservations
    path('reservations/', views.ReservationView.as_view(), name='user-reservations'),
    path('reservations/<int:reservation_id>/', views.ReservationDetailView.as_view(), name='reservation-detail'),
    path('reservations/<int:reservation_id>/cancel/', views.ReservationCancelView.as_view(), name='cancel-reservation'),
    path('reservations/create-with-subscription/', views.CreateReservationWithSubscriptionView.as_view(), name='create-reservation-subscription'),
    
    # Invitations
] 