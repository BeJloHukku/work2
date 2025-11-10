import requests
from typing import Any, Dict


class DependencyAnalyzer:
    NPM_API_URL = "https://registry.npmjs.org"
    
    def __init__(self, package_name: str, repository_url: str = None):
        self.package_name = package_name
        self.repository_url = repository_url or self.NPM_API_URL
    
    def get_dependencies(self) -> Dict[str, Any]:

        try:
            return self.get_npm_dependencies()

        except Exception as e:
            return {
                'success': False,
                'package': self.package_name,
                'error': f"Ошибка при получении зависимостей: {str(e)}"
            }
    
    def get_npm_dependencies(self) -> Dict[str, Any]:
        try:
            url = f"{self.repository_url}/{self.package_name}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            dist_tags = data.get('dist-tags', {})
            latest_version = dist_tags.get('latest', 'unknown')
            
            # Получить зависимости из последней версии
            versions = data.get('versions', {})
            dependencies = []
            
            if latest_version in versions:
                latest = versions[latest_version]
                deps = latest.get('dependencies', {})
                dependencies = list(deps.keys())
            
            return {
                'success': True,
                'package': self.package_name,
                'version': latest_version,
                'type': 'npm',
                'dependencies': dependencies,
                'count': len(dependencies)
            }
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return {
                    'success': False,
                    'package': self.package_name,
                    'error': f"Пакет '{self.package_name}' не найден в npm registry"
                }
            raise
        except requests.exceptions.Timeout:
            return {
                'success': False,
                'package': self.package_name,
                'error': "Превышено время ожидания при запросе к npm registry"
            }
    
    @staticmethod
    def show_dependencies(deps_info: Dict[str, Any]) -> str:
        if not deps_info.get('success'):
            return f"{deps_info.get('error', 'Неизвестная ошибка')}"
        
        output = []
        output.append(f"\nПакет: {deps_info['package']}")
        output.append(f"Версия: {deps_info['version']}")
        output.append(f"Тип: {deps_info['type'].upper()}")
        output.append(f"Прямые зависимости: {deps_info['count']}")
        
        if deps_info['dependencies']:
            output.append("\nЗависимости:")
            for i, dep in enumerate(sorted(deps_info['dependencies']), 1):
                output.append(f"   {i}. {dep}")
        else:
            output.append("\nЗависимостей не найдено")
        
        return "\n".join(output)
