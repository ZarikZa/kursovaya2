from django import forms
from home.models import *
from home.forms import BaseUserCreationForm
from django.core.validators import FileExtensionValidator


class CompanySignUpForm(BaseUserCreationForm):
    company_name = forms.CharField(
        max_length=100, 
        required=True, 
        label="Название компании",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Название вашей компании',
            'autocomplete': 'organization'
        })
    )
    company_number = forms.CharField(
        max_length=10, 
        required=True, 
        label="ИНН",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '1234567890',
            'autocomplete': 'off'
        })
    )
    industry = forms.CharField(
        max_length=100, 
        required=True, 
        label="Сфера деятельности",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Например, IT, строительство',
            'autocomplete': 'off'
        })
    )
    description = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': 'Опишите вашу компанию',
            'rows': 4
        }), 
        label="Описание компании"
    )
    theme = forms.CharField(
        max_length=100, 
        required=False, 
        label="Тема", 
        help_text="Опционально",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Тема оформления',
            'autocomplete': 'off'
        })
    )
    email = forms.EmailField(
        required=True, 
        label="Email",
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'example@company.com',
            'autocomplete': 'email'
        })
    )
    phone = forms.CharField(
        max_length=80, 
        required=True, 
        label="Телефон",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+7 (999) 999-99-99',
            'autocomplete': 'tel'
        })
    )
    verification_document = forms.FileField(
        required=True,
        label="Подтверждающий документ",
        help_text="Загрузите документ, подтверждающий регистрацию компании (PDF, до 5MB)",
        widget=forms.FileInput(attrs={
            'class': 'form-control file-input',
            'accept': '.pdf',
        }),
        validators=[FileExtensionValidator(['pdf'])]
    )
    
    password1 = forms.CharField(
        label="Пароль",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите пароль',
            'autocomplete': 'new-password'
        })
    )
    password2 = forms.CharField(
        label="Подтверждение пароля",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Повторите пароль',
            'autocomplete': 'new-password'
        })
    )

    class Meta:
        model = User
        fields = ('email', 'phone', 'company_name', 'company_number', 'industry', 'description', 'theme', 'verification_document')
    def save(self, commit=True):
        user = super().save(commit=False)
        user.user_type = 'company'
        user.phone = self.cleaned_data['phone']
        if commit:
            try:
                user.save()
                Company.objects.update_or_create(
                    user=user,
                    defaults={
                        'name': self.cleaned_data['company_name'],
                        'number': self.cleaned_data['company_number'],
                        'industry': self.cleaned_data['industry'],
                        'description': self.cleaned_data['description'],
                        'theme': self.cleaned_data.get('theme', ''),
                        'verification_document': self.cleaned_data['verification_document']
                    }
                )
            except Exception as e:
                if user.pk:
                    user.delete()
                raise e
        return user

class CompanyProfileEditForm(forms.ModelForm):
    company_name = forms.CharField(
        max_length=100, 
        required=True, 
        label="Название компании",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Название вашей компании',
            'autocomplete': 'organization'
        })
    )
    company_number = forms.CharField(
        max_length=10, 
        required=True, 
        label="ИНН",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '1234567890',
            'autocomplete': 'off'
        })
    )
    industry = forms.CharField(
        max_length=100, 
        required=True, 
        label="Сфера деятельности",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Например, IT, строительство',
            'autocomplete': 'off'
        })
    )
    description = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': 'Опишите вашу компанию',
            'rows': 4
        }), 
        label="Описание компании"
    )
    email = forms.EmailField(
        required=True, 
        label="Email",
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'example@company.com',
            'autocomplete': 'email'
        })
    )
    phone = forms.CharField(
        max_length=80, 
        required=True, 
        label="Телефон",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+7 (999) 999-99-99',
            'autocomplete': 'tel'
        })
    )

    class Meta:
        model = User
        fields = ('email', 'phone')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.phone = self.cleaned_data['phone']
        if commit:
            try:
                user.save()
                Company.objects.update_or_create(
                    user=user,
                    defaults={
                        'name': self.cleaned_data['company_name'],
                        'number': self.cleaned_data['company_number'],
                        'industry': self.cleaned_data['industry'],
                        'description': self.cleaned_data['description']
                    }
                )
            except Exception as e:
                raise e
        return user

class PasswordResetRequestForm(forms.Form):
    email = forms.EmailField(
        required=True,
        label="Email",
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите ваш email',
            'autocomplete': 'email'
        })
    )

