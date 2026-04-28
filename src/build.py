import ast
import asyncio
import importlib.util
import shutil
import sys
from pathlib import Path
from typing import List

from jinja2 import Environment, FileSystemLoader

from src.setup import create_marketplace_db, create_asset_dbs, delete_service_bus_entities


def is_in_venv(file_path: Path) -> bool:
    """
    Checks if a given file path is located inside the current virtual environment's
    site-packages or dist-packages directory.

    Args:
        file_path: The pathlib.Path object of the file to check.

    Returns:
        True if the file is in the venv's site-packages, False otherwise.
    """
    try:
        venv_path = Path(sys.prefix).resolve()
        return venv_path in file_path.parents or "site-packages" in str(file_path) or "dist-packages" in str(file_path)
    except Exception:
        return False


def resolve_module(module_name: str, source_root: Path) -> Path | None:
    """Resolve a module name to a file path inside the source root, if possible."""
    try:
        spec = importlib.util.find_spec(module_name)
    except (ModuleNotFoundError, AttributeError):
        return None

    if spec and spec.origin:
        path = Path(spec.origin).resolve()
        if source_root in path.parents and not is_in_venv(path):
            return path
    return None


def extract_path_from_call(node: ast.Call, source_root: Path, jinja_dirs: list[Path]) -> Path | None:
    """
    Extract file paths from:
    - Path("file")
    - open("file")
    - TemplateResponse(name="template.html")
    """
    # Path("something")
    if isinstance(node.func, ast.Name) and node.func.id == "Path":
        if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
            return (source_root / node.args[0].value).resolve()

    # open("something")
    if isinstance(node.func, ast.Name) and node.func.id == "open":
        if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
            return (source_root / node.args[0].value).resolve()

    # TemplateResponse(name="...")
    if isinstance(node.func, ast.Attribute) and node.func.attr == "TemplateResponse":
        for kw in node.keywords:
            if kw.arg == "name" and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                template_name = kw.value.value
                for template_dir in jinja_dirs:
                    path = (template_dir / template_name).resolve()
                    if path.is_file():
                        return path
    return None


def get_imported_files(start_file: Path, source_root: Path) -> list[str]:
    imported_files = set()
    files_to_process = [start_file.resolve()]
    source_root = source_root.resolve()
    jinja_dirs = []  # dynamically filled from Jinja2Templates(directory=...)

    sys.path.insert(0, str(source_root.parent))

    while files_to_process:
        current_file = files_to_process.pop(0)
        if not current_file.is_file() or current_file in imported_files:
            continue
        imported_files.add(current_file)

        # Parse only Python files
        if current_file.suffix != ".py":
            continue

        try:
            tree = ast.parse(current_file.read_text(encoding="utf-8"), filename=str(current_file))
        except Exception as e:
            print(f"Warning: Could not parse {current_file}. Skipping. Error: {e}")
            continue

        for node in ast.walk(tree):
            # Python imports
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if path := resolve_module(alias.name, source_root):
                        if path not in imported_files:
                            files_to_process.append(path)

            elif isinstance(node, ast.ImportFrom) and node.module:
                for alias in node.names:
                    full_name = f"{node.module}.{alias.name}"
                    path = resolve_module(full_name, source_root) or resolve_module(node.module, source_root)
                    if path and path not in imported_files:
                        files_to_process.append(path)

            elif isinstance(node, ast.Call):
                # Detect Jinja template directories
                if getattr(node.func, "id", None) == "Jinja2Templates":
                    for kw in node.keywords:
                        if kw.arg == "directory" and isinstance(kw.value, ast.Constant):
                            jinja_dirs.append((source_root / kw.value.value).resolve())
                
                # Detect StaticFiles directories
                elif getattr(node.func, "id", None) == "StaticFiles":
                    for kw in node.keywords:
                        if kw.arg == "directory":
                            static_dir = None
                            if isinstance(kw.value, ast.Constant):
                                static_dir = (source_root / kw.value.value).resolve()
                            elif isinstance(kw.value, ast.Call) and getattr(kw.value.func, "id", None) == "Path":
                                if kw.value.args and isinstance(kw.value.args[0], ast.Constant):
                                    static_dir = (source_root / kw.value.args[0].value).resolve()
                            
                            if static_dir and static_dir.is_dir():
                                for file_path in static_dir.rglob("*"):
                                    if file_path.is_file() and file_path not in imported_files:
                                        files_to_process.append(file_path)
                
                # Other file path calls
                else:
                    if file_path := extract_path_from_call(node, source_root, jinja_dirs):
                        if file_path.is_file() and file_path not in imported_files:
                            files_to_process.append(file_path)

    sys.path.pop(0)
    return sorted(str(p) for p in imported_files)

