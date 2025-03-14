#!/usr/bin/env python3
"""
Code Analyzer for WEB-AI-Startr.Team

This script:
1. Analyzes project structure and complexity
2. Identifies duplicate code and potential refactoring opportunities
3. Generates visualizations of code dependencies
4. Provides metrics on code quality and maintainability
5. Recommends files and components that can be removed
"""

import os
import sys
import re
import ast
import json
import yaml
from pathlib import Path
import argparse
from typing import Dict, List, Set, Tuple, Counter
from collections import defaultdict
import networkx as nx
import matplotlib.pyplot as plt

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Constants
PROJECT_ROOT = Path(__file__).parent.parent
STRTEAM_DIR = PROJECT_ROOT / "strteam"
CONFIG_DIR = PROJECT_ROOT / "config"
EXCLUDE_DIRS = [
    "__pycache__",
    "WareHouse",
    ".git",
    ".idea",
    "venv",
    "build",
    "dist",
]
EXCLUDE_FILES = [
    "__init__.py",
    "__main__.py",
    "__pycache__",
]


def count_lines(file_path: Path) -> Dict[str, int]:
    """Count lines of code, comments, and blank lines in a file."""
    if not file_path.exists() or file_path.suffix not in {".py", ".md", ".yaml", ".json"}:
        return {"code": 0, "comment": 0, "blank": 0, "total": 0}
    
    code_lines = 0
    comment_lines = 0
    blank_lines = 0
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
            in_multiline_comment = False
            
            for line in lines:
                line = line.strip()
                
                # Check for multiline comments
                if file_path.suffix == ".py":
                    if '"""' in line or "'''" in line:
                        # Toggle multiline comment status if it's a full comment
                        if line.startswith('"""') or line.startswith("'''"):
                            if line.endswith('"""') or line.endswith("'''"):
                                if len(line) > 6:  # It's not just opening/closing quotes
                                    comment_lines += 1
                                else:
                                    blank_lines += 1
                            else:
                                in_multiline_comment = not in_multiline_comment
                                comment_lines += 1
                            continue
                        elif line.endswith('"""') or line.endswith("'''"):
                            in_multiline_comment = not in_multiline_comment
                            comment_lines += 1
                            continue
                    
                    if in_multiline_comment:
                        comment_lines += 1
                        continue
                        
                    if line.startswith("#"):
                        comment_lines += 1
                        continue
                
                if not line:
                    blank_lines += 1
                else:
                    code_lines += 1
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return {"code": 0, "comment": 0, "blank": 0, "total": 0}
        
    total_lines = code_lines + comment_lines + blank_lines
    return {"code": code_lines, "comment": comment_lines, "blank": blank_lines, "total": total_lines}