class PasswordResetConfirmForm(forms.Form):
    new_password1 = forms.CharField(
        label="Новый пароль",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Не менее 8 символов',
            'autocomplete': 'new-password'
        })
    )
    new_password2 = forms.CharField(
        label="Подтверждение пароля",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Повторите пароль',
            'autocomplete': 'new-password'
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        new_password1 = cleaned_data.get("new_password1")
        new_password2 = cleaned_data.get("new_password2")
        if new_password1 and new_password2 and new_password1 != new_password2:
            raise forms.ValidationError("Пароли не совпадают")
        return cleaned_data
    
class HRAgentCreateForm(BaseUserCreationForm):
    first_name = forms.CharField(
        max_length=80,
        required=True,
        label="Имя",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ваше имя',
            'autocomplete': 'given-name'
        })
    )
    last_name = forms.CharField(
        max_length=80,
        required=True,
        label="Фамилия",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ваша фамилия',
            'autocomplete': 'family-name'
        })
    )
    email = forms.EmailField(
        required=True,
        label="Email",
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'example@email.com',
            'autocomplete': 'email'
        })
    )
    phone = forms.CharField(
        max_length=80,
        required=True,
        label="Телефон",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+7 (999) 999-99-99',
            'autocomplete': 'tel'
        })
    )

    class Meta:
        model = User
        fields = ('email', 'phone', 'password1', 'password2', 'first_name', 'last_name')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Не менее 8 символов',
            'autocomplete': 'new-password'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Повторите пароль',
            'autocomplete': 'new-password'
        })

    def save(self, commit=True, company=None):
        user = super().save(commit=False)
        user.username = user.email
        user.user_type = 'hragent'
        if commit:
            user.save()
            Employee.objects.create(
                user=user,
                first_name=self.cleaned_data['first_name'],
                last_name=self.cleaned_data['last_name'],
                company=company,
                access_level='hr'
            )
        return user

class HRAgentEditForm(forms.ModelForm):
    email = forms.EmailField(
        required=True,
        label="Email",
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'example@email.com',
            'autocomplete': 'email'
        })
    )
    phone = forms.CharField(
        max_length=80,
        required=True,
        label="Телефон",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+7 (999) 999-99-99',
            'autocomplete': 'tel'
        })
    )

    class Meta:
        model = Employee
        fields = ('first_name', 'last_name')
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ваше имя',
                'autocomplete': 'given-name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ваша фамилия',
                'autocomplete': 'family-name'
            }),
        }


class VacancyForm(forms.ModelForm):
    work_conditions = forms.ModelChoiceField(
        queryset=WorkConditions.objects.all(),
        label="Тип занятости",
        widget=forms.Select(attrs={
            'class': 'form-control',
            'placeholder': 'Выберите тип занятости',
        })
    )
    position = forms.CharField(
        max_length=100,
        required=True,
        label="Должность",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите должность',
            'autocomplete': 'off'
        })
    )
    description = forms.CharField(
        required=True,
        label="Описание",
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Введите описание вакансии'
        })
    )
    requirements = forms.CharField(
        required=True,
        label="Требования",
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Введите требования'
        })
    )
    salary_min = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=True,
        label="Минимальная зарплата, ₽",
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '0.00',
            'step': '0.01'
        })
    )
    salary_max = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=True,
        label="Максимальная зарплата, ₽",
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '0.00',
            'step': '0.01'
        })
    )
    experience = forms.ChoiceField(
        choices=[('', 'Не указан')] + list(Vacancy._meta.get_field('experience').choices),
        required=False,
        label="Опыт работы",
        widget=forms.Select(attrs={
            'class': 'form-control',
            'placeholder': 'Выберите опыт'
        })
    )
    city = forms.CharField(
        max_length=100,
        required=True,
        label="Город",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите город',
            'autocomplete': 'off'
        })
    )
    category = forms.ChoiceField(
        choices=[('', 'Не указана')] + list(Vacancy._meta.get_field('category').choices),
        required=False,
        label="Категория",
        widget=forms.Select(attrs={
            'class': 'form-control',
            'placeholder': 'Выберите категорию'
        })
    )
    work_conditions_details = forms.CharField(
        required=False,
        label="Детали условий",
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Введите детали условий (по одной строке)'
        })
    )
    status = forms.ModelChoiceField(
        queryset=StatusVacancies.objects.all(),
        label="Статус",
        widget=forms.Select(attrs={
            'class': 'form-control',
            'placeholder': 'Выберите статус'
        })
    )

    class Meta:
        model = Vacancy
        fields = ['work_conditions', 'position', 'description', 'requirements', 'salary_min', 'salary_max', 'experience', 'city', 'category', 'work_conditions_details', 'status']

class ResponseStatusUpdateForm(forms.ModelForm):
    status = forms.ModelChoiceField(
        queryset=StatusResponse.objects.all(),
        label="Статус отклика",
        widget=forms.Select(attrs={
            'class': 'form-control',
            'placeholder': 'Выберите статус'
        })
    )

    class Meta:
        model = Response
        fields = ['status']