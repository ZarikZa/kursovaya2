import os
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import FileExtensionValidator

class User(AbstractUser):
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=80)
    
    USERNAME_FIELD = 'email' 
    REQUIRED_FIELDS = ['username', 'phone'] 
    
    USER_TYPE_CHOICES = (
        ('applicant', 'Соискатель'),
        ('company', 'Компания'),
        ('analitic', 'Аналитик'),
        ('hragent', 'HR агент'),
        ('adminsite', 'АдминСайта'),
    )
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES, default='applicant')
    
    class Meta:
        db_table = 'users'
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
    
    def __str__(self):
        return self.email
    
    def save(self, *args, **kwargs):
        if not self.username:
            self.username = self.email
        super().save(*args, **kwargs)
      
class Role(models.Model):
    role_name = models.CharField(max_length=100)
    
    class Meta:
        db_table = 'roles'
        verbose_name = 'Роль'
        verbose_name_plural = 'Роли'
    
    def __str__(self):
        return self.role_name
    

class Company(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'
    
    STATUS_CHOICES = [
        (STATUS_PENDING, 'На проверке'),
        (STATUS_APPROVED, 'Подтверждена'),
        (STATUS_REJECTED, 'Отклонена'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    number = models.CharField(max_length=10)
    industry = models.CharField(max_length=100)
    description = models.TextField()
    theme = models.CharField(max_length=100, blank=True, null=True)
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        verbose_name='Статус аккаунта'
    )
    verification_document = models.FileField(
        upload_to='company_documents/%Y/%m/%d/',
        verbose_name='Подтверждающий документ (PDF)',
        validators=[FileExtensionValidator(['pdf'])],
        help_text='Загрузите документ в формате PDF'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'companies'
        verbose_name = 'Компания'
        verbose_name_plural = 'Компании'
    
    def __str__(self):
        return self.name
    
    def is_approved(self):
        return self.status == self.STATUS_APPROVED

class Applicant(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=80)
    last_name = models.CharField(max_length=80)
    birth_date = models.DateField()
    resume = models.TextField(blank=True)
    theme = models.CharField(max_length=100, blank=True, null=True) 

    class Meta:
        db_table = 'applicants'
        verbose_name = 'Соискатель'
        verbose_name_plural = 'Соискатели'
    
    def __str__(self):
        return f"{self.first_name} {self.last_name}"
    
    def add_to_favorites(self, vacancy):
        favorite, created = Favorites.objects.get_or_create(
            applicant=self,
            vacancy=vacancy
        )
        return created
    
    def remove_from_favorites(self, vacancy):
        Favorites.objects.filter(applicant=self, vacancy=vacancy).delete()
    
    def get_favorites(self):
        return self.favorite_vacancies.all()
    
    def is_in_favorites(self, vacancy):
        return Favorites.objects.filter(applicant=self, vacancy=vacancy).exists()

class Employee(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=80)
    last_name = models.CharField(max_length=80)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True, blank=True)
    access_level = models.CharField(max_length=50, default='standard')
    theme = models.CharField(max_length=100, blank=True, null=True) 
    class Meta:
        db_table = 'employees'
        verbose_name = 'Сотрудник'
        verbose_name_plural = 'Сотрудники'
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.role})"

class WorkConditions(models.Model):
    work_conditions_name = models.CharField(max_length=50)
    
    class Meta:
        db_table = 'work_conditions'
        verbose_name = 'Условие работы'
        verbose_name_plural = 'Условия работы'
    
    def __str__(self):
        return self.work_conditions_name

class StatusVacancies(models.Model):
    status_vacancies_name = models.CharField(max_length=50)
    
    class Meta:
        db_table = 'status_vacancies'
        verbose_name = 'Статус вакансии'
        verbose_name_plural = 'Статусы вакансий'
    
    def __str__(self):
        return self.status_vacancies_name

class StatusResponse(models.Model):
    status_response_name = models.CharField(max_length=100)
    
    class Meta:
        db_table = 'status_responses'
        verbose_name = 'Статус отклика'
        verbose_name_plural = 'Статусы откликов'
    
    def __str__(self):
        return self.status_response_name
    
