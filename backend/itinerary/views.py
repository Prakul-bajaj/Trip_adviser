from rest_framework import generics, status, views
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.utils import timezone

from .models import Itinerary, DayPlan, Activity, Transportation, ItineraryShare
from .serializers import (
    ItineraryListSerializer, ItineraryDetailSerializer, ItineraryCreateSerializer,
    DayPlanSerializer, ActivitySerializer, ActivityCreateSerializer,
    TransportationSerializer, ItineraryShareSerializer
)
from .itinerary_generator import ItineraryGenerator, ItineraryOptimizer, ItineraryExporter
from users.permissions import IsOwnerOrAdmin
import secrets


class ItineraryListCreateView(generics.ListCreateAPIView):
    """List user's itineraries or create new"""
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ItineraryCreateSerializer
        return ItineraryListSerializer
    
    def get_queryset(self):
        return Itinerary.objects.filter(user=self.request.user)
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        itinerary = serializer.save()
        
        # Return detailed serializer
        output_serializer = ItineraryDetailSerializer(itinerary, context={'request': request})
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)


class ItineraryDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Get, update or delete an itinerary"""
    serializer_class = ItineraryDetailSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]
    
    def get_queryset(self):
        return Itinerary.objects.filter(user=self.request.user)
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.views_count += 1
        instance.save(update_fields=['views_count'])
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class DayPlanDetailView(generics.RetrieveUpdateAPIView):
    """Get or update a specific day plan"""
    serializer_class = DayPlanSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return DayPlan.objects.filter(itinerary__user=self.request.user)


class ActivityListCreateView(generics.ListCreateAPIView):
    """List or create activities for a day plan"""
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ActivityCreateSerializer
        return ActivitySerializer
    
    def get_queryset(self):
        day_plan_id = self.kwargs.get('day_plan_id')
        return Activity.objects.filter(
            day_plan_id=day_plan_id,
            day_plan__itinerary__user=self.request.user
        )
    
    def perform_create(self, serializer):
        day_plan_id = self.kwargs.get('day_plan_id')
        day_plan = get_object_or_404(
            DayPlan, 
            id=day_plan_id,
            itinerary__user=self.request.user
        )
        serializer.save(day_plan=day_plan)


class ActivityDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Get, update or delete an activity"""
    serializer_class = ActivitySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Activity.objects.filter(day_plan__itinerary__user=self.request.user)


class TransportationListCreateView(generics.ListCreateAPIView):
    """List or create transportation for itinerary"""
    serializer_class = TransportationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        itinerary_id = self.kwargs.get('itinerary_id')
        return Transportation.objects.filter(
            itinerary_id=itinerary_id,
            itinerary__user=self.request.user
        )
    
    def perform_create(self, serializer):
        itinerary_id = self.kwargs.get('itinerary_id')
        itinerary = get_object_or_404(
            Itinerary,
            id=itinerary_id,
            user=self.request.user
        )
        serializer.save(itinerary=itinerary)


class TransportationDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Get, update or delete transportation"""
    serializer_class = TransportationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Transportation.objects.filter(itinerary__user=self.request.user)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def optimize_itinerary(request, pk):
    """Optimize an existing itinerary"""
    try:
        itinerary = get_object_or_404(Itinerary, id=pk, user=request.user)
        
        optimizer = ItineraryOptimizer()
        
        # Optimize each day plan
        for day_plan in itinerary.day_plans.all():
            optimizer.optimize_route(day_plan)
        
        serializer = ItineraryDetailSerializer(itinerary)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def share_itinerary(request, pk):
    """Share an itinerary with others"""
    try:
        itinerary = get_object_or_404(Itinerary, id=pk, user=request.user)
        
        # Generate share token
        share_token = secrets.token_urlsafe(32)
        
        share = ItineraryShare.objects.create(
            itinerary=itinerary,
            shared_by=request.user,
            share_token=share_token,
            is_public_link=True,
            can_edit=request.data.get('can_edit', False),
            expires_at=request.data.get('expires_at')
        )
        
        serializer = ItineraryShareSerializer(share)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def view_shared_itinerary(request, share_token):
    """View a shared itinerary using share token"""
    try:
        share = get_object_or_404(
            ItineraryShare,
            share_token=share_token
        )
        
        # Check if expired
        if share.expires_at and share.expires_at < timezone.now():
            return Response(
                {'error': 'This share link has expired'},
                status=status.HTTP_410_GONE
            )
        
        serializer = ItineraryDetailSerializer(share.itinerary)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def export_itinerary_pdf(request, pk):
    """Export itinerary as PDF"""
    try:
        itinerary = get_object_or_404(Itinerary, id=pk, user=request.user)
        
        exporter = ItineraryExporter()
        pdf_content = exporter.export_to_pdf(itinerary)
        
        response = HttpResponse(pdf_content, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="itinerary_{itinerary.id}.pdf"'
        return response
    
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def export_itinerary_ics(request, pk):
    """Export itinerary as ICS calendar file"""
    try:
        itinerary = get_object_or_404(Itinerary, id=pk, user=request.user)
        
        exporter = ItineraryExporter()
        ics_content = exporter.export_to_ics(itinerary)
        
        response = HttpResponse(ics_content, content_type='text/calendar')
        response['Content-Disposition'] = f'attachment; filename="itinerary_{itinerary.id}.ics"'
        return response
    
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def duplicate_itinerary(request, pk):
    """Duplicate an existing itinerary"""
    try:
        original = get_object_or_404(Itinerary, id=pk, user=request.user)
        
        new_start_date = request.data.get('start_date', original.start_date)
        new_end_date = request.data.get('end_date', original.end_date)
        
        # Create duplicate
        duplicate = Itinerary.objects.create(
            user=request.user,
            destination=original.destination,
            title=f"{original.title} (Copy)",
            description=original.description,
            start_date=new_start_date,
            end_date=new_end_date,
            duration_days=original.duration_days,
            number_of_travelers=original.number_of_travelers,
            companion_type=original.companion_type,
            total_budget=original.total_budget,
            budget_per_person=original.budget_per_person,
            currency=original.currency,
            pace=original.pace,
            interests=original.interests
        )
        
        # Duplicate day plans and activities
        for day_plan in original.day_plans.all():
            new_day_plan = DayPlan.objects.create(
                itinerary=duplicate,
                day_number=day_plan.day_number,
                date=new_start_date,
                title=day_plan.title,
                notes=day_plan.notes,
                estimated_cost=day_plan.estimated_cost
            )
            
            # Duplicate activities
            for activity in day_plan.activities.all():
                Activity.objects.create(
                    day_plan=new_day_plan,
                    title=activity.title,
                    description=activity.description,
                    activity_type=activity.activity_type,
                    attraction=activity.attraction,
                    restaurant=activity.restaurant,
                    accommodation=activity.accommodation,
                    start_time=activity.start_time,
                    end_time=activity.end_time,
                    duration_minutes=activity.duration_minutes,
                    location_name=activity.location_name,
                    latitude=activity.latitude,
                    longitude=activity.longitude,
                    address=activity.address,
                    estimated_cost=activity.estimated_cost,
                    order=activity.order,
                    notes=activity.notes
                )
        
        serializer = ItineraryDetailSerializer(duplicate)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )