from .models import *
from .forms import *
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.views.generic import CreateView
from django.db.models import Q
from django.core.paginator import Paginator
def home_page(request):
    return render(request, 'home.html')

@login_required
def applicant_profile(request):
    applicant = get_object_or_404(Applicant, user=request.user)
    
    favorites = Favorites.objects.filter(applicant=applicant).select_related('vacancy')
    
    responses = Response.objects.filter(applicants=applicant).select_related('vacancy', 'status')
    
    context = {
        'applicant': applicant,
        'favorites': favorites,
        'responses': responses,
    }
    return render(request, 'profile.html', context)
def custom_login(request):
    if request.user.is_authenticated:
        return redirect('home_page')
    
    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('username') 
            password = form.cleaned_data.get('password')
            user = authenticate(request, email=email, password=password)  
            
            print(f"DEBUG: User found: {user}")  # Отладочный принт
            print(f"DEBUG: User authenticated: {user is not None}")  # Отладочный принт
            
            if user is not None:
                if hasattr(user, 'company'):
                    company = user.company
                    print(f"DEBUG: Company status: {company.status}")  # Отладочный принт
                    
                    if company.status == Company.STATUS_PENDING:
                        print("DEBUG: Redirecting to pending page")  # Отладочный принт
                        return redirect('account_pending')
                    elif company.status == Company.STATUS_REJECTED:
                        print("DEBUG: Company rejected")  # Отладочный принт
                        return render(request, 'auth/login.html', {'form': form})
                    else:
                        print("DEBUG: Company approved, logging in")  # Отладочный принт
                
                # Логиним пользователя
                login(request, user)
                print("DEBUG: User logged in successfully")  # Отладочный принт
                
                # Редирект
                next_url = request.GET.get('next')
                if next_url and next_url.startswith('/'):
                    return redirect(next_url)
                else:
                    if hasattr(user, 'company'):
                        return redirect('home_comp')
                    else:
                        return redirect('home_page')
            else:
                print("DEBUG: Authentication failed")  # Отладочный принт
                form.add_error(None, '❌ Неверный email или пароль')
        else:
            print("DEBUG: Form invalid")  # Отладочный принт
            print(f"DEBUG: Form errors: {form.errors}")  # Отладочный принт
    else:
        form = CustomAuthenticationForm()
    
    return render(request, 'auth/login.html', {'form': form})


class ApplicantRegisterView(CreateView):
    model = User
    form_class = ApplicantSignUpForm
    template_name = 'auth/register.html'
    
    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        
        next_url = self.request.GET.get('next')
        
        if next_url and next_url.startswith('/'):
            return redirect(next_url)
        else:
            return redirect('home_page')  
    
    def form_invalid(self, form):
        return self.render_to_response(self.get_context_data(form=form))


class AnaliticRegisterView(CreateView):
    model = User
    form_class = AnaliticSignUpForm
    template_name = 'auth/register_analitic.html'
    
    def form_valid(self, form):
        user = form.save()
        login(self.request, user)

class HRAgentRegisterView(CreateView):
    model = User
    form_class = HRAgentSignUpForm
    template_name = 'auth/register_hr.html'
    
    def form_valid(self, form):
        user = form.save()
        login(self.request, user)

class AdminSiteRegisterView(CreateView):
    model = User
    form_class = AdminSiteSignUpForm
    template_name = 'auth/register_admin.html'
    
    def form_valid(self, form):
        user = form.save()
        login(self.request, user)

def custom_logout(request):
    logout(request)
    next_url = request.GET.get('next')
        
    if next_url and next_url.startswith('/'):
        return redirect(next_url)
    else:
        return redirect('home_page')  
    
