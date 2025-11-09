from datetime import datetime, timedelta, time
from .models import Itinerary, DayPlan, Activity
from destinations.models import Attraction, Restaurant
import random


class ItineraryGenerator:
    """
    Auto-generate day-by-day itinerary based on destination and preferences
    """
    
    def create_day_plans(self, itinerary):
        """Create day plans for the entire itinerary"""
        current_date = itinerary.start_date
        
        for day_num in range(1, itinerary.duration_days + 1):
            day_plan = DayPlan.objects.create(
                itinerary=itinerary,
                day_number=day_num,
                date=current_date,
                title=f"Day {day_num} in {itinerary.destination.name}"
            )
            
            # Generate activities for this day
            self.generate_day_activities(day_plan, itinerary)
            
            current_date += timedelta(days=1)
    
    def generate_day_activities(self, day_plan, itinerary):
        """Generate activities for a single day"""
        destination = itinerary.destination
        pace = itinerary.pace
        
        # Get available attractions and restaurants
        attractions = list(Attraction.objects.filter(
            destination=destination,
            is_active=True
        ))
        
        restaurants = list(Restaurant.objects.filter(
            destination=destination,
            is_active=True
        ))
        
        # If no data available, create placeholder activities
        if not attractions and not restaurants:
            self._create_placeholder_activities(day_plan, itinerary)
            return
        
        # Determine number of activities based on pace
        activity_counts = {
            'relaxed': 2,
            'moderate': 3,
            'fast': 4
        }
        num_attractions = activity_counts.get(pace, 3)
        
        # Select random attractions if available
        selected_attractions = random.sample(attractions, min(num_attractions, len(attractions))) if attractions else []
        
        order = 0
        
        # Morning activity
        if selected_attractions:
            self._create_attraction_activity(
                day_plan,
                selected_attractions[0],
                time(9, 0),
                order
            )
            order += 1
        else:
            # Create placeholder morning activity
            Activity.objects.create(
                day_plan=day_plan,
                title="Morning Exploration",
                description=f"Explore the local area and attractions in {destination.name}",
                activity_type='free_time',
                start_time=time(9, 0),
                end_time=time(12, 0),
                duration_minutes=180,
                location_name=destination.name,
                latitude=destination.latitude,
                longitude=destination.longitude,
                estimated_cost=0,
                order=order
            )
            order += 1
        
        # Lunch activity
        if restaurants:
            lunch_restaurant = random.choice(restaurants)
            Activity.objects.create(
                day_plan=day_plan,
                title=f"Lunch at {lunch_restaurant.name}",
                description=f"Enjoy {', '.join(lunch_restaurant.cuisine_types[:2])} cuisine",
                activity_type='meal',
                restaurant=lunch_restaurant,
                start_time=time(13, 0),
                end_time=time(14, 30),
                duration_minutes=90,
                location_name=lunch_restaurant.name,
                latitude=lunch_restaurant.latitude,
                longitude=lunch_restaurant.longitude,
                address=lunch_restaurant.address,
                estimated_cost=lunch_restaurant.average_cost_for_two / 2 * itinerary.number_of_travelers,
                order=order
            )
            order += 1
        else:
            # Placeholder lunch
            Activity.objects.create(
                day_plan=day_plan,
                title="Lunch Break",
                description="Try local restaurants and cuisine",
                activity_type='meal',
                start_time=time(13, 0),
                end_time=time(14, 30),
                duration_minutes=90,
                location_name=destination.name,
                estimated_cost=500 * itinerary.number_of_travelers,
                order=order
            )
            order += 1
        
        # Afternoon activity
        if len(selected_attractions) > 1:
            self._create_attraction_activity(
                day_plan,
                selected_attractions[1],
                time(15, 0),
                order
            )
            order += 1
        else:
            Activity.objects.create(
                day_plan=day_plan,
                title="Afternoon Activities",
                description="Sightseeing and local experiences",
                activity_type='free_time',
                start_time=time(15, 0),
                end_time=time(18, 0),
                duration_minutes=180,
                location_name=destination.name,
                estimated_cost=500 * itinerary.number_of_travelers,
                order=order
            )
            order += 1
        
        # Dinner activity
        if len(restaurants) > 1:
            dinner_restaurant = random.choice([r for r in restaurants if not hasattr(r, '_used')])
            dinner_restaurant._used = True
            Activity.objects.create(
                day_plan=day_plan,
                title=f"Dinner at {dinner_restaurant.name}",
                description=f"Evening meal featuring {', '.join(dinner_restaurant.cuisine_types[:2])}",
                activity_type='meal',
                restaurant=dinner_restaurant,
                start_time=time(19, 30),
                end_time=time(21, 0),
                duration_minutes=90,
                location_name=dinner_restaurant.name,
                latitude=dinner_restaurant.latitude,
                longitude=dinner_restaurant.longitude,
                address=dinner_restaurant.address,
                estimated_cost=dinner_restaurant.average_cost_for_two / 2 * itinerary.number_of_travelers,
                order=order
            )
            order += 1
        else:
            Activity.objects.create(
                day_plan=day_plan,
                title="Dinner",
                description="Evening meal at local restaurant",
                activity_type='meal',
                start_time=time(19, 30),
                end_time=time(21, 0),
                duration_minutes=90,
                location_name=destination.name,
                estimated_cost=700 * itinerary.number_of_travelers,
                order=order
            )
            order += 1
        
        # Add evening activity if fast pace and attractions available
        if pace == 'fast' and len(selected_attractions) > 2:
            self._create_attraction_activity(
                day_plan,
                selected_attractions[2],
                time(17, 0),
                order
            )
        
        # Calculate total day cost
        total_cost = sum(
            activity.estimated_cost
            for activity in day_plan.activities.all()
        )
        day_plan.estimated_cost = total_cost
        day_plan.save()
    
    def _create_placeholder_activities(self, day_plan, itinerary):
        """Create placeholder activities when no data is available"""
        destination = itinerary.destination
        
        activities_data = [
            {
                'title': 'Morning Sightseeing',
                'description': f'Explore famous landmarks and attractions in {destination.name}',
                'start_time': time(9, 0),
                'end_time': time(12, 0),
                'cost': 1000
            },
            {
                'title': 'Lunch at Local Restaurant',
                'description': 'Try authentic local cuisine',
                'start_time': time(13, 0),
                'end_time': time(14, 30),
                'cost': 800
            },
            {
                'title': 'Afternoon Activities',
                'description': 'Visit markets, beaches, or cultural sites',
                'start_time': time(15, 0),
                'end_time': time(18, 0),
                'cost': 500
            },
            {
                'title': 'Dinner',
                'description': 'Evening meal with local specialties',
                'start_time': time(19, 30),
                'end_time': time(21, 0),
                'cost': 1000
            }
        ]
        
        for idx, act_data in enumerate(activities_data):
            Activity.objects.create(
                day_plan=day_plan,
                title=act_data['title'],
                description=act_data['description'],
                activity_type='free_time' if 'Sightseeing' in act_data['title'] or 'Activities' in act_data['title'] else 'meal',
                start_time=act_data['start_time'],
                end_time=act_data['end_time'],
                duration_minutes=(datetime.combine(datetime.today(), act_data['end_time']) - 
                                datetime.combine(datetime.today(), act_data['start_time'])).seconds // 60,
                location_name=destination.name,
                latitude=destination.latitude,
                longitude=destination.longitude,
                estimated_cost=act_data['cost'] * itinerary.number_of_travelers,
                order=idx
            )
        
        # Update day cost
        day_plan.estimated_cost = sum(a['cost'] for a in activities_data) * itinerary.number_of_travelers
        day_plan.save()
    
    def _create_attraction_activity(self, day_plan, attraction, start_time, order):
        """Helper to create an attraction visit activity"""
        duration = int(attraction.typical_visit_duration * 60)
        start_dt = datetime.combine(datetime.today(), start_time)
        end_dt = start_dt + timedelta(minutes=duration)
        
        Activity.objects.create(
            day_plan=day_plan,
            title=f"Visit {attraction.name}",
            description=attraction.description,
            activity_type='attraction',
            attraction=attraction,
            start_time=start_time,
            end_time=end_dt.time(),
            duration_minutes=duration,
            location_name=attraction.name,
            latitude=attraction.latitude,
            longitude=attraction.longitude,
            estimated_cost=attraction.entry_fee * day_plan.itinerary.number_of_travelers,
            order=order
        )


