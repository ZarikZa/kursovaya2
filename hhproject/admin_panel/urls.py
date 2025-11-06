from django.urls import path
from .views import *

urlpatterns = [
    path('', admin_dashboard, name='admin_dashboard'),
    
    path('companies/', company_moderation, name='admin_company_moderation'),
    path('companies/<int:company_id>/', company_detail, name='admin_company_detail'),
    
    path('backups/', backup_management, name='admin_backup_management'),
    path('backups/<int:backup_id>/download/', download_backup, name='admin_download_backup'),
    path('backups/<int:backup_id>/delete/', delete_backup, name='admin_delete_backup'),
    path('backups/cancel-restore/', cancel_restore, name='admin_cancel_restore'),
    
    path('logs/', admin_logs, name='admin_logs'),
    path('logs/clear/', clear_logs, name='admin_clear_logs'),
    
    # API
    path('api/company-stats/', api_company_stats, name='api_company_stats'),
    path('api/recent-activity/', api_recent_activity, name='api_recent_activity'),

    path('site-admins/',admin_management, name='admin_management'),
    path('site-admins/create/',create_site_admin, name='create_site_admin'),
    path('site-admins/<int:admin_id>/edit/',edit_site_admin, name='edit_site_admin'),
    path('site-admins/<int:admin_id>/toggle/',toggle_site_admin_status, name='toggle_site_admin_status'),
    path('site-admins/<int:admin_id>/delete/',delete_site_admin, name='delete_site_admin'),
]