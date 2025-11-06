from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.core.files import File
from datetime import timedelta
import os
from .forms import SiteAdminCreateForm, SiteAdminEditForm

from home.models import Company, User, Employee, Vacancy, StatusVacancies
from home.models import Backup, AdminLog
from .forms import CompanyModerationForm, BackupForm
from .procedure_manager import ProcedureBackupManager

# Функции проверки прав доступа
def is_admin(user):
    """Проверка что пользователь администратор (суперпользователь или adminsite)"""
    return user.is_authenticated and (user.is_superuser or user.user_type == 'adminsite')

def is_superuser_only(user):
    """Проверка что пользователь ТОЛЬКО суперпользователь"""
    return user.is_authenticated and user.is_superuser

def get_admin_context(request):
    pending_count = Company.objects.filter(status=Company.STATUS_PENDING).count()
    site_admins_count = User.objects.filter(user_type='adminsite', is_active=True).count()
    
    return {
        'pending_companies_count': pending_count,
        'site_admins_count': site_admins_count,
        'is_superuser': request.user.is_superuser,
    }

@user_passes_test(is_admin, login_url='/admin/login/')
def admin_dashboard(request):
    """Главная страница админки"""
    context = get_admin_context(request)
    
    # Статистика компаний
    pending_companies = Company.objects.filter(status=Company.STATUS_PENDING)
    total_companies = Company.objects.count()
    approved_companies = Company.objects.filter(status=Company.STATUS_APPROVED).count()
    rejected_companies = Company.objects.filter(status=Company.STATUS_REJECTED).count()
    
    # Последние логи
    recent_logs = AdminLog.objects.all().order_by('-created_at')[:10]
    
    # Статистика пользователей
    total_users = User.objects.count()
    company_users = User.objects.filter(user_type='company').count()
    applicant_users = User.objects.filter(user_type='applicant').count()
    
    context.update({
        'pending_count': pending_companies.count(),
        'total_companies': total_companies,
        'approved_companies': approved_companies,
        'rejected_companies': rejected_companies,
        'total_users': total_users,
        'company_users': company_users,
        'applicant_users': applicant_users,
        'recent_logs': recent_logs,
    })
    return render(request, 'admin_panel/dashboard.html', context)

from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags

@user_passes_test(is_admin, login_url='/admin/login/')
def company_moderation(request):
    """Страница модерации компаний"""
    context = get_admin_context(request)
    
    companies = Company.objects.all().order_by('-created_at')
    pending_companies = companies.filter(status=Company.STATUS_PENDING)
    
    if request.method == 'POST':
        company_id = request.POST.get('company_id')
        status = request.POST.get('status')
        
        if company_id and status:
            try:
                company = Company.objects.get(id=company_id)
                
                old_status = company.status
                company.status = status
                company.save()
                
                if old_status != company.status:
                    # Отправка email уведомления
                    email_sent = send_company_status_email(company, old_status)
                    
                    if company.status == Company.STATUS_APPROVED:
                        action = 'company_approved'
                        details = f'Компания {company.name} одобрена'
                    elif company.status == Company.STATUS_REJECTED:
                        action = 'company_rejected'
                        details = f'Компания {company.name} отклонена'
                    else:
                        action = 'company_updated'
                        details = f'Статус компании {company.name} изменен на {company.get_status_display()}'
                    
                    # Добавляем информацию об email в детали
                    if email_sent:
                        details += ' (email отправлен)'
                    else:
                        details += ' (ошибка отправки email)'
                    
                    AdminLog.objects.create(
                        admin=request.user,
                        action=action,
                        target_company=company,
                        details=details
                    )
            except:
                pass
                    
    context.update({
        'pending_companies': pending_companies,
        'all_companies': companies,
        'status_choices': Company.STATUS_CHOICES,
    })
    return render(request, 'admin_panel/company_moderation.html', context)

@user_passes_test(is_admin, login_url='/admin/login/')
def company_detail(request, company_id):
    """Детальная информация о компании"""
    context = get_admin_context(request)
    
    company = get_object_or_404(Company, id=company_id)
    
    if request.method == 'POST':
        form = CompanyModerationForm(request.POST, instance=company)
        if form.is_valid():
            old_status = company.status
            company = form.save()
            
            if old_status != company.status:
                # Отправка email уведомления
                send_company_status_email(company, old_status)
                
                if company.status == Company.STATUS_APPROVED:
                    action = 'company_approved'
                    details = f'Компания {company.name} одобрена через детальную страницу'
                elif company.status == Company.STATUS_REJECTED:
                    action = 'company_rejected' 
                    details = f'Компания {company.name} отклонена через детальную страницу'
                else:
                    action = 'company_updated'
                    details = f'Статус компании {company.name} изменен на {company.get_status_display()}'
                
                AdminLog.objects.create(
                    admin=request.user,
                    action=action,
                    target_company=company,
                    details=details
                )
            
            return redirect('admin_company_moderation')
    else:
        form = CompanyModerationForm(instance=company)
    
    context.update({
        'company': company,
        'form': form,
    })
    return render(request, 'admin_panel/company_detail.html', context)

def send_company_status_email(company, old_status):
    
    user_email = company.user.email
    company_name = company.name
    new_status = company.status
    status_display = company.get_status_display()
    
    if new_status == 'approved':
        status_title = "Компания одобрена!"
        status_description = "Ваша компания успешно прошла модерацию и теперь может размещать вакансии на нашей платформе."
        status_icon = "🎉"
        status_color = "#10b981"
    elif new_status == 'rejected':
        status_title = "Требуется внимание"
        status_description = "К сожалению, ваша компания не прошла модерацию. Пожалуйста, свяжитесь с поддержкой для уточнения деталей."
        status_icon = "⚠️"
        status_color = "#ef4444"
    else:
        status_title = "Статус обновлен"
        status_description = f"Статус вашей компании изменен на: {status_display}"
        status_icon = "📋"
        status_color = "#2563eb"
    
    try:
        subject = f'Статус вашей компании на HR-Lab изменен'
        
        html_message = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{
                    font-family: 'Inter', 'Arial', sans-serif;
                    line-height: 1.6;
                    color: #1e293b;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 0;
                    background: linear-gradient(135deg, #2563eb 0%, #1e293b 100%);
                }}
                .container {{
                    background: white;
                    margin: 20px;
                    border-radius: 20px;
                    overflow: hidden;
                    box-shadow: 0 15px 35px rgba(0, 0, 0, 0.2);
                }}
                .header {{
                    background: linear-gradient(135deg, #2563eb 0%, #1e293b 100%);
                    color: white;
                    padding: 40px 30px;
                    text-align: center;
                }}
                .header h1 {{
                    margin: 0;
                    font-size: 28px;
                    font-weight: 700;
                }}
                .header p {{
                    margin: 10px 0 0 0;
                    opacity: 0.9;
                    font-size: 16px;
                }}
                .content {{
                    padding: 40px 30px;
                }}
                .status-card {{
                    background: rgba(37, 99, 235, 0.05);
                    border: 1px solid rgba(37, 99, 235, 0.2);
                    border-radius: 15px;
                    padding: 25px;
                    margin: 25px 0;
                    text-align: center;
                }}
                .status-icon {{
                    font-size: 48px;
                    margin-bottom: 15px;
                }}
                .status-title {{
                    font-size: 20px;
                    font-weight: 700;
                    color: #1e293b;
                    margin-bottom: 10px;
                }}
                .status-description {{
                    color: #64748b;
                    font-size: 16px;
                    line-height: 1.5;
                }}
                .approved {{
                    background: rgba(16, 185, 129, 0.05);
                    border-color: rgba(16, 185, 129, 0.2);
                }}
                .approved .status-title {{
                    color: #065f46;
                }}
                .rejected {{
                    background: rgba(239, 68, 68, 0.05);
                    border-color: rgba(239, 68, 68, 0.2);
                }}
                .rejected .status-title {{
                    color: #991b1b;
                }}
                .action-button {{
                    display: inline-block;
                    background: linear-gradient(45deg, #2563eb, #1e40af);
                    color: white;
                    padding: 14px 32px;
                    text-decoration: none;
                    border-radius: 25px;
                    font-weight: 600;
                    font-size: 16px;
                    margin: 20px 0;
                    transition: all 0.3s ease;
                }}
                .action-button:hover {{
                    background: linear-gradient(45deg, #1e40af, #2563eb);
                    transform: translateY(-2px);
                    box-shadow: 0 5px 15px rgba(37, 99, 235, 0.3);
                }}
                .info-section {{
                    background: #f8fafc;
                    border-radius: 12px;
                    padding: 20px;
                    margin: 25px 0;
                }}
                .info-item {{
                    display: flex;
                    justify-content: space-between;
                    padding: 10px 0;
                    border-bottom: 1px solid #e2e8f0;
                }}
                .info-item:last-child {{
                    border-bottom: none;
                }}
                .info-label {{
                    color: #64748b;
                    font-weight: 500;
                }}
                .info-value {{
                    color: #1e293b;
                    font-weight: 600;
                }}
                .footer {{
                    background: #f1f5f9;
                    padding: 30px;
                    text-align: center;
                    border-top: 1px solid #e2e8f0;
                }}
                .footer p {{
                    margin: 5px 0;
                    color: #64748b;
                    font-size: 14px;
                }}
                .contact-info {{
                    margin-top: 15px;
                    padding-top: 15px;
                    border-top: 1px solid #e2e8f0;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>HR-Lab</h1>
                    <p>Уведомление о статусе компании</p>
                </div>
                
                <div class="content">
                    <h2 style="color: #1e293b; margin-top: 0;">Уважаемый представитель компании!</h2>
                    <p style="color: #64748b; font-size: 16px;">
                        Статус вашей компании <strong>"{company_name}"</strong> на платформе HR-Lab был обновлен.
                    </p>
                    
                    <div class="status-card {new_status}">
                        <div class="status-icon">{status_icon}</div>
                        <div class="status-title">{status_title}</div>
                        <div class="status-description">{status_description}</div>
                    </div>
                    
                    <div class="info-section">
                        <div class="info-item">
                            <span class="info-label">Компания:</span>
                            <span class="info-value">{company_name}</span>
                        </div>
                        <div class="info-item">
                            <span class="info-label">Новый статус:</span>
                            <span class="info-value" style="color: {status_color}; font-weight: 700;">
                                {status_display}
                            </span>
                        </div>
                        <div class="info-item">
                            <span class="info-label">Дата обновления:</span>
                            <span class="info-value">{company.created_at.strftime('%d.%m.%Y')}</span>
                        </div>
                    </div>
                    
                    <p style="color: #64748b; font-size: 15px; text-align: center;">
                        Если у вас возникли вопросы, не стесняйтесь обращаться в нашу службу поддержки.
                    </p>
                </div>
                
                <div class="footer">
                    <p><strong>С уважением, команда HR-Lab</strong></p>
                    <p>Мы помогаем компаниям находить лучших сотрудников</p>
                    <div class="contact-info">
                        <p>Email: hr-labogency@mail.ru</p>
                    </div>
                    <p style="font-size: 12px; margin-top: 20px; color: #94a3b8;">
                        Это автоматическое сообщение, пожалуйста, не отвечайте на него.
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Текстовая версия для почтовых клиентов, которые не поддерживают HTML
        plain_message = f"""
        Уважаемый представитель компании "{company_name}"!

        Статус вашей компании на платформе HR-Lab был изменен.

        Новый статус: {status_display}

        {status_description}

        Для управления вашей компанией перейдите в личный кабинет:
        http://127.0.0.1:8000/compani/

        С уважением,
        Команда HR-Lab

        ---
        Email: support@hr-lab.ru
        Телефон: +7 (999) 123-45-67
        """
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user_email],
            html_message=html_message,
            fail_silently=False,
        )
        
        return True
        
    except Exception as e:
        print(f"❌ [EMAIL] ОШИБКА: {str(e)}")
        return False

@user_passes_test(is_admin, login_url='/admin/login/')
def vacancy_management(request):
    """Управление вакансиями (для всех админов)"""
    context = get_admin_context(request)
    
    vacancies = Vacancy.objects.all().select_related('company', 'status').order_by('-created_date')
    
    # Фильтры
    status_filter = request.GET.get('status', '')
    if status_filter:
        vacancies = vacancies.filter(status__id=status_filter)
    
    search_query = request.GET.get('search', '')
    if search_query:
        vacancies = vacancies.filter(position__icontains=search_query)
    
    context.update({
        'vacancies': vacancies,
        'status_choices': StatusVacancies.objects.all(),
        'current_status': status_filter,
        'search_query': search_query,
    })
    return render(request, 'admin_panel/vacancy_management.html', context)

@user_passes_test(is_admin, login_url='/admin/login/')
def backup_management(request):
    """Управление бэкапами"""
    context = get_admin_context(request)
    
    backups = Backup.objects.all().order_by('-created_at')
    backup_manager = ProcedureBackupManager()
    
    procedure_tests = backup_manager.test_procedures()
    db_stats = []
    
    if request.method == 'POST':
        if 'create_backup' in request.POST:
            backup_type = request.POST.get('backup_type', 'database')
            
            try:
                result = backup_manager.create_database_backup()
                
                with open(result['filepath'], 'rb') as f:
                    backup = Backup(
                        name=result['filename'],
                        backup_type=result['backup_type'],
                        file_size=result['file_size'],
                        created_by=request.user
                    )
                    backup.backup_file.save(result['filename'], File(f))
                    backup.save()
                
                backup_format = result.get('format', 'unknown')
                AdminLog.objects.create(
                    admin=request.user,
                    action='backup_created',
                    details=f'Создан бэкап ({backup_format}): {result["filename"]} ({backup.get_file_size_display()})'
                )
                
                
                
            except Exception as e:
                pass
        elif 'restore_backup' in request.POST:
            backup_id = request.POST.get('backup_id')
            if backup_id:
                backup = get_object_or_404(Backup, id=backup_id)
                
                try:
                    if 'confirm_restore' not in request.POST:
                        request.session['pending_restore'] = backup_id
                        return redirect('admin_backup_management')
                    
                    backup_manager.restore_database_backup(backup.backup_file)
                    
                    AdminLog.objects.create(
                        admin=request.user,
                        action='backup_restored',
                        details=f'Восстановлен бэкап: {backup.name}'
                    )
                    
                    if 'pending_restore' in request.session:
                        del request.session['pending_restore']
                    
                    
                except Exception as e:
                    pass
        
        elif 'upload_backup' in request.POST:
            form = BackupForm(request.POST, request.FILES)
            if form.is_valid():
                backup_file = request.FILES['backup_file']
                
                allowed_extensions = ['.sql', '.zip', '.dat', '.backup']
                file_ext = os.path.splitext(backup_file.name)[1].lower()
                
                if file_ext not in allowed_extensions:
                   pass
                else:
                    backup = Backup(
                        name=backup_file.name,
                        backup_type='full',
                        file_size=backup_file.size,
                        created_by=request.user
                    )
                    backup.backup_file.save(backup_file.name, backup_file)
                    backup.save()
                    
                    AdminLog.objects.create(
                        admin=request.user,
                        action='backup_uploaded',
                        details=f'Загружен бэкап: {backup_file.name}'
                    )
                    
        
        elif 'get_stats' in request.POST:
            try:
                db_stats = backup_manager.get_database_stats()
                request.session['db_stats'] = db_stats
            except Exception as e:
                pass
    db_stats = request.session.get('db_stats', [])
    pending_restore_id = request.session.get('pending_restore')
    pending_restore = None
    if pending_restore_id:
        pending_restore = get_object_or_404(Backup, id=pending_restore_id)
    
    context.update({
        'backups': backups,
        'procedure_tests': procedure_tests,
        'db_stats': db_stats,
        'pending_restore': pending_restore,
        'form': BackupForm(),
        'backup_types': Backup.BACKUP_TYPES,
    })
    return render(request, 'admin_panel/backup_management.html', context)

@user_passes_test(is_admin, login_url='/admin/login/')
def download_backup(request, backup_id):
    """Скачивание бэкапа"""
    backup = get_object_or_404(Backup, id=backup_id)
    
    try:
        response = HttpResponse(backup.backup_file, content_type='application/octet-stream')
        response['Content-Disposition'] = f'attachment; filename="{backup.name}"'
        
        AdminLog.objects.create(
            admin=request.user,
            action='backup_downloaded',
            details=f'Скачан бэкап: {backup.name}'
        )
        
        return response
        
    except Exception as e:
        return redirect('admin_backup_management')

@user_passes_test(is_admin, login_url='/admin/login/')
def delete_backup(request, backup_id):
    """Удаление бэкапа"""
    backup = get_object_or_404(Backup, id=backup_id)
    
    try:
        backup_name = backup.name
        backup.delete()
        
        AdminLog.objects.create(
            admin=request.user,
            action='backup_deleted',
            details=f'Удален бэкап: {backup_name}'
        )
        
    except Exception as e:
        pass
    return redirect('admin_backup_management')

@user_passes_test(is_admin, login_url='/admin/login/')
def cancel_restore(request):
    """Отмена ожидающего восстановления"""
    if 'pending_restore' in request.session:
        del request.session['pending_restore']
    
    return redirect('admin_backup_management')

@user_passes_test(is_admin, login_url='/admin/login/')
def admin_logs(request):
    """Просмотр логов администраторов"""
    context = get_admin_context(request)
    
    logs = AdminLog.objects.all().order_by('-created_at')
    
    action_filter = request.GET.get('action', '')
    if action_filter:
        logs = logs.filter(action=action_filter)
    
    search_query = request.GET.get('search', '')
    if search_query:
        logs = logs.filter(details__icontains=search_query)
    
    context.update({
        'logs': logs,
        'action_choices': AdminLog.ACTION_CHOICES,
        'current_action': action_filter,
        'search_query': search_query,
    })
    return render(request, 'admin_panel/admin_logs.html', context)

@user_passes_test(is_admin, login_url='/admin/login/')
def clear_logs(request):
    """Очистка логов"""
    if request.method == 'POST':
        from datetime import datetime
        days_old = int(request.POST.get('days_old', 30))
        cutoff_date = datetime.now() - timedelta(days=days_old)
        
        deleted_count = AdminLog.objects.filter(created_at__lt=cutoff_date).delete()[0]
        
        AdminLog.objects.create(
            admin=request.user,
            action='logs_cleared',
            details=f'Очищено {deleted_count} логов старше {days_old} дней'
        )
        
    
    return redirect('admin_logs')

@user_passes_test(is_admin, login_url='/admin/login/')
def api_company_stats(request):
    """API для получения статистики компаний"""
    stats = {
        'pending': Company.objects.filter(status=Company.STATUS_PENDING).count(),
        'approved': Company.objects.filter(status=Company.STATUS_APPROVED).count(),
        'rejected': Company.objects.filter(status=Company.STATUS_REJECTED).count(),
        'total': Company.objects.count(),
    }
    return JsonResponse(stats)

@user_passes_test(is_admin, login_url='/admin/login/')
def api_recent_activity(request):
    """API для получения последней активности"""
    logs = AdminLog.objects.all().order_by('-created_at')[:5]
    
    activity = []
    for log in logs:
        activity.append({
            'admin': log.admin.username,
            'action': log.get_action_display(),
            'details': log.details,
            'timestamp': log.created_at.strftime('%Y-%m-%d %H:%M'),
            'company': log.target_company.name if log.target_company else None,
        })
    
    return JsonResponse({'activity': activity})

# Функции управления админами - ТОЛЬКО для суперпользователей
@user_passes_test(is_superuser_only, login_url='/admin/login/')
def admin_management(request):
    """Управление администраторами сайта (только для superuser)"""
    context = get_admin_context(request)
    site_admins = User.objects.filter(user_type='adminsite').select_related('employee')
    
    context.update({
        'site_admins': site_admins,
    })
    return render(request, 'admin_panel/admin_management.html', context)

@user_passes_test(is_superuser_only, login_url='/admin/login/')
def create_site_admin(request):
    """Создание нового администратора сайта"""
    context = get_admin_context(request)
    
    if request.method == 'POST':
        form = SiteAdminCreateForm(request.POST)
        if form.is_valid():
            try:
                admin = form.save()
                AdminLog.objects.create(
                    admin=request.user,
                    action='admin_created',
                    details=f'Создан администратор сайта: {admin.get_full_name()} ({admin.email})'
                )
                return redirect('admin_management')
            except Exception as e:
                pass
    else:
        form = SiteAdminCreateForm()
    
    context.update({
        'form': form,
        'title': 'Создание администратора сайта'
    })
    return render(request, 'admin_panel/admin_form.html', context)

@user_passes_test(is_superuser_only, login_url='/admin/login/')
def edit_site_admin(request, admin_id):
    """Редактирование администратора сайта"""
    context = get_admin_context(request)
    admin_user = get_object_or_404(User, id=admin_id, user_type='adminsite')
    
    try:
        admin_employee = Employee.objects.get(user=admin_user)
    except Employee.DoesNotExist:
        # Если записи Employee нет - создаем
        admin_employee = Employee.objects.create(
            user=admin_user,
            first_name=admin_user.first_name,
            last_name=admin_user.last_name,
            access_level='admin'
        )
    
    if request.method == 'POST':
        form = SiteAdminEditForm(request.POST, instance=admin_employee)
        if form.is_valid():
            try:
                admin = form.save()
                AdminLog.objects.create(
                    admin=request.user,
                    action='admin_updated',
                    details=f'Обновлен администратор сайта: {admin.user.get_full_name()} ({admin.user.email})'
                )
                return redirect('admin_management')
            except Exception as e:
                pass
    else:
        form = SiteAdminEditForm(instance=admin_employee)
    
    context.update({
        'form': form,
        'admin': admin_user,
        'title': 'Редактирование администратора сайта'
    })
    return render(request, 'admin_panel/admin_form.html', context)

@user_passes_test(is_superuser_only, login_url='/admin/login/')
def toggle_site_admin_status(request, admin_id):
    """Активация/деактивация администратора сайта"""
    admin_user = get_object_or_404(User, id=admin_id, user_type='adminsite')
    
    if admin_user == request.user:
        return redirect('admin_management')
    
    if admin_user.is_active:
        admin_user.is_active = False
        action = 'deactivated'
        message = f'✅ Администратор сайта {admin_user.get_full_name()} деактивирован'
    else:
        admin_user.is_active = True
        action = 'activated'
        message = f'✅ Администратор сайта {admin_user.get_full_name()} активирован'
    
    admin_user.save()
    
    AdminLog.objects.create(
        admin=request.user,
        action=f'admin_{action}',
        details=f'Администратор сайта {admin_user.get_full_name()} {action}'
    )
    
    return redirect('admin_management')

@user_passes_test(is_superuser_only, login_url='/admin/login/')
def delete_site_admin(request, admin_id):
    """Удаление администратора сайта"""
    admin_user = get_object_or_404(User, id=admin_id, user_type='adminsite')
    
    if admin_user == request.user:
        return redirect('admin_management')
    
    admin_name = admin_user.get_full_name()
    admin_email = admin_user.email
    
    admin_user.delete()
    
    AdminLog.objects.create(
        admin=request.user,
        action='admin_deleted',
        details=f'Удален администратор сайта: {admin_name} ({admin_email})'
    )
    
    return redirect('admin_management')