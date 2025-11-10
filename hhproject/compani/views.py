from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from home.models import *
from django.views.generic import CreateView, UpdateView
from django.contrib.auth import login, update_session_auth_hash, authenticate
from django.contrib import messages
from django.core.mail import send_mail, get_connection
from django.conf import settings
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
from smtplib import SMTPAuthenticationError, SMTPServerDisconnected, SMTPConnectError
from .forms import *
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse

def account_pending(request):
    return render(request, 'auth/account_pending.html')

def home_comp(request):
    return render(request, 'compani/homeComp.html')

class CompanyRegisterView(CreateView):
    model = User
    form_class = CompanySignUpForm
    template_name = 'auth/register_comp.html'

    def form_valid(self, form):
        form.save()
        return redirect('account_pending')

def company_profile(request):
    if not request.user.is_authenticated or request.user.user_type != 'company':
        return redirect('login_user')
    
    company = request.user.company
    vacancies = company.vacancy_set.all()
    employees = Employee.objects.filter(company=company)
    
    context = {
        'company': company,
        'vacancies': vacancies,
        'employees': employees,
        'user': request.user
    }
    return render(request, 'compani/profile/company_profile.html', context)

class CompanyProfileUpdateView(UpdateView):
    model = Company
    fields = ['name', 'number', 'industry', 'description']
    template_name = 'compani/edit_company_profile.html'
    success_url = reverse_lazy('company_profile')

    def get_object(self, queryset=None):
        return self.request.user.company

    def form_valid(self, form):
        response = super().form_valid(form)
        return response

def edit_company_profile(request):
    if not request.user.is_authenticated or request.user.user_type != 'company':
        return redirect('login_user')
    
    company = request.user.company
    if request.method == 'POST':
        form = CompanyProfileEditForm(request.POST, instance=request.user)
        if form.is_valid():
            user = form.save()
            company.name = form.cleaned_data['company_name']
            company.number = form.cleaned_data['company_number']
            company.industry = form.cleaned_data['industry']
            company.description = form.cleaned_data['description']
            company.save()
            messages.success(request, 'Профиль компании успешно обновлён.')
            return redirect('company_profile')
    else:
        form = CompanyProfileEditForm(instance=request.user, initial={
            'company_name': company.name,
            'company_number': company.number,
            'industry': company.industry,
            'description': company.description,
            'email': request.user.email,
            'phone': request.user.phone
        })

    context = {
        'form': form,
        'company': company
    }
    return render(request, 'compani/profile/edit_company_profile.html', context)

def verify_password_and_save(request):
    if not request.user.is_authenticated or request.user.user_type != 'company':
        return redirect('login_user')
    
    if request.method == 'POST':
        current_password = request.POST.get('current_password')
        user = authenticate(request, username=request.user.email, password=current_password)
        if user is not None:
            form_data = request.POST.copy()
            form_data.pop('current_password', None)  
            form = CompanyProfileEditForm(form_data, instance=request.user)
            if form.is_valid():
                user = form.save()
                company = request.user.company
                company.name = form.cleaned_data['company_name']
                company.number = form.cleaned_data['company_number']
                company.industry = form.cleaned_data['industry']
                company.description = form.cleaned_data['description']
                company.save()
                messages.success(request, 'Профиль компании успешно обновлён.')
                return redirect('company_profile')
            else:
                messages.error(request, f'Ошибка в данных формы: {form.errors.as_text()}')
        else:
            messages.error(request, 'Неверный текущий пароль.')
    
    company = request.user.company
    form = CompanyProfileEditForm(instance=request.user, initial={
        'company_name': company.name,
        'company_number': company.number,
        'industry': company.industry,
        'description': company.description,
        'email': request.user.email,
        'phone': request.user.phone
    })
    return render(request, 'compani/profile/edit_company_profile.html', {'form': form, 'company': company})