def get_imports(file_path: Path) -> List[str]:
    """Extract import statements from a Python file."""
    if not file_path.exists() or file_path.suffix != ".py":
        return []
        
    imports = []
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        # Parse the file
        tree = ast.parse(content)
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for name in node.names:
                    imports.append(name.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for name in node.names:
                    imports.append(f"{module}.{name.name}")
    except Exception as e:
        print(f"Error parsing {file_path}: {e}")
        
    return imports


def get_classes_and_functions(file_path: Path) -> Dict[str, List[str]]:
    """Extract class and function definitions from a Python file."""
    if not file_path.exists() or file_path.suffix != ".py":
        return {"classes": [], "functions": []}
        
    classes = []
    functions = []
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        # Parse the file
        tree = ast.parse(content)
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                classes.append(node.name)
            elif isinstance(node, ast.FunctionDef):
                functions.append(node.name)
    except Exception as e:
        print(f"Error parsing {file_path}: {e}")
        
    return {"classes": classes, "functions": functions}


def find_similar_functions(files: List[Path]) -> List[Tuple[Path, Path, str]]:
    """Find similar functions between files."""
    similar_funcs = []
    func_map = {}
    
    for file_path in files:
        if file_path.suffix != ".py":
            continue
            
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                
            # Parse the file
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Get function source code
                    func_source = ast.unparse(node)
                    func_name = node.name
                    
                    # Skip small functions
                    if len(func_source.split("\n")) < 5:
                        continue
                        
                    # Skip dunder methods
                    if func_name.startswith("__") and func_name.endswith("__"):
                        continue
                        
                    if func_name in func_map:
                        similar_funcs.append((file_path, func_map[func_name][0], func_name))
                    else:
                        func_map[func_name] = (file_path, func_source)
        except Exception as e:
            print(f"Error analyzing {file_path}: {e}")
            
    return similar_funcs


def create_dependency_graph(files: List[Path]) -> nx.DiGraph:
    """Create a dependency graph of Python files."""
    G = nx.DiGraph()
    
    # Add nodes for all Python files
    for file_path in files:
        if file_path.suffix != ".py":
            continue
            
        G.add_node(str(file_path.relative_to(PROJECT_ROOT)))
    
    # Add edges based on imports
    for file_path in files:
        if file_path.suffix != ".py":
            continue
            
        imports = get_imports(file_path)
        file_node = str(file_path.relative_to(PROJECT_ROOT))
        
        for import_name in imports:
            # Try to find the corresponding file
            import_parts = import_name.split(".")
            
            # Check if this is a local import
            potential_paths = []
            for i in range(len(import_parts)):
                potential_path = "/".join(import_parts[:i+1]) + ".py"
                potential_paths.append(potential_path)
            
            # Look for the import target in our nodes
            for node in G.nodes():
                for pot_path in potential_paths:
                    if node.endswith(pot_path):
                        G.add_edge(file_node, node)
                        break
    
    return G


def find_unused_files(files: List[Path]) -> List[Path]:
    """Find potentially unused files."""
    # Create dependency graph
    G = create_dependency_graph(files)
    
    # Add entry points
    entry_points = [
        "run.py",
        "setup.py",
        "strteam/__main__.py",
        "strteam/__init__.py",
    ]
    
    # Find files not reachable from entry points
    unused_files = []
    
    for file_path in files:
        if file_path.suffix != ".py":
            continue
            
        file_node = str(file_path.relative_to(PROJECT_ROOT))
        
        # Skip if it's an entry point
        if file_node in entry_points:
            continue
            
        # Check if this file is imported anywhere
        if file_node in G.nodes() and G.in_degree(file_node) == 0:
            # Not imported by any other file
            unused_files.append(file_path)
    
    return unused_files


def generate_module_metrics(files: List[Path]) -> Dict[str, Dict]:
    """Generate metrics for each module."""
    metrics = {}
    
    for file_path in files:
        if file_path.suffix != ".py":
            continue
            
        # Skip files in excluded dirs
        if any(part in str(file_path) for part in EXCLUDE_DIRS):
            continue
            
        # Basic metrics
        line_counts = count_lines(file_path)
        imports = get_imports(file_path)
        classes_funcs = get_classes_and_functions(file_path)
        
        relative_path = str(file_path.relative_to(PROJECT_ROOT))
        module_name = relative_path.replace("/", ".").replace(".py", "")
        
        metrics[module_name] = {
            "path": relative_path,
            "line_counts": line_counts,
            "imports": len(imports),
            "classes": len(classes_funcs["classes"]),
            "functions": len(classes_funcs["functions"]),
            "complexity_score": (
                line_counts["code"] * 0.5 + 
                len(imports) * 2 + 
                len(classes_funcs["classes"]) * 3 + 
                len(classes_funcs["functions"]) * 0.5
            ),
        }
    
    return metrics


def identify_code_duplication(files: List[Path]) -> Dict[str, List]:
    """Identify potential code duplication."""
    # Patterns to look for
    patterns = {
        "similar_functions": [],
        "duplicate_imports": [],
        "repeated_code_blocks": [],
    }
    
    # Find similar functions
    patterns["similar_functions"] = find_similar_functions(files)
    
    # Find duplicate imports
    import_count = Counter()
    for file_path in files:
        if file_path.suffix != ".py":
            continue
            
        imports = get_imports(file_path)
        for imp in imports:
            import_count[imp] += 1
    
    # Find highly duplicated imports
    for imp, count in import_count.items():
        if count > 5:  # Only report imports used in many files
            patterns["duplicate_imports"].append((imp, count))
    
    # Find repeated code blocks (simplified approach)
    code_blocks = defaultdict(list)
    for file_path in files:
        if file_path.suffix != ".py":
            continue
            
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.readlines()
                
            for i in range(len(content) - 5):
                block = "".join(content[i:i+5])
                
                # Skip blocks that are too simple
                if len(block.strip()) < 100:
                    continue
                    
                # Skip blocks that are mostly comments
                if block.count("#") > block.count("\n") / 2:
                    continue
                    
                code_blocks[block].append((file_path, i))
        except Exception as e:
            print(f"Error analyzing {file_path}: {e}")
    
    # Filter for blocks that appear in multiple files
    for block, occurrences in code_blocks.items():
        if len(occurrences) > 1 and len(set(o[0] for o in occurrences)) > 1:
            patterns["repeated_code_blocks"].append(occurrences)
    
    return patterns


def visualize_dependency_graph(files: List[Path], output_file: str = "dependency_graph.png"):
    """Visualize the dependency graph of Python files."""
    G = create_dependency_graph(files)
    
    # Remove disconnected nodes
    to_remove = []
    for node in G.nodes():
        if G.in_degree(node) == 0 and G.out_degree(node) == 0:
            to_remove.append(node)
    
    for node in to_remove:
        G.remove_node(node)
    
    # Draw the graph
    plt.figure(figsize=(20, 16))
    
    # Use different layout algorithms based on graph size
    if len(G.nodes()) > 50:
        # For large graphs, use faster algorithms
        pos = nx.spring_layout(G, seed=42, k=0.15)
    else:
        try:
            # Try to use a more readable layout for smaller graphs
            pos = nx.kamada_kawai_layout(G)
        except:
            # Fall back to spring layout if kamada_kawai fails
            pos = nx.spring_layout(G, seed=42)
    
    # Draw nodes with different colors based on directory
    node_colors = []
    for node in G.nodes():
        if "camel" in node:
            node_colors.append("lightblue")
        elif "chatdev" in node:
            node_colors.append("lightgreen")
        elif "ecl" in node:
            node_colors.append("salmon")
        elif "utils" in node:
            node_colors.append("orange") 
        else:
            node_colors.append("lightgray")
    
    # Draw the graph with improved styling
    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=800, alpha=0.8)
    nx.draw_networkx_labels(G, pos, font_size=8, font_weight="bold")
    nx.draw_networkx_edges(G, pos, width=1.0, alpha=0.5, arrows=True, 
                           arrowstyle='->', arrowsize=15, connectionstyle="arc3,rad=0.1")
    
    plt.title("Project Dependency Graph", fontsize=16)
    plt.axis('off')  # Turn off axis instead of using tight_layout
    
    # Add a legend for node colors
    legend_elements = [
        plt.Line2D([0], [0], marker='o', color='w', label='CAMEL', markerfacecolor='lightblue', markersize=10),
        plt.Line2D([0], [0], marker='o', color='w', label='ChatDev', markerfacecolor='lightgreen', markersize=10),
        plt.Line2D([0], [0], marker='o', color='w', label='ECL', markerfacecolor='salmon', markersize=10),
        plt.Line2D([0], [0], marker='o', color='w', label='Utils', markerfacecolor='orange', markersize=10),
        plt.Line2D([0], [0], marker='o', color='w', label='Other', markerfacecolor='lightgray', markersize=10),
    ]
    plt.legend(handles=legend_elements, loc='upper right')
    
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"Dependency graph saved to {output_file}")


