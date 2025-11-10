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


def calculate_load_order(graph: DependencyGraph) -> Dict[str, Any]:
    # Строим обратный граф: пакет -> кто от него зависит
    reverse_graph: Dict[str, List[str]] = {}
    in_degree: Dict[str, int] = {}
    
    all_packages = graph.get_all_packages()
    
    for package in all_packages:
        reverse_graph[package] = []
        in_degree[package] = 0
    
    # Подсчет входящих рёбер
    for package, dependencies in graph.graph.items():
        for dep in dependencies:
            if dep not in reverse_graph:
                reverse_graph[dep] = []
            reverse_graph[dep].append(package)
            in_degree[package] = in_degree.get(package, 0) + 1
    
    # Находим пакеты без зависимостей
    queue = [pkg for pkg in all_packages if in_degree[pkg] == 0]
    load_order = []
    levels_dict: Dict[int, List[str]] = {}
    current_level = 0
    
    while queue:
        current_level_packages = queue[:]
        levels_dict[current_level] = current_level_packages
        queue = []
        
        for package in current_level_packages:
            load_order.append(package)
            
            # Уменьшаем in-degree для зависимых пакетов
            for dependent in reverse_graph.get(package, []):
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)
        
        current_level += 1
    
    # Проверяем наличие нерешенных пакетов\
    unresolved = [pkg for pkg in all_packages if in_degree[pkg] > 0]
    
    return {
        'order': load_order,
        'levels': levels_dict,
        'has_cycles': len(unresolved) > 0,
        'unresolved': unresolved
    }


def format_load_order(graph: DependencyGraph) -> str:
    output = []
    
    load_info = calculate_load_order(graph)
    
    output.append("Порядок загрузки зависимостей")
    
    output.append(f"\nКорневой пакет: {graph.root_package}")
    output.append(f"Всего пакетов для загрузки: {len(load_info['order'])}")
    output.append(f"Уровней загрузки: {len(load_info['levels'])}")
    
    if load_info['has_cycles']:
        output.append(f"Нерешенных пакетов: {len(load_info['unresolved'])}")
        output.append(f"Пакеты в циклах: {', '.join(load_info['unresolved'])}")
    
    output.append("Порядок загрузки по уровням:")
    
    for level, packages in load_info['levels'].items():
        output.append(f"\n** Уровень {level}: ({len(packages)} пакет(ов))")
        for i, pkg in enumerate(packages, 1):
            deps = graph.get_dependencies(pkg)
            deps_str = f" -> зависит от: {', '.join(deps)}" if deps else " (без зависимостей)"
            output.append(f"   {i}. {pkg}{deps_str}")
    
    output.append("Линейный порядок загрузки:")
    
    for i, pkg in enumerate(load_info['order'], 1):
        output.append(f"{i}. {pkg}")
    
    if load_info['unresolved']:
        output.append("Пакеты, не включенные в порядок загрузки (циклы):")
        for pkg in load_info['unresolved']:
            deps = graph.get_dependencies(pkg)
            output.append(f"* {pkg} -> {', '.join(deps)}")
    
    return "\n".join(output)