def change_password_request(request):
    if request.method == 'POST':
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            user = User.objects.filter(email=email).first()
            if user:
                token = default_token_generator.make_token(user)
                uid = urlsafe_base64_encode(force_bytes(user.pk))
                reset_link = request.build_absolute_uri(
                    reverse_lazy('change_password_confirm', kwargs={'uidb64': uid, 'token': token})
                )
                subject = 'Сброс пароля для HR-Lab'
                message = (
                    f'Здравствуйте,\n\n'
                    f'Для сброса пароля перейдите по ссылке: {reset_link}\n\n'
                    f'Если вы не запрашивали сброс пароля, проигнорируйте это письмо.\n\n'
                    f'С уважением,\nКоманда HR-Lab'
                )
                try:
                    print(f"Attempting to send email to {email} with host {settings.EMAIL_HOST}:{settings.EMAIL_PORT}")
                    connection = get_connection()
                    connection.open()
                    send_mail(
                        subject,
                        message,
                        settings.DEFAULT_FROM_EMAIL,
                        [email],
                        fail_silently=False,
                        connection=connection,
                    )
                    connection.close()
                    messages.success(request, 'Письмо с инструкциями по сбросу пароля отправлено на ваш email.')
                    return redirect('company_profile')
                except SMTPAuthenticationError as e:
                    messages.error(request, 'Ошибка аутентификации SMTP. Проверьте email или пароль приложения в настройках Яндекса.')
                except SMTPConnectError as e:
                    messages.error(request, 'Не удалось подключиться к SMTP-серверу Яндекса. Проверьте настройки хоста и порта.')
                except SMTPServerDisconnected as e:
                    messages.error(request, 'Соединение с SMTP-сервером прервано. Попробуйте снова.')
                except Exception as e:
                    messages.error(request, f'Неизвестная ошибка при отправке письма: {str(e)}')
            else:
                messages.error(request, 'Пользователь с таким email не найден.')
    else:
        form = PasswordResetRequestForm()

    return render(request, 'compani/profile/change_password_request.html', {'form': form})