def copy_files(file_list: list[str], dest_dir: Path, source_root: Path):
    """
    Copies a list of files to a destination directory, preserving the original
    directory structure relative to the source_root.

    Args:
        file_list: A list of absolute file paths to copy.
        dest_dir: The destination directory to copy files into.
        source_root: The root directory of the source files (e.g., the 'src' folder).
    """
    for src_path_str in file_list:
        src_path = Path(src_path_str)
        # Construct the destination path, preserving the subdirectory structure
        # relative to the source_root.
        relative_path = src_path.relative_to(source_root)
        dest_path = dest_dir / relative_path

        # Create parent directories if they don't exist
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        # Copy the file
        shutil.copy2(src_path, dest_path)
        print(f"Copied {src_path.relative_to(source_root)} to {dest_path}")


def build(source: Path, configs: List[str]):
    """
    Main function to orchestrate the build process for different user environments.
    """
    # The root of your application's source code
    source_root = Path(".").resolve()

    print(f"Starting build process from source root: {source_root}")

    # Find the files imported by the main application file
    all_imported_files = get_imported_files(Path(source).resolve(), source_root)

    if not all_imported_files:
        print("Warning: No imported application files were found.")
        return

    print("\n--- Identified Application Files to Copy ---")
    for f in all_imported_files:
        print(f"- {f}")

    print("\n--- Creating build directories and copying files for each user ---")

    for user in configs:
        dist_dir = Path("dist") / user
        print(f"\nCopying files for '{user}'. Destination: '{dist_dir}'")

        try:
            # Create the destination directory for the current user
            shutil.rmtree(dist_dir, ignore_errors=True)
            dist_dir.mkdir(parents=True, exist_ok=True)

            # Copy the identified files to the new directory
            copy_files(all_imported_files, dist_dir, source_root)

            print(f"Successfully created build for '{user}' in '{dist_dir}'")
        except Exception as e:
            print(f"Error processing user '{user}': {e}")
            continue


env = Environment(loader=FileSystemLoader('src/templates'))

ports = {
    "marketplace": 8000,
    "manufacturer": 8001,
    "recycler": 8002,
    "recycler_2": 8003,
    "fleet": 8004,
    "manufacturer_2": 8005,
    "oem": 8006,
    "fleet_2": 8007,
    "oem_2": 8008,
    "virtual_recycler_agent": 8009,
}


def write_dockerfile(template, config):
    data = {"user":config}
    if config in ports:
        data["port"] = ports[config]
    j_template = env.get_template(template)
    rendered = j_template.render(data)
    Path(f"./dist/{config}/Dockerfile").write_text(rendered)


async def main():
    dist = Path("./dist")
    if dist.exists():
        shutil.rmtree(dist)
    dist.mkdir()

    x = input("Do you want to delete all existing Service Bus topics/subscriptions? (yes/no, default no)\n> ")
    if x.lower() == "yes":
        print("Deleting all existing Service Bus topics/subscriptions...")
        await delete_service_bus_entities(market_db_path="./dist/marketplace/marketplace.db")
        print("Service Bus cleanup complete.")


    base_image = dist / "base_image"
    base_image.mkdir()
    shutil.copy2(Path("./src/templates/base_image.dockerfile"), base_image / "Dockerfile")
    shutil.copy2(Path("./pyproject.toml"), base_image / "pyproject.toml")
    shutil.copy2(Path("./uv.lock"), base_image / "uv.lock")
    print("Base image files copied.")

    build(Path("src/main.py"), ["marketplace"])
    write_dockerfile("marketplace.dockerfile", "marketplace")
    config_dir = Path("src/assets/config")
    users = [x.stem for x in config_dir.iterdir() if not "__" in x.stem and not "template" in x.stem]
    build(Path("src/agent.py"), users)

    await create_marketplace_db(marketplace_db_path="./dist/marketplace/marketplace.db", config_dir=config_dir)

    for config in users:
        await create_asset_dbs(asset_db_dir=Path(f"./dist/{config}/"), config=config)
        write_dockerfile("agent.dockerfile", config)

    print("Copying files for frontend. Please copy the dist folder from npm run build manually into dist/frontend")
    frontend = Path("dist/frontend")
    frontend.mkdir()
    shutil.copy2(Path("./src/templates/nginx.conf"), frontend)
    write_dockerfile("frontend.dockerfile", "frontend")

    print("\nBuild process complete.")


if __name__ == "__main__":
    asyncio.run(main())