class ItineraryOptimizer:
    """
    Optimize itinerary based on geography, time, and budget
    """
    
    def optimize_route(self, day_plan):
        """Optimize activity order based on geographical proximity"""
        activities = list(day_plan.activities.all().order_by('start_time'))
        
        if len(activities) < 2:
            return
        
        # Simple optimization: reorder based on location proximity
        optimized = [activities[0]]
        remaining = activities[1:]
        
        while remaining:
            last_activity = optimized[-1]
            if last_activity.latitude and last_activity.longitude:
                # Find nearest next activity
                nearest = min(
                    remaining,
                    key=lambda a: self._distance(
                        last_activity.latitude, last_activity.longitude,
                        a.latitude or 0, a.longitude or 0
                    ) if a.latitude else float('inf')
                )
                optimized.append(nearest)
                remaining.remove(nearest)
            else:
                optimized.append(remaining.pop(0))
        
        # Update order
        for idx, activity in enumerate(optimized):
            activity.order = idx
            activity.save()
    
    def _distance(self, lat1, lon1, lat2, lon2):
        """Calculate simple distance between two points"""
        return ((lat2 - lat1) ** 2 + (lon2 - lon1) ** 2) ** 0.5


class ItineraryExporter:
    """
    Export itinerary to different formats (PDF, ICS calendar)
    """
    
    def export_to_pdf(self, itinerary):
        """Export itinerary as PDF with complete details"""
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER, TA_LEFT
        from io import BytesIO
        
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
        elements = []
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1a237e'),
            spaceAfter=20,
            alignment=TA_CENTER
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#283593'),
            spaceAfter=10,
            spaceBefore=15
        )
        
        # Title
        elements.append(Paragraph(itinerary.title, title_style))
        elements.append(Spacer(1, 20))
        
        # Trip Overview
        overview_data = [
            ['Destination:', itinerary.destination.name],
            ['Duration:', f"{itinerary.duration_days} days"],
            ['Dates:', f"{itinerary.start_date.strftime('%d %b %Y')} to {itinerary.end_date.strftime('%d %b %Y')}"],
            ['Travelers:', f"{itinerary.number_of_travelers} ({itinerary.companion_type})"],
            ['Total Budget:', f"{itinerary.currency} {itinerary.total_budget:,.2f}"],
            ['Per Person:', f"{itinerary.currency} {itinerary.budget_per_person:,.2f}"],
        ]
        
        overview_table = Table(overview_data, colWidths=[2*inch, 4*inch])
        overview_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e8eaf6')),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#1a237e')),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        elements.append(overview_table)
        elements.append(Spacer(1, 30))
        
        # Day-by-day itinerary
        for day_plan in itinerary.day_plans.all().order_by('day_number'):
            # Day heading
            day_heading = f"Day {day_plan.day_number}: {day_plan.date.strftime('%A, %d %B %Y')}"
            elements.append(Paragraph(day_heading, heading_style))
            
            # Activities for this day
            activities = day_plan.activities.all().order_by('order', 'start_time')
            
            if activities:
                for activity in activities:
                    # Activity time and title
                    time_str = f"{activity.start_time.strftime('%I:%M %p')} - {activity.end_time.strftime('%I:%M %p')}"
                    activity_title = f"<b>{time_str}</b>: {activity.title}"
                    elements.append(Paragraph(activity_title, styles['Normal']))
                    
                    # Activity description
                    if activity.description:
                        elements.append(Paragraph(f"&nbsp;&nbsp;&nbsp;&nbsp;{activity.description}", styles['BodyText']))
                    
                    # Location
                    if activity.location_name:
                        elements.append(Paragraph(f"&nbsp;&nbsp;&nbsp;&nbsp;<i>Location: {activity.location_name}</i>", styles['Normal']))
                    
                    # Cost
                    if activity.estimated_cost > 0:
                        elements.append(Paragraph(f"&nbsp;&nbsp;&nbsp;&nbsp;Cost: {itinerary.currency} {activity.estimated_cost:,.2f}", styles['Normal']))
                    
                    elements.append(Spacer(1, 8))
                
                # Day total
                day_total = f"<b>Day {day_plan.day_number} Total: {itinerary.currency} {day_plan.estimated_cost:,.2f}</b>"
                elements.append(Paragraph(day_total, styles['Normal']))
            else:
                elements.append(Paragraph("<i>No activities planned for this day</i>", styles['Italic']))
            
            elements.append(Spacer(1, 20))
        
        # Build PDF
        doc.build(elements)
        pdf = buffer.getvalue()
        buffer.close()
        return pdf
    
    def export_to_ics(self, itinerary):
        """Export itinerary as ICS calendar file"""
        from icalendar import Calendar, Event
        from datetime import datetime
        
        cal = Calendar()
        cal.add('prodid', '-//Travel Chatbot//Itinerary//EN')
        cal.add('version', '2.0')
        
        for day_plan in itinerary.day_plans.all():
            for activity in day_plan.activities.all():
                event = Event()
                event.add('summary', activity.title)
                event.add('description', activity.description)
                
                # Combine date and time
                start_dt = datetime.combine(day_plan.date, activity.start_time)
                end_dt = datetime.combine(day_plan.date, activity.end_time)
                
                event.add('dtstart', start_dt)
                event.add('dtend', end_dt)
                
                if activity.location_name:
                    event.add('location', activity.location_name)
                
                cal.add_component(event)
        
        return cal.to_ical()