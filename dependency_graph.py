from typing import Dict, List, Set, Any, Optional
import json


class DependencyGraph:
    
    def __init__(self, root_package: str):
        self.root_package = root_package
        self.graph: Dict[str, List[str]] = {}  # package -> [dependencies]
        self.visited: Set[str] = set()
        self.cycles: List[List[str]] = []  # Найденные циклы
        self.levels: Dict[str, int] = {}  # package -> depth level
    
    def add_dependency(self, package: str, dependency: str):
        if package not in self.graph:
            self.graph[package] = []
        if dependency not in self.graph[package]:
            self.graph[package].append(dependency)
    
    def get_dependencies(self, package: str) -> List[str]:
        return self.graph.get(package, [])
    
    def get_all_packages(self) -> Set[str]:
        packages = set(self.graph.keys())
        for deps in self.graph.values():
            packages.update(deps)
        return packages
    
    def get_statistics(self) -> Dict[str, Any]:
        all_packages = self.get_all_packages()
        return {
            'total_packages': len(all_packages),
            'total_edges': sum(len(deps) for deps in self.graph.values()),
            'max_depth': max(self.levels.values()) if self.levels else 0,
            'cycles_found': len(self.cycles),
            'packages_with_dependencies': len(self.graph)
        }


class DependencyGraphBuilder:
    
    def __init__(self, analyzer, max_depth: int = 3):
        self.analyzer = analyzer
        self.max_depth = max_depth
    
    def build_graph_recursive(self, root_package: str) -> DependencyGraph:
        graph = DependencyGraph(root_package)
        visited_at_depth: Dict[str, int] = {}
        
        def bfs_recursive(package: str, depth: int, path: List[str]):
            #Рекурсивный BFS обход
            if depth >= self.max_depth:
                return
            
            # Получаем зависимости
            analyzer = type(self.analyzer)(package, self.analyzer.repository_url)
            deps_info = analyzer.get_dependencies()
            
            if not deps_info.get('success'):
                return
            
            dependencies = deps_info.get('dependencies', [])
            
            # Обрабатываем каждую зависимость
            for dep in dependencies:
                graph.add_dependency(package, dep)
                
                # Проверка на цикл
                if dep in path:
                    cycle_path = path[path.index(dep):] + [dep]
                    if cycle_path not in graph.cycles:
                        graph.cycles.append(cycle_path)
                    continue
                
                # Проверяем, не посещен ли уже пакет на меньшей глубине
                if dep in visited_at_depth and visited_at_depth[dep] <= depth + 1:
                    continue
                
                visited_at_depth[dep] = depth + 1
                graph.levels[dep] = depth + 1
                
                # Рекурсивно обходим зависимости
                bfs_recursive(dep, depth + 1, path + [dep])
        
        # Начинаем с корневого пакета
        visited_at_depth[root_package] = 0
        graph.levels[root_package] = 0
        bfs_recursive(root_package, 0, [root_package])
        
        graph.visited = set(visited_at_depth.keys())
        return graph


class TestRepositoryLoader:
    
    def __init__(self, package_name: str, repository_path: str):
        self.package_name = package_name
        self.repository_url = repository_path
        self.repository_path = repository_path
        self.repository_data = self.load_repository()
    
    def load_repository(self) -> Dict[str, List[str]]:
        try:
            with open(self.repository_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data.get('packages', {})
        except FileNotFoundError:
            raise FileNotFoundError(f"Файл репозитория не найден: {self.repository_path}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Ошибка парсинга JSON: {e}")
    
    def get_dependencies(self) -> Dict[str, Any]:
        if self.package_name not in self.repository_data:
            return {
                'success': False,
                'package': self.package_name,
                'error': f"Пакет '{self.package_name}' не найден в тестовом репозитории"
            }
        
        dependencies = self.repository_data[self.package_name]
        
        return {
            'success': True,
            'package': self.package_name,
            'version': '1.0.0',
            'type': 'test',
            'dependencies': dependencies,
            'count': len(dependencies)
        }
    



def format_graph(graph: DependencyGraph) -> str:
    output = []
    
    output.append(f"\nГраф зависимостей: {graph.root_package}")
    
    stats = graph.get_statistics()
    output.append(f"\nВсего пакетов: {stats['total_packages']}")
    output.append(f"Всего связей: {stats['total_edges']}")
    output.append(f"Максимальная глубина: {stats['max_depth']}")
    output.append(f"Циклов найдено: {stats['cycles_found']}")
    
    if graph.cycles:
        output.append("\nОбнаружены циклические зависимости:")
        for i, cycle in enumerate(graph.cycles, 1):
            cycle_str = " -> ".join(cycle)
            output.append(f"   {i}. {cycle_str}")
    
    output.append("\nСтруктура графа:")
    output.append(format_tree(graph, graph.root_package, "", set()))
    
    return "\n".join(output)


def format_tree(graph: DependencyGraph, package: str, prefix: str, visited: Set[str]) -> str:
    output = []
    
    if package in visited:
        output.append(f"{prefix}├── {package} (уже посещен)")
        return "\n".join(output)
    
    visited.add(package)
    output.append(f"{prefix}├── {package}")
    
    dependencies = graph.get_dependencies(package)
    for i, dep in enumerate(dependencies):
        is_last = i == len(dependencies) - 1
        extension = "    " if is_last else "│   "
        output.append(format_tree(graph, dep, prefix + extension, visited.copy()))
    
    return "\n".join(output)
