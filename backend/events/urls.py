from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'activities', views.ActivityViewSet, basename='activity')
router.register(r'venues', views.VenueViewSet, basename='venue')
router.register(r'events', views.EventViewSet, basename='event')
router.register(r'registrations', views.EventRegistrationViewSet, basename='eventregistration')
router.register(r'groups', views.MatchingGroupViewSet, basename='matchinggroup')

urlpatterns = [
    # Router URLs
    path('', include(router.urls)),
    
    # Event registration
    path('events/<int:event_id>/register/', views.RegisterToEventView.as_view(), name='register-to-event'),
    path('events/<int:event_id>/unregister/', views.UnregisterFromEventView.as_view(), name='unregister-from-event'),
    
    # Matching system
    path('events/<int:event_id>/create-groups/', views.CreateMatchingGroupsView.as_view(), name='create-matching-groups'),
    path('groups/<int:group_id>/join/', views.JoinGroupView.as_view(), name='join-group'),
    path('groups/<int:group_id>/leave/', views.LeaveGroupView.as_view(), name='leave-group'),
    
    # Feedback
    path('events/<int:event_id>/feedback/', views.SubmitFeedbackView.as_view(), name='submit-feedback'),
    
    # Dashboard for admins
    path('dashboard/overview/', views.DashboardOverviewView.as_view(), name='dashboard-overview'),
    path('dashboard/pending-matches/', views.PendingMatchesView.as_view(), name='pending-matches'),
] 