def change_password_confirm(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        if request.method == 'POST':
            form = PasswordResetConfirmForm(request.POST)
            if form.is_valid():
                user.set_password(form.cleaned_data['new_password1'])
                user.save()
                update_session_auth_hash(request, user)  
                messages.success(request, 'Пароль успешно изменён. Вы можете войти с новым паролем.')
                return redirect('company_profile')
        else:
            form = PasswordResetConfirmForm()
        return render(request, 'compani/profile/change_password_confirm.html', {'form': form, 'validlink': True})
    else:
        messages.error(request, 'Ссылка для сброса пароля недействительна или истекла.')
        return render(request, 'compani/profile/change_password_confirm.html', {'form': None, 'validlink': False})
    
@login_required
def hr_agents_list(request):
    if request.user.user_type != 'company':
        messages.error(request, 'У вас нет доступа к управлению HR-агентами.')
        return redirect('home_comp')

    try:
        company = Company.objects.get(user=request.user)
    except Company.DoesNotExist:
        messages.error(request, 'У вас нет компании для управления HR-агентами.')
        return redirect('home_comp')

    hr_agents = Employee.objects.filter(
        company=company,
        user__user_type='hragent',
    )

    if request.method == 'POST' and 'delete' in request.POST:
        employee_id = request.POST.get('employee_id')
        employee = get_object_or_404(Employee, id=employee_id, company=company)
        user = employee.user
        employee.delete()
        user.delete()
        messages.success(request, 'HR-агент успешно удалён.')
        return redirect('hr_agents_list')

    return render(request, 'compani/hrCRUD/hr_agents_list.html', {'hr_agents': hr_agents, 'company': company})


@login_required
def hr_agent_edit(request, employee_id):
    if request.user.user_type != 'company':
        messages.error(request, 'У вас нет доступа к редактированию HR-агентов.')
        return redirect('home_comp')

    try:
        company = Company.objects.get(user=request.user)
    except Company.DoesNotExist:
        messages.error(request, 'У вас нет компании для управления HR-агентами.')
        return redirect('home_comp')

    employee = get_object_or_404(Employee, id=employee_id, company=company)
    user = employee.user

    if request.method == 'POST':
        form = HRAgentEditForm(request.POST, instance=employee)
        if form.is_valid():
            form.save()
            user.email = form.cleaned_data['email']
            user.phone = form.cleaned_data['phone']
            user.save()
            messages.success(request, 'Данные HR-агента успешно обновлены.')
            return redirect('hr_agents_list')
        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме.')
    else:
        initial_data = {
            'first_name': employee.first_name,
            'last_name': employee.last_name,
            'email': user.email,
            'phone': user.phone,
        }
        form = HRAgentEditForm(initial=initial_data)

    return render(request, 'compani/hrCRUD/hr_agent_form.html', {'form': form, 'title': 'Редактировать HR-агента', 'employee': employee})

@login_required
def create_vacancy(request):
    if request.user.user_type not in ['company', 'hragent']:
        messages.error(request, 'Только компании и HR-агенты могут создавать вакансии.')
        return redirect('home_page')
    
    if request.user.user_type == 'hragent':
        try:
            employee = Employee.objects.get(user=request.user)
            company = employee.company
        except Employee.DoesNotExist:
            messages.error(request, 'HR-агент не привязан к компании.')
            return redirect('home_comp')
    
    if request.method == 'POST':
        form = VacancyForm(request.POST)
        if form.is_valid():
            vacancy = form.save(commit=False)
            if request.user.user_type == 'company':
                vacancy.company = request.user.company
            else:  # hragent
                vacancy.company = employee.company
            vacancy.status = StatusVacancies.objects.get(status_vacancies_name='Активна')
            vacancy.save()
            messages.success(request, 'Вакансия успешно создана!')
            return redirect('vacancy_list')
    else:
        form = VacancyForm()
    
    context = {
        'form': form,
    }
    return render(request, 'compani/vacancy/create_vacancy.html', context)

@login_required
def edit_vacancy(request, vacancy_id):
    if request.user.user_type == 'company':
        vacancy = get_object_or_404(Vacancy, id=vacancy_id, company=request.user.company)
    elif request.user.user_type == 'hragent':
        employee = get_object_or_404(Employee, user=request.user)
        vacancy = get_object_or_404(Vacancy, id=vacancy_id, company=employee.company)
    else:
        messages.error(request, 'У вас нет прав для редактирования вакансий.')
        return redirect('home_page')
    
    if request.method == 'POST':
        form = VacancyForm(request.POST, instance=vacancy)
        if form.is_valid():
            vacancy = form.save(commit=False)
            # Сохраняем компанию (для HR-агента уже проверено через get_object_or_404)
            if request.user.user_type == 'company':
                vacancy.company = request.user.company
            else:
                vacancy.company = employee.company
            vacancy.save()
            messages.success(request, 'Вакансия успешно обновлена!')
            return redirect('vacancy_list')
    else:
        form = VacancyForm(instance=vacancy)
    
    context = {
        'form': form,
    }
    return render(request, 'compani/vacancy/edit_vacancy.html', context)

@login_required
def archive_vacancy(request, vacancy_id):
    if request.user.user_type == 'company':
        vacancy = get_object_or_404(Vacancy, id=vacancy_id, company=request.user.company)
    elif request.user.user_type == 'hragent':
        employee = get_object_or_404(Employee, user=request.user)
        vacancy = get_object_or_404(Vacancy, id=vacancy_id, company=employee.company)
    else:
        messages.error(request, 'У вас нет прав для архивирования вакансий.')
        return redirect('home_page')
    
    try:
        archived_status = StatusVacancies.objects.get(status_vacancies_name='Архивирована')
        vacancy.status = archived_status
        vacancy.save()
        messages.success(request, 'Вакансия успешно архивирована!')
    except StatusVacancies.DoesNotExist:
        messages.error(request, 'Статус "Архивирована" не найден. Обратитесь к администратору.')
    
    return redirect('vacancy_list')

@login_required
def unarchive_vacancy(request, vacancy_id):
    if request.user.user_type == 'company':
        vacancy = get_object_or_404(Vacancy, id=vacancy_id, company=request.user.company)
    elif request.user.user_type == 'hragent':
        employee = get_object_or_404(Employee, user=request.user)
        vacancy = get_object_or_404(Vacancy, id=vacancy_id, company=employee.company)
    else:
        messages.error(request, 'У вас нет прав для разархивирования вакансий.')
        return redirect('home_page')
    
    try:
        active_status = StatusVacancies.objects.get(status_vacancies_name='Активна')
        vacancy.status = active_status
        vacancy.save()
        messages.success(request, 'Вакансия успешно разархивирована!')
    except StatusVacancies.DoesNotExist:
        messages.error(request, 'Статус "Активна" не найден. Обратитесь к администратору.')
    
    return redirect('vacancy_list')

@login_required
def vacancy_list(request):
    if request.user.user_type == 'company':
        vacancies = Vacancy.objects.filter(company=request.user.company)
    elif request.user.user_type == 'hragent':
        employee = get_object_or_404(Employee, user=request.user)
        vacancies = Vacancy.objects.filter(company=employee.company)
    else:
        vacancies = Vacancy.objects.none()
    
    context = {
        'vacancies': vacancies,
    }
    return render(request, 'compani/vacancy/vacancy_list.html', context)

@login_required
def responses_list(request):
    if request.user.user_type not in ['company', 'hragent']:
        messages.error(request, 'У вас нет доступа к просмотру откликов.')
        return redirect('home_comp')

    try:
        if request.user.user_type == 'company':
            company = Company.objects.get(user=request.user)
        elif request.user.user_type == 'hragent':
            employee = Employee.objects.get(user=request.user)
            company = employee.company
    except (Company.DoesNotExist, Employee.DoesNotExist):
        messages.error(request, 'У вас нет компании для просмотра откликов.')
        return redirect('home_comp')

    # Получаем все отклики на вакансии компании
    responses = Response.objects.filter(vacancy__company=company).select_related(
        'applicants', 'vacancy', 'status'
    ).order_by('-response_date')

    # Статистика по статусам
    counts = {
        'total': responses.count(),
        'new': responses.filter(status__status_response_name='Новый').count(),
        'viewed': responses.filter(status__status_response_name='Просмотрен').count(),
        'invited': responses.filter(status__status_response_name='Приглашен').count(),
        'rejected': responses.filter(status__status_response_name='Отклонен').count(),
    }

    # Фильтрация по статусу
    status_filter = request.GET.get('status', 'all')
    current_status = status_filter

    if status_filter != 'all':
        status_mapping = {
            'new': 'Новый',
            'viewed': 'Просмотрен', 
            'invited': 'Приглашен',
            'rejected': 'Отклонен'
        }
        if status_filter in status_mapping:
            responses = responses.filter(status__status_response_name=status_mapping[status_filter])

    # Обработка AJAX запросов для обновления статуса
    if request.method == 'POST':
        response_id = request.POST.get('response_id')
        response = get_object_or_404(Response, id=response_id, vacancy__company=company)
        
        # Сохраняем старый статус перед обновлением
        old_status_name = response.status.status_response_name
        
        form = ResponseStatusUpdateForm(request.POST, instance=response)
        if form.is_valid():
            form.save()
            
            # Получаем новый статус после сохранения
            response.refresh_from_db()
            new_status_name = response.status.status_response_name
            
            # Отправляем письмо только если статус действительно изменился
            email_sent = False
            if old_status_name != new_status_name:
                email_sent = send_response_status_email(response, old_status_name, new_status_name)
            
            # Для AJAX запросов
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                # Обновляем статистику
                updated_counts = {
                    'total': Response.objects.filter(vacancy__company=company).count(),
                    'new': Response.objects.filter(vacancy__company=company, status__status_response_name='Новый').count(),
                    'viewed': Response.objects.filter(vacancy__company=company, status__status_response_name='Просмотрен').count(),
                    'invited': Response.objects.filter(vacancy__company=company, status__status_response_name='Приглашен').count(),
                    'rejected': Response.objects.filter(vacancy__company=company, status__status_response_name='Отклонен').count(),
                }
                
                if email_sent:
                    return JsonResponse({
                        'status': 'success', 
                        'message': 'Статус обновлен. Уведомление отправлено.',
                        'counts': updated_counts
                    })
                else:
                    if old_status_name != new_status_name:
                        return JsonResponse({
                            'status': 'warning', 
                            'message': 'Статус обновлен, но не удалось отправить уведомление.',
                            'counts': updated_counts
                        })
                    else:
                        return JsonResponse({
                            'status': 'success', 
                            'message': 'Статус обновлен.',
                            'counts': updated_counts
                        })
            
            # Для обычных POST запросов
            if email_sent:
                messages.success(request, f'Статус отклика успешно обновлён. Уведомление отправлено соискателю.')
            else:
                if old_status_name != new_status_name:
                    messages.warning(request, f'Статус отклика обновлён, но не удалось отправить уведомление соискателю.')
                else:
                    messages.success(request, 'Статус отклика успешно обновлён.')
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'status': 'error', 'message': 'Ошибка при обновлении статуса.'})
            messages.error(request, 'Ошибка при обновлении статуса.')
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'success'})
        return redirect('responses_list')

    # Подготавливаем данные для шаблона
    response_data = []
    for response in responses:
        form = ResponseStatusUpdateForm(instance=response)
        response_data.append({
            'response': response,
            'form': form
        })

    context = {
        'company': company,
        'response_data': response_data,
        'counts': counts,
        'current_status': current_status,
    }
    return render(request, 'compani/responses_list.html', context)

