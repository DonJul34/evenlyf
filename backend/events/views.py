from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny

# TODO: Imports will be added when serializers are created
# from .models import Activity, Venue, Event, EventRegistration, MatchingGroup
# from .serializers import ActivitySerializer, VenueSerializer, EventSerializer


class ActivityViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet pour les activités"""
    permission_classes = [AllowAny]
    
    def list(self, request):
        return Response({'message': 'Activities list - à implémenter'})


class VenueViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet pour les lieux"""
    permission_classes = [AllowAny]
    
    def list(self, request):
        return Response({'message': 'Venues list - à implémenter'})


class EventViewSet(viewsets.ModelViewSet):
    """ViewSet pour les événements"""
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        return Response({'message': 'Events list - à implémenter'})


class EventRegistrationViewSet(viewsets.ModelViewSet):
    """ViewSet pour les inscriptions aux événements"""
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        return Response({'message': 'Event registrations list - à implémenter'})


class MatchingGroupViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet pour les groupes de matching"""
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        return Response({'message': 'Matching groups list - à implémenter'})


class RegisterToEventView(APIView):
    """Vue pour s'inscrire à un événement"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, event_id):
        return Response({'message': f'Register to event {event_id} - à implémenter'})


class UnregisterFromEventView(APIView):
    """Vue pour se désinscrire d'un événement"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, event_id):
        return Response({'message': f'Unregister from event {event_id} - à implémenter'})


class CreateMatchingGroupsView(APIView):
    """Vue pour créer les groupes de matching pour un événement"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, event_id):
        return Response({'message': f'Create matching groups for event {event_id} - à implémenter'})


class JoinGroupView(APIView):
    """Vue pour rejoindre un groupe"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, group_id):
        return Response({'message': f'Join group {group_id} - à implémenter'})


class LeaveGroupView(APIView):
    """Vue pour quitter un groupe"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, group_id):
        return Response({'message': f'Leave group {group_id} - à implémenter'})


class SubmitFeedbackView(APIView):
    """Vue pour soumettre un feedback"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, event_id):
        return Response({'message': f'Submit feedback for event {event_id} - à implémenter'})


class DashboardOverviewView(APIView):
    """Vue pour le tableau de bord admin"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        return Response({'message': 'Dashboard overview - à implémenter'})


class PendingMatchesView(APIView):
    """Vue pour les matches en attente"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        return Response({'message': 'Pending matches - à implémenter'})
