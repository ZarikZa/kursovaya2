from django.db import connection
from django.conf import settings
import subprocess
import os
from datetime import datetime
import zipfile

class ProcedureBackupManager:
    def __init__(self):
        self.db_settings = settings.DATABASES['default']
        self.backup_dir = os.path.join(settings.BASE_DIR, 'backups')
        os.makedirs(self.backup_dir, exist_ok=True)
    
    def call_postgres_function(self, function_name, *args):
        """Вызывает хранимую функцию PostgreSQL и возвращает результат"""
        with connection.cursor() as cursor:
            placeholders = ', '.join(['%s'] * len(args))
            sql = f"SELECT {function_name}({placeholders})"
            
            cursor.execute(sql, args)
            result = cursor.fetchone()[0]
            
        return result
    
    def create_database_backup(self):
        """Создает бэкап через хранимые процедуры в бинарном формате"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = os.path.join(self.backup_dir, f'backup_{timestamp}')
        os.makedirs(backup_path, exist_ok=True)
        
        try:
            # Пытаемся использовать хранимые процедуры
            result = self.call_postgres_function('create_full_binary_backup', backup_path + '/')
            
            # Создаем zip архив
            zip_filename = f'backup_binary_{timestamp}.zip'
            zip_path = os.path.join(self.backup_dir, zip_filename)
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file in os.listdir(backup_path):
                    if file.endswith('.dat'):
                        file_path = os.path.join(backup_path, file)
                        zipf.write(file_path, file)
            
            # Очищаем временные файлы
            import shutil
            shutil.rmtree(backup_path)
            
            file_size = os.path.getsize(zip_path)
            
            return {
                'filepath': zip_path,
                'filename': zip_filename,
                'file_size': file_size,
                'backup_type': 'database',
                'procedure_result': result,
                'format': 'binary'
            }
            
        except Exception as e:
            # Если процедуры не работают, используем pg_dump
            return self.create_backup_with_pg_dump(timestamp)
    
    def create_backup_with_pg_dump(self, timestamp):
        """Создает бэкап используя pg_dump"""
        filename = f'backup_pgdump_{timestamp}.backup'
        filepath = os.path.join(self.backup_dir, filename)
        
        try:
            cmd = [
                'pg_dump',
                '-h', self.db_settings['HOST'],
                '-p', self.db_settings.get('PORT', '5432'),
                '-U', self.db_settings['USER'],
                '-d', self.db_settings['NAME'],
                '-f', filepath,
                '-F', 'c',
                '-v'
            ]
            
            env = os.environ.copy()
            env['PGPASSWORD'] = self.db_settings['PASSWORD']
            
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise Exception(f"pg_dump failed: {result.stderr}")
            
            file_size = os.path.getsize(filepath)
            
            return {
                'filepath': filepath,
                'filename': filename,
                'file_size': file_size,
                'backup_type': 'database',
                'procedure_result': 'Used pg_dump',
                'format': 'pg_dump_binary'
            }
            
        except Exception as e:
            raise Exception(f"Backup failed: {str(e)}")
    
    def restore_database_backup(self, backup_file):
        """Восстанавливает базу данных"""
        import tempfile
        
        with tempfile.TemporaryDirectory() as temp_dir:
            if backup_file.name.endswith('.zip'):
                # Бинарные бэкапы из процедур
                zip_path = os.path.join(temp_dir, 'backup.zip')
                with open(zip_path, 'wb') as f:
                    for chunk in backup_file.chunks():
                        f.write(chunk)
                
                with zipfile.ZipFile(zip_path, 'r') as zipf:
                    zipf.extractall(temp_dir)
                
                for binary_file in os.listdir(temp_dir):
                    if binary_file.endswith('.dat'):
                        table_name = binary_file.split('_backup_')[0]
                        binary_path = os.path.join(temp_dir, binary_file)
                        
                        try:
                            result = self.call_postgres_function(
                                'restore_table_from_binary_backup', 
                                table_name, 
                                binary_path
                            )
                            print(f"Restored {table_name}: {result}")
                        except Exception as e:
                            print(f"Error restoring {table_name}: {e}")
            
            elif backup_file.name.endswith('.backup') or backup_file.name.endswith('.sql'):
                # Бэкапы pg_dump
                self.restore_from_pg_dump(backup_file)
    
    def restore_from_pg_dump(self, backup_file):
        """Восстановление из pg_dump файла"""
        temp_path = os.path.join(self.backup_dir, 'temp_restore.backup')
        
        with open(temp_path, 'wb') as f:
            for chunk in backup_file.chunks():
                f.write(chunk)
        
        try:
            cmd = [
                'pg_restore',
                '-h', self.db_settings['HOST'],
                '-p', self.db_settings.get('PORT', '5432'),
                '-U', self.db_settings['USER'],
                '-d', self.db_settings['NAME'],
                '-c',
                '-v',
                temp_path
            ]
            
            env = os.environ.copy()
            env['PGPASSWORD'] = self.db_settings['PASSWORD']
            
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise Exception(f"pg_restore failed: {result.stderr}")
                
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    def get_database_stats(self):
        """Получает статистику базы данных"""
        try:
            with connection.cursor() as cursor:
                cursor.callproc('get_database_stats')
                results = cursor.fetchall()
            
            stats = []
            for table_name, row_count, table_size, index_size, total_size in results:
                stats.append({
                    'table_name': table_name,
                    'row_count': row_count,
                    'table_size': table_size,
                    'index_size': index_size,
                    'total_size': total_size
                })
            
            return stats
            
        except Exception as e:
            return [{'error': f'Could not get stats: {str(e)}'}]
    
    def test_procedures(self):
        """Тестирует доступность хранимых процедур"""
        tests = []
        
        try:
            stats = self.get_database_stats()
            tests.append({
                'procedure': 'get_database_stats',
                'status': 'OK' if stats and not stats[0].get('error') else 'FAILED',
                'result': f'Found {len(stats)} tables'
            })
        except Exception as e:
            tests.append({
                'procedure': 'get_database_stats',
                'status': 'FAILED',
                'result': str(e)
            })
        
        return tests