def send_response_status_email(response, old_status_name, new_status_name):
    """
    Отправляет письмо соискателю при изменении статуса отклика
    """
    applicant = response.applicants
    user_email = applicant.user.email
    first_name = applicant.first_name
    last_name = applicant.last_name
    vacancy_name = response.vacancy.position
    company_name = response.vacancy.company.name
    
    # Определяем стиль и контент в зависимости от статуса
    status_config = {
        'новый': {
            'title': 'Ваш отклик получен!',
            'description': 'Ваш отклик на вакансию успешно получен и находится на рассмотрении.',
            'icon': '📨',
            'color': '#2563eb'
        },
        'рассматривается': {
            'title': 'Отклик рассматривается',
            'description': 'Ваш отклик находится на активном рассмотрении рекрутером.',
            'icon': '👀',
            'color': '#f59e0b'
        },
        'приглашение': {
            'title': 'Приглашение на собеседование!',
            'description': 'Поздравляем! Вас приглашают на собеседование.',
            'icon': '🎉',
            'color': '#10b981'
        },
        'отказ': {
            'title': 'Решение по вашему отклику',
            'description': 'К сожалению, по результатам рассмотрения вашего отклика было принято отрицательное решение.',
            'icon': '💼',
            'color': '#ef4444'
        },
        'архив': {
            'title': 'Отклик перемещен в архив',
            'description': 'Ваш отклик был перемещен в архив.',
            'icon': '📁',
            'color': '#64748b'
        }
    }
    
    # Получаем настройки для текущего статуса или используем значения по умолчанию
    status_info = status_config.get(new_status_name.lower(), {
        'title': f'Статус отклика изменен на: {new_status_name}',
        'description': f'Статус вашего отклика был изменен на "{new_status_name}".',
        'icon': '📋',
        'color': '#2563eb'
    })
    
    try:
        subject = f'Обновление статуса отклика на вакансию "{vacancy_name}"'
        
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
                .invitation {{
                    background: rgba(16, 185, 129, 0.05);
                    border-color: rgba(16, 185, 129, 0.2);
                }}
                .invitation .status-title {{
                    color: #065f46;
                }}
                .rejection {{
                    background: rgba(239, 68, 68, 0.05);
                    border-color: rgba(239, 68, 68, 0.2);
                }}
                .rejection .status-title {{
                    color: #991b1b;
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
                    padding: 12px 0;
                    border-bottom: 1px solid #e2e8f0;
                }}
                .info-item:last-child {{
                    border-bottom: none;
                }}
                .info-label {{
                    color: #64748b;
                    font-weight: 500;
                    min-width: 120px;
                }}
                .info-value {{
                    color: #1e293b;
                    font-weight: 600;
                    text-align: right;
                    flex: 1;
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
                .next-steps {{
                    background: rgba(245, 158, 11, 0.1);
                    border: 1px solid rgba(245, 158, 11, 0.3);
                    border-radius: 10px;
                    padding: 20px;
                    margin: 25px 0;
                }}
                .next-steps-title {{
                    color: #92400e;
                    font-weight: 600;
                    margin-bottom: 10px;
                    text-align: center;
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
                    <p>Уведомление о статусе отклика</p>
                </div>
                
                <div class="content">
                    <h2 style="color: #1e293b; margin-top: 0;">Здравствуйте, {first_name} {last_name}!</h2>
                    <p style="color: #64748b; font-size: 16px;">
                        Статус вашего отклика на вакансию был обновлен.
                    </p>
                    
                    <div class="status-card { 'invitation' if new_status_name.lower() == 'приглашение' else 'rejection' if new_status_name.lower() == 'отказ' else '' }">
                        <div class="status-icon">{status_info['icon']}</div>
                        <div class="status-title">{status_info['title']}</div>
                        <div class="status-description">{status_info['description']}</div>
                    </div>
                    
                    <div class="info-section">
                        <div class="info-item">
                            <span class="info-label">Вакансия:</span>
                            <span class="info-value">{vacancy_name}</span>
                        </div>
                        <div class="info-item">
                            <span class="info-label">Компания:</span>
                            <span class="info-value">{company_name}</span>
                        </div>
                        <div class="info-item">
                            <span class="info-label">Предыдущий статус:</span>
                            <span class="info-value">{old_status_name}</span>
                        </div>
                        <div class="info-item">
                            <span class="info-label">Новый статус:</span>
                            <span class="info-value" style="color: {status_info['color']}; font-weight: 700;">{new_status_name}</span>
                        </div>
                        <div class="info-item">
                            <span class="info-label">Дата обновления:</span>
                            <span class="info-value">{timezone.now().strftime('%d.%m.%Y')}</span>
                        </div>
                    </div>
                    
                    {"<div class='next-steps'><div class='next-steps-title'>💡 Что дальше?</div><p style='color: #92400e; margin: 0; text-align: center;'>Ожидайте связи от представителя компании для согласования деталей собеседования.</p></div>" if new_status_name.lower() == 'приглашение' else ""}
                    
                    {"<div class='next-steps'><div class='next-steps-title'>💡 Не отчаивайтесь!</div><p style='color: #92400e; margin: 0; text-align: center;'>Продолжайте поиск - на нашей платформе много интересных вакансий, которые ждут именно вас!</p></div>" if new_status_name.lower() == 'отказ' else ""}
                    
                    <div style="text-align: center;">
                        <a href="http://127.0.0.1:8000/vacancy/" class="action-button">
                            Смотреть другие вакансии
                        </a>
                    </div>
                    
                    <p style="color: #64748b; font-size: 15px; text-align: center;">
                        Если у вас возникли вопросы, вы можете обратиться в нашу службу поддержки.
                    </p>
                </div>
                
                <div class="footer">
                    <p><strong>С уважением, команда HR-Lab</strong></p>
                    <p>Мы помогаем найти работу мечты</p>
                    <div class="contact-info">
                        <p>Email: hr-labogency@mail.ru</p>
                        <p>Телефон: +7 (999) 123-45-67</p>
                    </div>
                    <p style="font-size: 12px; margin-top: 20px; color: #94a3b8;">
                        Это автоматическое сообщение, пожалуйста, не отвечайте на него.
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Текстовая версия
        plain_message = f"""
        Здравствуйте, {first_name} {last_name}!

        Статус вашего отклика на вакансию был обновлен.

        Вакансия: {vacancy_name}
        Компания: {company_name}
        Предыдущий статус: {old_status_name}
        Новый статус: {new_status_name}

        {status_info['description']}

        {"💡 Что дальше? Ожидайте связи от представителя компании для согласования деталей собеседования." if new_status_name.lower() == 'приглашение' else ""}
        {"💡 Не отчаивайтесь! Продолжайте поиск - на нашей платформе много интересных вакансий." if new_status_name.lower() == 'отказ' else ""}

        Посмотреть другие вакансии:
        http://127.0.0.1:8000/vacancy/

        С уважением,
        Команда HR-Lab

        ---
        Email: hr-labogency@mail.ru
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
        print(f"❌ [EMAIL] ОШИБКА отправки уведомления о статусе отклика: {str(e)}")
        return False

@login_required
def hr_agent_create(request):
    if request.user.user_type != 'company':
        messages.error(request, 'У вас нет доступа к созданию HR-агентов.')
        return redirect('home_comp')

    try:
        company = Company.objects.get(user=request.user)
    except Company.DoesNotExist:
        messages.error(request, 'У вас нет компании для управления HR-агентами.')
        return redirect('home_comp')

    if request.method == 'POST':
        form = HRAgentCreateForm(request.POST)
        if form.is_valid():
            user = form.save(company=company)
            
            hr_agent = Employee.objects.get(user=user, company=company)
            
            password = form.cleaned_data['password1']
            
            email_sent = send_hr_agent_credentials(hr_agent, password, company.name)
            
            if email_sent:
                messages.success(request, 'HR-агент успешно создан. Письмо с учетными данными отправлено.')
            else:
                messages.warning(request, 'HR-агент создан, но не удалось отправить письмо с учетными данными.')
            
            return redirect('hr_agents_list')
        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме.')
    else:
        form = HRAgentCreateForm()

    return render(request, 'compani/hrCRUD/hr_agent_form.html', {'form': form, 'title': 'Создать HR-агента'})

def send_hr_agent_credentials(hr_agent, password, company_name):
    user_email = hr_agent.user.email
    first_name = hr_agent.first_name
    last_name = hr_agent.last_name
    
    try:
        subject = f'Добро пожаловать в HR-Lab! Ваши учетные данные'
        
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
                .welcome-section {{
                    text-align: center;
                    margin-bottom: 30px;
                }}
                .welcome-icon {{
                    font-size: 48px;
                    margin-bottom: 15px;
                }}
                .credentials-card {{
                    background: rgba(37, 99, 235, 0.05);
                    border: 1px solid rgba(37, 99, 235, 0.2);
                    border-radius: 15px;
                    padding: 25px;
                    margin: 25px 0;
                }}
                .credentials-title {{
                    font-size: 20px;
                    font-weight: 700;
                    color: #1e293b;
                    margin-bottom: 20px;
                    text-align: center;
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
                    padding: 12px 0;
                    border-bottom: 1px solid #e2e8f0;
                }}
                .info-item:last-child {{
                    border-bottom: none;
                }}
                .info-label {{
                    color: #64748b;
                    font-weight: 500;
                    min-width: 120px;
                }}
                .info-value {{
                    color: #1e293b;
                    font-weight: 600;
                    text-align: right;
                    flex: 1;
                }}
                .password-warning {{
                    background: rgba(245, 158, 11, 0.1);
                    border: 1px solid rgba(245, 158, 11, 0.3);
                    border-radius: 10px;
                    padding: 15px;
                    margin: 20px 0;
                    text-align: center;
                }}
                .warning-icon {{
                    color: #f59e0b;
                    font-size: 20px;
                    margin-bottom: 8px;
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
                .security-note {{
                    background: rgba(16, 185, 129, 0.1);
                    border: 1px solid rgba(16, 185, 129, 0.3);
                    border-radius: 10px;
                    padding: 15px;
                    margin: 20px 0;
                    text-align: center;
                    font-size: 14px;
                    color: #065f46;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>HR-Lab</h1>
                    <p>Добро пожаловать в команду!</p>
                </div>
                
                <div class="content">
                    <div class="welcome-section">
                        <div class="welcome-icon">👋</div>
                        <h2 style="color: #1e293b; margin-top: 0;">Здравствуйте, {first_name} {last_name}!</h2>
                        <p style="color: #64748b; font-size: 16px;">
                            Вас добавили в качестве HR-агента компании <strong>"{company_name}"</strong> на платформе HR-Lab.
                        </p>
                    </div>
                    
                    <div class="credentials-card">
                        <div class="credentials-title">Ваши учетные данные для входа</div>
                        
                        <div class="info-section">
                            <div class="info-item">
                                <span class="info-label">Логин (Email):</span>
                                <span class="info-value">{user_email}</span>
                            </div>
                            <div class="info-item">
                                <span class="info-label">Пароль:</span>
                                <span class="info-value" style="color: #2563eb; font-family: monospace;">{password}</span>
                            </div>
                            <div class="info-item">
                                <span class="info-label">Компания:</span>
                                <span class="info-value">{company_name}</span>
                            </div>
                            <div class="info-item">
                                <span class="info-label">Роль:</span>
                                <span class="info-value">HR-агент</span>
                            </div>
                        </div>
                        
                        <div class="password-warning">
                            <div class="warning-icon">⚠️</div>
                            <p style="color: #92400e; margin: 0; font-weight: 500;">
                                Сохраните эти данные в надежном месте!
                            </p>
                        </div>
                    </div>
                    
                    <div class="security-note">
                        <p style="margin: 0;">💡 <strong>Рекомендация по безопасности:</strong> После первого входа смените пароль в личном кабинете.</p>
                    </div>
                    
                    <div style="text-align: center;">
                        <a href="http://127.0.0.1:8000/accounts/login/" class="action-button">
                            Войти в систему
                        </a>
                    </div>
                    
                    <p style="color: #64748b; font-size: 15px; text-align: center;">
                        Если у вас возникли вопросы, обратитесь к администратору вашей компании или в нашу службу поддержки.
                    </p>
                </div>
                
                <div class="footer">
                    <p><strong>С уважением, команда HR-Lab</strong></p>
                    <p>Мы помогаем компаниям находить лучших сотрудников</p>
                    <div class="contact-info">
                        <p>Email: hr-labogency@mail.ru</p>
                        <p>Телефон: +7 (999) 123-45-67</p>
                    </div>
                    <p style="font-size: 12px; margin-top: 20px; color: #94a3b8;">
                        Это автоматическое сообщение, пожалуйста, не отвечайте на него.
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Текстовая версия
        plain_message = f"""
        Здравствуйте, {first_name} {last_name}!

        Вас добавили в качестве HR-агента компании "{company_name}" на платформе HR-Lab.

        Ваши учетные данные для входа:

        Логин (Email): {user_email}
        Пароль: {password}
        Компания: {company_name}
        Роль: HR-агент

        Войдите в систему по ссылке:
        http://127.0.0.1:8000/accounts/login/

        🔐 Рекомендация по безопасности: После первого входа смените пароль в личном кабинете.

        С уважением,
        Команда HR-Lab

        ---
        Email: hr-labogency@mail.ru
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
        print(f"❌ [EMAIL] ОШИБКА отправки данных HR-агенту: {str(e)}")
        return False
    
# views.py
@login_required
def employee_profile(request):
    if request.user.user_type != 'hragent':
        messages.error(request, 'У вас нет доступа к этой странице.')
        return redirect('home_comp')
    
    try:
        employee = Employee.objects.get(user=request.user)
    except Employee.DoesNotExist:
        messages.error(request, 'Профиль сотрудника не найден.')
        return redirect('home_comp')
    
    context = {
        'employee': employee,
        'user': request.user,
    }
    return render(request, 'compani/employee_profile.html', context)

@login_required
def edit_employee_profile(request):
    if request.user.user_type != 'hragent':
        messages.error(request, 'У вас нет доступа к этой странице.')
        return redirect('home_comp')
    
    try:
        employee = Employee.objects.get(user=request.user)
    except Employee.DoesNotExist:
        messages.error(request, 'Профиль сотрудника не найден.')
        return redirect('home_comp')
    
    if request.method == 'POST':
        form = EmployeeProfileForm(request.POST, instance=employee, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Профиль успешно обновлен!')
            return redirect('employee_profile')
        else:
            # Отладочная информация
            print("FORM ERRORS:", form.errors)
            print("FORM NON FIELD ERRORS:", form.non_field_errors())
            for field in form:
                if field.errors:
                    print(f"FIELD {field.name} ERRORS:", field.errors)
            
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме.')
    else:
        form = EmployeeProfileForm(instance=employee, user=request.user)
    
    context = {
        'employee': employee,
        'user': request.user,
        'form': form,
    }
    return render(request, 'compani/employee_edit_profile.html', context)