def get_all_files() -> List[Path]:
    """Get all files in the project."""
    files = []
    
    for root, dirs, filenames in os.walk(PROJECT_ROOT):
        # Skip excluded directories
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        
        root_path = Path(root)
        
        for filename in filenames:
            if filename in EXCLUDE_FILES:
                continue
                
            file_path = root_path / filename
            files.append(file_path)
    
    return files


def generate_yaml_flow_diagram() -> Dict:
    """Generate a YAML flow diagram of the project structure."""
    # Start with the overall structure
    flow_diagram = {
        "name": "WEB-AI-Startr.Team",
        "type": "project",
        "components": [
            {
                "name": "Config Management",
                "type": "system",
                "components": [
                    {"name": "JSON Configs", "path": "config/CompanyConfig", "type": "config"},
                    {"name": "YAML Configs", "path": "config/CompanyConfig_yaml", "type": "config"},
                    {"name": "Newstyle Configs", "path": "config/CompanyConfig_newstyle", "type": "config"},
                ]
            },
            {
                "name": "Agent System",
                "type": "system",
                "components": [
                    {"name": "Base Agent", "path": "strteam/camel/agents/base.py", "type": "class"},
                    {"name": "Chat Agent", "path": "strteam/camel/agents/chat_agent.py", "type": "class"},
                    {"name": "Task Agent", "path": "strteam/camel/agents/task_agent.py", "type": "class"},
                    {"name": "Critic Agent", "path": "strteam/camel/agents/critic_agent.py", "type": "class"},
                    {"name": "Role Playing", "path": "strteam/camel/agents/role_playing.py", "type": "class"},
                ]
            },
            {
                "name": "Phase System",
                "type": "system", 
                "components": [
                    {"name": "Phase", "path": "strteam/chatdev/phase.py", "type": "class"},
                    {"name": "Composed Phase", "path": "strteam/chatdev/composed_phase.py", "type": "class"},
                ]
            },
            {
                "name": "Chat Environment",
                "type": "system",
                "components": [
                    {"name": "Chat Environment", "path": "strteam/chatdev/chat_env.py", "type": "class"},
                    {"name": "Chat Chain", "path": "strteam/chatdev/chat_chain.py", "type": "class"},
                ]
            },
            {
                "name": "Execution Flow",
                "type": "flow",
                "flow": [
                    {
                        "phase": "Requirements Analysis",
                        "agents": ["Project Manager", "Planning Agent"],
                        "type": "recursive",
                    },
                    {
                        "phase": "Design",
                        "agents": ["Architect", "Developer"],
                        "type": "recursive",
                    },
                    {
                        "phase": "Implementation",
                        "agents": ["Developer"],
                        "type": "recursive",
                        "sub_phases": [
                            {"name": "Coding", "agents": ["Developer"]},
                            {"name": "Review", "agents": ["Reviewer", "Developer"]},
                        ]
                    },
                    {
                        "phase": "Testing",
                        "agents": ["Tester", "Developer"],
                        "type": "recursive",
                    },
                    {
                        "phase": "Documentation",
                        "agents": ["Documentation", "Developer"],
                        "type": "simple",
                    },
                ]
            }
        ]
    }
    
    return flow_diagram