def vakansii_page(request):
    vacancies = Vacancy.objects.select_related(
        'company', 
        'work_conditions', 
        'status'
    ).filter(status__status_vacancies_name='Активна')
    
    # Обработка фильтров
    search_query = request.GET.get('search', '')
    if search_query:
        vacancies = vacancies.filter(
            Q(position__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(company__name__icontains=search_query)
        )
    
    # Фильтр по типу занятости
    employment_filters = request.GET.getlist('employment')
    if employment_filters:
        vacancies = vacancies.filter(work_conditions__work_conditions_name__in=employment_filters)
    
    # Фильтр по опыту работы (предполагается поле experience)
    experience_filters = request.GET.getlist('experience')
    if experience_filters:
        vacancies = vacancies.filter(experience__in=experience_filters)  # Адаптируй под модель
    
    # Фильтр по зарплате
    salary_from = request.GET.get('salary_from')
    salary_to = request.GET.get('salary_to')
    if salary_from:
        vacancies = vacancies.filter(salary_min__gte=salary_from)
    if salary_to:
        vacancies = vacancies.filter(salary_max__lte=salary_to)
    
    # Сортировка
    sort_by = request.GET.get('sort', 'newest')
    if sort_by == 'salary_high':
        vacancies = vacancies.order_by('-salary_max')
    elif sort_by == 'salary_low':
        vacancies = vacancies.order_by('salary_min')
    else: 
        vacancies = vacancies.order_by('-created_date')
    
    paginator = Paginator(vacancies, 10)  # 10 вакансий на страницу
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Передача вариантов типов занятости и выбранных фильтров
    work_conditions = WorkConditions.objects.all()
    selected_employments = request.GET.getlist('employment')
    selected_experiences = request.GET.getlist('experience')
    
    if request.user.is_authenticated and request.user.user_type == 'applicant':
        try:
            applicant = Applicant.objects.get(user=request.user)
            for vacancy in page_obj.object_list:
                vacancy.has_response = vacancy.response_set.filter(applicants=applicant).exists()
        except Applicant.DoesNotExist:
            for vacancy in page_obj.object_list:
                vacancy.has_response = False
    else:
        for vacancy in page_obj.object_list:
            vacancy.has_response = False
    
    context = {
        'page_obj': page_obj,
        'work_conditions': work_conditions,
        'selected_employments': selected_employments,
        'selected_experiences': selected_experiences,
        'salary_from': request.GET.get('salary_from', ''),
        'salary_to': request.GET.get('salary_to', ''),
    }
    return render(request, 'vakans.html', context)

def vacancy_detail(request, vacancy_id):
    vacancy = get_object_or_404(Vacancy.objects.select_related('company', 'work_conditions', 'status'), id=vacancy_id)
    vacancy.views += 1
    vacancy.save(update_fields=['views'])
    
    is_favorite = False
    has_response = False
    
    if request.user.is_authenticated and request.user.user_type == 'applicant':
        try:
            applicant = Applicant.objects.get(user=request.user)
            is_favorite = vacancy.favorites_set.filter(applicant=applicant).exists()
            has_response = vacancy.response_set.filter(applicants=applicant).exists()
        except Applicant.DoesNotExist:
            pass 
    
    context = {
        'vacancy': vacancy,
        'is_favorite': is_favorite,
        'has_response': has_response,
    }
    return render(request, 'vacancy_detail.html', context)

def apply_to_vacancy(request, vacancy_id):
    if not request.user.is_authenticated or request.user.user_type != 'applicant':
        return redirect('vacancy_detail', vacancy_id=vacancy_id)
    
    vacancy = get_object_or_404(Vacancy, id=vacancy_id)
    
    try:
        applicant = Applicant.objects.get(user=request.user)
    except Applicant.DoesNotExist:
        return redirect('vacancy_detail', vacancy_id=vacancy_id)
    
    existing_response = Response.objects.filter(
        applicants=applicant, 
        vacancy=vacancy
    ).exists()
    
    if existing_response:
        return redirect('vacancy_detail', vacancy_id=vacancy_id)
    
    try:
        status_new, created = StatusResponse.objects.get_or_create(
            status_response_name='Новый',
            defaults={'status_response_name': 'Новый'}
        )
        
        Response.objects.create(
            applicants=applicant,
            vacancy=vacancy,
            status=status_new
        )
        
        
    except Exception as e:
        pass
    return redirect('vacancy_detail', vacancy_id=vacancy_id)

@login_required
def add_to_favorites(request, vacancy_id):
    if request.user.user_type != 'applicant':
        return redirect('vacancy_detail', vacancy_id=vacancy_id)
    
    try:
        applicant = Applicant.objects.get(user=request.user)
        vacancy = get_object_or_404(Vacancy, id=vacancy_id)
        
        favorite_exists = Favorites.objects.filter(
            applicant=applicant, 
            vacancy=vacancy
        ).exists()
        
        if favorite_exists:
            pass
        else:
            Favorites.objects.create(applicant=applicant, vacancy=vacancy)
            
    except Applicant.DoesNotExist:
        pass
    
    return redirect('vacancy_detail', vacancy_id=vacancy_id)

@login_required
def remove_from_favorites(request, vacancy_id):
    if request.user.user_type != 'applicant':
        return redirect('vacancy_detail', vacancy_id=vacancy_id)
    
    try:
        applicant = Applicant.objects.get(user=request.user)
        vacancy = get_object_or_404(Vacancy, id=vacancy_id)
        
        favorite = Favorites.objects.filter(
            applicant=applicant, 
            vacancy=vacancy
        ).first()
        
        if favorite:
            favorite.delete()
       
    except Applicant.DoesNotExist:
        pass
    
    return redirect('vacancy_detail', vacancy_id=vacancy_id)


@login_required
def edit_applicant_profile(request):
    if request.user.user_type != 'applicant':
        return redirect('home_page')
    
    applicant = get_object_or_404(Applicant, user=request.user)
    
    if request.method == 'POST':
        form = ApplicantEditForm(request.POST, instance=applicant)
        user_form = UserEditForm(request.POST, instance=request.user)
        
        if form.is_valid() and user_form.is_valid():
            form.save()
            user_form.save()
            return redirect('applicant_profile')
    else:
        form = ApplicantEditForm(instance=applicant)
        user_form = UserEditForm(instance=request.user)
    
    context = {
        'form': form,
        'user_form': user_form,
    }
    return render(request, 'edit_applicant_profile.html', context)

@login_required
def delete_applicant_profile(request):
    if request.user.user_type != 'applicant':
        return redirect('home_page')
    
    if request.method == 'POST':
        user = request.user
        user.delete()
        return redirect('home_page')
    
    return redirect('applicant_profile')