class Vacancy(models.Model):
    company = models.ForeignKey('Company', on_delete=models.CASCADE)  
    work_conditions = models.ForeignKey('WorkConditions', on_delete=models.CASCADE)
    position = models.CharField(max_length=100)
    description = models.TextField()
    requirements = models.TextField()
    salary_min = models.DecimalField(max_digits=12, decimal_places=2)
    salary_max = models.DecimalField(max_digits=12, decimal_places=2)
    created_date = models.DateTimeField(auto_now_add=True)
    status = models.ForeignKey('StatusVacancies', on_delete=models.CASCADE)
    views = models.PositiveIntegerField(default=0)
    experience = models.CharField(max_length=20, choices=[
        ('Без опыта', 'Без опыта'),
        ('1-3 года', '1-3 года'),
        ('3-6 лет', '3-6 лет'),
        ('от 6 лет', 'от 6 лет'),
    ], blank=True, null=True)
    city = models.CharField(max_length=100, default='Москва')  
    category = models.CharField(max_length=50, choices=[
        ('IT', 'IT'),
        ('Маркетинг', 'Маркетинг'),
        ('Продажи', 'Продажи'),
        ('HR', 'HR'),
    ], default='IT') 
    work_conditions_details = models.TextField(blank=True, null=True) 

    class Meta:
        db_table = 'vacancies'
        verbose_name = 'Вакансия'
        verbose_name_plural = 'Вакансии'
    
    def __str__(self):
        return f"{self.position} - {self.company.name}"

class Response(models.Model):
    applicants = models.ForeignKey(Applicant, on_delete=models.CASCADE)
    vacancy = models.ForeignKey(Vacancy, on_delete=models.CASCADE)
    response_date = models.DateTimeField(auto_now_add=True)
    status = models.ForeignKey(StatusResponse, on_delete=models.CASCADE)
    
    class Meta:
        db_table = 'responses'
        verbose_name = 'Отклик'
        verbose_name_plural = 'Отклики'
        unique_together = ['applicants', 'vacancy']
    
    def __str__(self):
        return f"Отклик {self.applicants} на {self.vacancy}"

class Favorites(models.Model):
    applicant = models.ForeignKey(Applicant, on_delete=models.CASCADE, verbose_name="Соискатель")
    vacancy = models.ForeignKey(Vacancy, on_delete=models.CASCADE, verbose_name="Вакансия")
    added_date = models.DateTimeField(auto_now_add=True, verbose_name="Дата добавления")
    
    class Meta:
        db_table = 'favorites'
        verbose_name = 'Избранное'
        verbose_name_plural = 'Избранные вакансии'
        unique_together = ['applicant', 'vacancy']
    
    def __str__(self):
        return f"{self.applicant} - {self.vacancy}"

class AdminLog(models.Model):
    ACTION_CHOICES = [
        ('company_approved', 'Компания одобрена'),
        ('company_rejected', 'Компания отклонена'),
        ('company_updated', 'Компания обновлена'),
        ('backup_created', 'Создан бэкап'),
        ('backup_restored', 'Бэкап восстановлен'),
        ('backup_deleted', 'Бэкап удален'),
        ('backup_downloaded', 'Бэкап скачан'),
        ('backup_uploaded', 'Бэкап загружен'),
        ('logs_cleared', 'Логи очищены'),
    ]
    
    admin = models.ForeignKey(User, on_delete=models.CASCADE)
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    target_company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True, blank=True)
    details = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Лог администратора'
        verbose_name_plural = 'Логи администраторов'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.admin.username} - {self.get_action_display()} - {self.created_at}"

class Backup(models.Model):
    BACKUP_TYPES = [
        ('full', 'Полный бэкап'),
        ('database', 'Только база данных'),
        ('media', 'Только медиафайлы'),
    ]
    
    name = models.CharField(max_length=255, verbose_name='Название бэкапа')
    backup_file = models.FileField(upload_to='backups/%Y/%m/%d/', verbose_name='Файл бэкапа')
    backup_type = models.CharField(max_length=20, choices=BACKUP_TYPES, default='database')
    file_size = models.BigIntegerField(default=0, verbose_name='Размер файла')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Создан')
    
    class Meta:
        verbose_name = 'Бэкап'
        verbose_name_plural = 'Бэкапы'
        ordering = ['-created_at']
    
    def delete(self, *args, **kwargs):
        if self.backup_file:
            if os.path.isfile(self.backup_file.path):
                os.remove(self.backup_file.path)
        super().delete(*args, **kwargs)
    
    def get_file_size_display(self):
        if self.file_size == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB"]
        i = 0
        size = self.file_size
        
        while size >= 1024 and i < len(size_names) - 1:
            size /= 1024.0
            i += 1
        
        return f"{size:.2f} {size_names[i]}"
    
    def __str__(self):
        return self.name