def main():
    parser = argparse.ArgumentParser(description="WEB-AI-Startr.Team Code Analyzer")
    parser.add_argument("--visualize", action="store_true", help="Generate dependency graph visualization")
    parser.add_argument("--metrics", action="store_true", help="Generate code metrics")
    parser.add_argument("--duplicates", action="store_true", help="Find code duplication")
    parser.add_argument("--flow-diagram", action="store_true", help="Generate YAML flow diagram")
    parser.add_argument("--output", type=str, default="analysis_output", help="Output directory")
    args = parser.parse_args()
    
    # Create output directory
    output_dir = Path(args.output)
    output_dir.mkdir(exist_ok=True)
    
    # Get all files
    print("Gathering files...")
    files = get_all_files()
    print(f"Found {len(files)} files")
    
    if args.visualize:
        print("Generating dependency graph...")
        visualize_dependency_graph(files, output_file=str(output_dir / "dependency_graph.png"))
    
    if args.metrics:
        print("Generating module metrics...")
        metrics = generate_module_metrics(files)
        
        # Sort by complexity
        sorted_metrics = dict(sorted(metrics.items(), key=lambda x: x[1]["complexity_score"], reverse=True))
        
        # Save metrics
        with open(output_dir / "module_metrics.json", "w") as f:
            json.dump(sorted_metrics, f, indent=2)
            
        print(f"Module metrics saved to {output_dir / 'module_metrics.json'}")
        
        # Print top 10 most complex modules
        print("\nTop 10 most complex modules:")
        for i, (module, data) in enumerate(list(sorted_metrics.items())[:10]):
            print(f"{i+1}. {module}: {data['complexity_score']:.1f} complexity score")
    
    if args.duplicates:
        print("Finding code duplication...")
        duplications = identify_code_duplication(files)
        
        # Save duplication report
        with open(output_dir / "duplication_report.json", "w") as f:
            json.dump(
                {
                    "similar_functions": [(str(a), str(b), c) for a, b, c in duplications["similar_functions"]],
                    "duplicate_imports": duplications["duplicate_imports"],
                    "repeated_code_blocks": [[(str(path), line) for path, line in blocks] 
                                             for blocks in duplications["repeated_code_blocks"]],
                },
                f, 
                indent=2
            )
            
        print(f"Duplication report saved to {output_dir / 'duplication_report.json'}")
        
        # Print summary
        print("\nDuplication summary:")
        print(f"- {len(duplications['similar_functions'])} similar functions")
        print(f"- {len(duplications['duplicate_imports'])} heavily duplicated imports")
        print(f"- {len(duplications['repeated_code_blocks'])} repeated code blocks")
    
    if args.flow_diagram:
        print("Generating YAML flow diagram...")
        flow_diagram = generate_yaml_flow_diagram()
        
        # Save flow diagram
        with open(output_dir / "flow_diagram.yaml", "w") as f:
            yaml.dump(flow_diagram, f, default_flow_style=False, sort_keys=False)
            
        print(f"Flow diagram saved to {output_dir / 'flow_diagram.yaml'}")
    
    # Find unused files
    print("\nLooking for potentially unused files...")
    unused = find_unused_files(files)
    
    with open(output_dir / "unused_files.txt", "w") as f:
        for file in sorted(unused):
            print(f"- {file.relative_to(PROJECT_ROOT)}")
            f.write(f"{file.relative_to(PROJECT_ROOT)}\n")
    
    print(f"\nFound {len(unused)} potentially unused files (saved to {output_dir / 'unused_files.txt'})")
    

if __name__ == "__main__":
    main()