from django.conf import settings
from notifications.twilio_service import send_whatsapp
from .models import Ticket
from django.template.loader import render_to_string

def send_ticket_assignment_notification(ticket: Ticket):
    """Send notification when a ticket is assigned to a contractor"""
    if not ticket.assignee or not ticket.assignee.phone_number:
        return
    
    site_name = ticket.site.name if ticket.site else 'the specified site'
    
    # Message to contractor
    contractor_message = f"""
    🎯 NEW TICKET ASSIGNED - {ticket.title}
    
    You've been assigned a new ticket by {ticket.created_by.get_full_name() or ticket.created_by.username}.
    
    📌 {ticket.title}
    📝 {ticket.description[:100]}...
    🏢 Site: {site_name}
    ⚠️ Priority: {ticket.get_priority_display()}
    
    Please confirm when you can start working on this ticket.
    """
    
    # Message to admin who assigned the ticket
    admin_message = f"""
    ✅ TICKET ASSIGNED - {ticket.title}
    
    You've assigned ticket #{ticket.id} to {ticket.assignee.get_full_name() or ticket.assignee.username}.
    
    We've notified them and will update you when they confirm.
    """
    
    try:
        # Notify contractor
        send_whatsapp(
            to=ticket.assignee.phone_number,
            body=contractor_message
        )
        
        # Notify admin who assigned the ticket
        if ticket.created_by.phone_number:
            send_whatsapp(
                to=ticket.created_by.phone_number,
                body=admin_message
            )
            
    except Exception as e:
        print(f"Failed to send WhatsApp notification: {e}")

def send_ticket_status_update(ticket: Ticket, previous_status: str):
    """Send notification when ticket status changes"""
    if not ticket.assignee:
        return
    
    site_name = ticket.site.name if ticket.site else 'the specified site'
    status_updates = {
        'ASSIGNED': {
            'title': 'TICKET ASSIGNED',
            'to_contractor': f"""
            🎯 TICKET ASSIGNED - {ticket.title}
            
            You've been assigned a new ticket by {ticket.created_by.get_full_name() or ticket.created_by.username}.
            
            📌 {ticket.title}
            📝 {ticket.description[:100]}...
            🏢 Site: {site_name}
            
            Please confirm when you can start working on this ticket.
            """,
            'to_admin': f"""
            ✅ TICKET ASSIGNED - {ticket.title}
            
            You've assigned ticket #{ticket.id} to {ticket.assignee.get_full_name() or ticket.assignee.username}.
            
            We've notified them and will update you when they confirm.
            """
        },
        'IN_PROGRESS': {
            'title': 'WORK STARTED',
            'to_contractor': f"""
            🚀 WORK STARTED - {ticket.title}
            
            You've started working on ticket #{ticket.id}.
            
            Please update the ticket status when you complete the work.
            """,
            'to_admin': f"""
            🚀 WORK IN PROGRESS - {ticket.title}
            
            {ticket.assignee.get_full_name() or ticket.assignee.username} has started working on ticket #{ticket.id}.
            
            You'll be notified when the work is completed.
            """
        },
        'RESOLVED': {
            'title': 'WORK COMPLETED',
            'to_contractor': f"""
            ✅ WORK COMPLETED - {ticket.title}
            
            You've marked ticket #{ticket.id} as completed.
            
            Waiting for site manager review and approval.
            """,
            'to_admin': f"""
            ✅ WORK COMPLETED - {ticket.title}
            
            {ticket.assignee.get_full_name() or ticket.assignee.username} has marked ticket #{ticket.id} as completed.
            
            Please review the work and close the ticket if everything is in order.
            """
        },
        'CLOSED': {
            'title': 'TICKET CLOSED',
            'to_contractor': f"""
            🎉 TICKET CLOSED - {ticket.title}
            
            Ticket #{ticket.id} has been closed by {ticket.closed_by.get_full_name() if ticket.closed_by else 'the site manager'}.
            
            Rating: {'⭐' * (ticket.contractor_rating or 0)}
            
            Thank you for your work!
            """,
            'to_admin': f"""
            🎉 TICKET CLOSED - {ticket.title}
            
            You've successfully closed ticket #{ticket.id}.
            
            Contractor: {ticket.assignee.get_full_name() or ticket.assignee.username}
            Rating: {'⭐' * (ticket.contractor_rating or 0)}
            """
        },
        'COMPLETED': {
            'title': 'Work Completed',
            'message': f'Ticket #{ticket.id} has been marked as completed'
        },
        'CLOSED': {
            'title': 'Ticket Closed',
            'message': f'Ticket #{ticket.id} has been closed'
        }
    }
    
    update = status_updates.get(ticket.status)
    if not update:
        return
    
    try:
        # Notify contractor
        if ticket.assignee.phone_number and 'to_contractor' in update:
            send_whatsapp(
                to=ticket.assignee.phone_number,
                body=update['to_contractor'].strip()
            )
        
        # Notify admin/site manager
        if ticket.created_by.phone_number and 'to_admin' in update and ticket.assignee != ticket.created_by:
            send_whatsapp(
                to=ticket.created_by.phone_number,
                body=update['to_admin'].strip()
            )
            
        # For closed tickets, also notify other admins
        if ticket.status == 'CLOSED':
            from django.contrib.auth import get_user_model
            User = get_user_model()
            
            admins = User.objects.filter(
                tenant=ticket.tenant,
                is_superuser=True
            ).exclude(
                id__in=[ticket.created_by_id, ticket.assignee_id]
            )
            
            for admin in admins:
                if admin.phone_number:
                    send_whatsapp(
                        to=admin.phone_number,
                        body=f"""
                        ℹ️ TICKET CLOSED - {ticket.title}
                        
                        Ticket #{ticket.id} has been closed by {ticket.closed_by.get_full_name() if ticket.closed_by else 'a site manager'}.
                        
                        Contractor: {ticket.assignee.get_full_name() or ticket.assignee.username}
                        Rating: {'⭐' * (ticket.contractor_rating or 0)}
                        """.strip()
                    )
                    
    except Exception as e:
        print(f"Failed to send status update notifications: {e}")


def send_contractor_confirmation_notification(ticket: Ticket):
    """Send notification when contractor confirms they can work on the ticket"""
    if not ticket.assignee or not ticket.created_by.phone_number:
        return
    
    message = f"""
    ✅ CONTRACTOR CONFIRMATION - {ticket.title}
    
    {ticket.assignee.get_full_name() or ticket.assignee.username} has confirmed they will work on ticket #{ticket.id}.
    
    📌 {ticket.title}
    🏢 Site: {ticket.site.name if ticket.site else 'N/A'}
    
    You can now mark the ticket as 'In Progress' when they start working.
    """
    
    try:
        send_whatsapp(
            to=ticket.created_by.phone_number,
            body=message.strip()
        )
    except Exception as e:
        print(f"Failed to send contractor confirmation notification: {e}")
