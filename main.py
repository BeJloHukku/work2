import sys
import yaml
from pathlib import Path
from typing import Any
from dependency_analyzer import DependencyAnalyzer


class ConfigValidator:
    
    REQUIRED_FIELDS = [
        'package_name',
        'repository_url',
        'repository_mode',
        'output_file',
        'output_format',
        'max_depth'
    ]
    
    VALID_MODES = ['online', 'offline']
    VALID_FORMAT = ['ascii']
    
    @staticmethod
    def validate(config: dict[str, Any]) -> tuple[bool, list[str]]:
        errors = []
        
        for field in ConfigValidator.REQUIRED_FIELDS:
            if field not in config:
                errors.append(f"Отсутствует обязательное поле: {field}")
        
        if errors:
            return False, errors
        
        # Проверка имени пакета
        if not config['package_name'] or not isinstance(config['package_name'], str):
            errors.append("Имя пакета должно быть непустой строкой")
        
        # Проверка URL репозитория
        if not config['repository_url'] or not isinstance(config['repository_url'], str):
            errors.append("URL репозитория должен быть непустой строкой")
        
        # Проверка режима работы
        if config['repository_mode'] not in ConfigValidator.VALID_MODES:
            errors.append(
                f"Неверный режим работы: {config['repository_mode']}. "
                f"Допустимые значения: {', '.join(ConfigValidator.VALID_MODES)}"
            )
        
        # Проверка имени выходного файла
        if not config['output_file'] or not isinstance(config['output_file'], str):
            errors.append("Имя выходного файла должно быть непустой строкой")
        
        # Проверка формата вывода
        if config['output_format'] not in ConfigValidator.VALID_FORMAT:
            errors.append(
                f"Неверный формат вывода: {config['output_format']}. "
                f"Допустимые значения: {', '.join(ConfigValidator.VALID_FORMAT)}"
            )
        
        # Проверка максимальной глубины
        try:
            depth = int(config['max_depth'])
            if depth < 1:
                errors.append("Максимальная глубина должна быть положительным числом")
        except (ValueError, TypeError):
            errors.append("Максимальная глубина должна быть целым числом")
        
        return len(errors) == 0, errors


class DependencyVisualizer:
    
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.config = None
    
    def load_config(self) -> bool:
        try:
            config_file = Path(self.config_path)
            
            if not config_file.exists():
                print(f"Ошибка: Файл конфигурации не найден: {self.config_path}")
                return False
            
            with open(config_file, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
            
            print(f"Конфигурация загружена из: {self.config_path}")
            return True
            
        except yaml.YAMLError as e:
            print(f"Ошибка парсинга YAML: {e}")
            return False
        except Exception as e:
            print(f"Ошибка при загрузке конфигурации: {e}")
            return False
    
    def validate_config(self) -> bool:
        if not self.config:
            print("Ошибка: Конфигурация не загружена")
            return False
        
        is_valid, errors = ConfigValidator.validate(self.config)
        
        if not is_valid:
            print("Ошибки в конфигурации:")
            for error in errors:
                print(f"  - {error}")
            return False
        
        print("Конфигурация валидна")
        return True
    
    def print_config(self):
        if not self.config:
            print("Конфигурация не загружена")
            return
        
        print("Параметры конфигурации:")
        
        print(f"Имя пакета              : {self.config['package_name']}")
        print(f"URL репозитория         : {self.config['repository_url']}")
        print(f"Режим работы            : {self.config['repository_mode']}")
        print(f"Выходной файл           : {self.config['output_file']}")
        print(f"Формат вывода           : {self.config['output_format']}")
        print(f"Максимальная глубина    : {self.config['max_depth']}")
        
    
    def run(self):
        # Загрузка конфигурации
        if not self.load_config():
            return 1
        
        # Валидация конфигурации
        if not self.validate_config():
            return 1
        
        self.print_config()
        
        if self.config['repository_mode'] == 'online':
            self.analyze_dependencies()
        
        return 0
    
    def analyze_dependencies(self):
        
        package_name = self.config['package_name']
        repository_url = self.config['repository_url']
        
        analyzer = DependencyAnalyzer(package_name, repository_url)
        deps_info = analyzer.get_dependencies()
        
        print(DependencyAnalyzer.show_dependencies(deps_info))


def main():
    if len(sys.argv) < 2:
        print("Использование: python main.py <путь_к_config.yaml>")
        print("Пример: python main.py config.yaml")
        return 1
    
    config_path = sys.argv[1]
    visualizer = DependencyVisualizer(config_path)
    return visualizer.run()


if __name__ == "__main__":
    sys.exit(main())
