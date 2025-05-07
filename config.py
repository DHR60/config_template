import os
import json
import argparse
import sys
from typing import Dict, Any, List, Tuple, Optional


def read_json_file(file_path: str) -> Dict[Any, Any]:
    """读取JSON文件并返回其内容"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"错误：无法读取文件 {file_path}：{e}")
        return {}


def save_json_file(file_path: str, data: Dict[Any, Any]) -> bool:
    """保存JSON数据到文件"""
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"错误：无法保存文件 {file_path}：{e}")
        return False


def find_template_file(dir_path: str, file_pattern: str) -> str:
    """递归查找目录中的模板文件"""
    for root, _, files in os.walk(dir_path):
        for file in files:
            if file.endswith(file_pattern):
                return os.path.join(root, file)
    return ""


def merge_config_with_template(
    config_data: Dict[Any, Any], template_data: Dict[Any, Any]
) -> Dict[Any, Any]:
    """将配置数据与模板数据合并"""
    # 创建模板文件的副本
    result_data = template_data.copy()

    # 保留配置文件中的remarks字段（如果存在）
    if "remarks" in config_data:
        result_data["remarks"] = config_data["remarks"]

    # 将配置文件的outbounds字段复制到结果中
    result_data["outbounds"] = config_data["outbounds"]

    return result_data


def validate_config_data(config_data: Dict[Any, Any], file_path: str) -> bool:
    """验证配置数据是否有效"""
    if not config_data:
        return False

    if "outbounds" not in config_data:
        print(f"警告：配置文件中没有outbounds字段: {file_path}")
        return False

    return True


def process_config_file(config_file_path: str, template_file_path: str) -> bool:
    """处理单个配置文件，使用模板更新配置"""
    # 读取模板文件
    template_data = read_json_file(template_file_path)
    if not template_data:
        print(f"警告：无法读取模板文件: {template_file_path}")
        return False

    # 读取配置文件
    config_data = read_json_file(config_file_path)
    if not validate_config_data(config_data, config_file_path):
        return False

    # 合并配置与模板
    result_data = merge_config_with_template(config_data, template_data)

    # 保存回配置文件
    if save_json_file(config_file_path, result_data):
        print(f"成功处理: {config_file_path}")
        return True
    return False


def process_file_with_template(
    config_file_path: str,
    template_file_path: str,
    target_file_path: Optional[str] = None,
) -> bool:
    """
    处理配置文件并使用模板更新，可选择保存到新位置

    Args:
        config_file_path: 源配置文件路径
        template_file_path: 模板文件路径
        target_file_path: 目标保存路径，None则覆盖源文件

    Returns:
        处理是否成功
    """
    # 读取模板文件
    template_data = read_json_file(template_file_path)
    if not template_data:
        print(f"警告：无法读取模板文件: {template_file_path}")
        return False

    # 读取配置文件
    config_data = read_json_file(config_file_path)
    if not validate_config_data(config_data, config_file_path):
        return False

    # 合并配置与模板
    result_data = merge_config_with_template(config_data, template_data)

    # 决定保存的目标路径
    save_path = target_file_path if target_file_path else config_file_path

    # 保存文件
    if save_json_file(save_path, result_data):
        if target_file_path:
            print(f"成功处理并保存到新位置: {save_path}")
        else:
            print(f"成功处理: {save_path}")
        return True
    return False


def process_special_template_folders(
    config_dir: str,
    template_dir: str,
    config_file_pattern: str,
    template_file_pattern: str,
) -> int:
    """
    处理特殊的+开头模板文件夹

    Args:
        config_dir: 配置目录
        template_dir: 模板目录
        config_file_pattern: 配置文件的模式
        template_file_pattern: 模板文件的模式

    Returns:
        成功处理的文件数量
    """
    processed_count = 0
    template_abs_path = os.path.abspath(template_dir)

    # 遍历模板目录以查找特殊文件夹（以+开头）
    for t_root, t_dirs, _ in os.walk(template_dir):
        # Iterate over a copy of t_dirs if we modify it (e.g., for pruning)
        for t_dirname in list(t_dirs):
            if t_dirname.startswith("+"):
                special_template_folder_path = os.path.join(t_root, t_dirname)
                special_folder_name_stripped = t_dirname[1:]  # 例如 "direct_rule_set"

                # 在此特殊模板文件夹中查找模板文件
                template_file_path = find_template_file(
                    special_template_folder_path, template_file_pattern
                )

                if not template_file_path:
                    print(
                        f"警告：在特殊模板目录 {special_template_folder_path} 中找不到模板文件"
                    )
                    continue

                # 确定相应的源配置目录
                # t_root 是特殊文件夹的父目录 (例如 .../template_dir/android)
                # rel_path_from_template_root 是 t_root 相对于 template_dir 的路径 (例如 "android")
                rel_path_from_template_root = os.path.relpath(t_root, template_abs_path)

                # 用于扫描源文件的配置目录
                if rel_path_from_template_root == ".":
                    # 特殊文件夹位于 template_dir 的根目录下
                    config_source_dir = config_dir
                else:
                    config_source_dir = os.path.join(
                        config_dir, rel_path_from_template_root
                    )

                # 将保存已处理文件的目标目录
                # 这将是 config_source_dir / special_folder_name_stripped
                # 例如 .../config_dir/android/direct_rule_set
                target_output_base_dir = os.path.join(
                    config_source_dir, special_folder_name_stripped
                )

                # 确保目标输出目录存在
                os.makedirs(target_output_base_dir, exist_ok=True)

                print(f"处理特殊模板: {template_file_path}")
                print(f"  源配置目录 (用于查找文件): {config_source_dir}")
                print(f"  目标输出目录 (用于保存文件): {target_output_base_dir}")

                # 处理来自 config_source_dir 的文件，使用模板，
                # 并将它们保存到 target_output_base_dir，只处理当前目录下的文件而不递归
                processed = process_config_folder_with_template(
                    config_source_dir,  # 从中处理配置文件的源目录
                    template_file_path,  # 要应用的特殊模板
                    target_output_base_dir,  # 输出的基目录
                    config_file_pattern,
                    recursive=False,  # 不递归处理子目录
                )
                processed_count += processed

                # 从 t_dirs 中移除已处理的特殊文件夹，以防止 os.walk 进一步深入
                # （例如，如果 +direct_rule_set 内部还有其他 +文件夹，我们不希望将其视为新的顶级特殊操作）
                if t_dirname in t_dirs:
                    t_dirs.remove(t_dirname)

    return processed_count


def process_config_folder_with_template(
    config_dir: str,
    template_file_path: str,
    target_dir: str,
    config_file_pattern: str,
    recursive: bool = True,
) -> int:
    """
    用单个模板处理整个配置目录，将结果保存到目标目录

    Args:
        config_dir: 配置文件目录
        template_file_path: 模板文件路径
        target_dir: 结果保存目录
        config_file_pattern: 配置文件的模式
        recursive: 是否递归处理子目录（默认为True）

    Returns:
        成功处理的文件数量
    """
    processed_count = 0

    # 如果递归，使用os.walk处理整个目录树
    if recursive:
        walk_function = os.walk
    else:
        # 如果不递归，创建一个只处理当前目录的函数
        def walk_current_dir_only(dir_path):
            dirs = []
            files = []
            try:
                with os.scandir(dir_path) as it:
                    for entry in it:
                        if entry.is_file():
                            files.append(entry.name)
                        elif entry.is_dir():
                            dirs.append(entry.name)
            except Exception as e:
                print(f"警告：无法扫描目录 {dir_path}: {e}")
            yield dir_path, dirs, files

        walk_function = walk_current_dir_only

    # 处理配置目录中的文件
    for root, _, files in walk_function(config_dir):
        for file in files:
            if file.endswith(config_file_pattern):
                config_file_path = os.path.join(root, file)

                # 创建与源配置文件相同结构的目标文件路径
                rel_path = os.path.relpath(root, config_dir)
                target_subdir = (
                    os.path.join(target_dir, rel_path)
                    if rel_path != "."
                    else target_dir
                )
                os.makedirs(target_subdir, exist_ok=True)
                target_file_path = os.path.join(target_subdir, file)

                # 处理文件
                if process_file_with_template(
                    config_file_path, template_file_path, target_file_path
                ):
                    processed_count += 1

    return processed_count


def process_normal_template_folders(
    config_dir: str,
    template_dir: str,
    config_file_pattern: str,
    template_file_pattern: str,
) -> int:
    """
    处理常规的模板文件夹结构（按照目录对应关系）

    Args:
        config_dir: 配置目录
        template_dir: 模板目录
        config_file_pattern: 配置文件的模式
        template_file_pattern: 模板文件的模式

    Returns:
        成功处理的文件数量
    """
    processed_count = 0
    config_abs_path = os.path.abspath(config_dir)
    template_abs_path = os.path.abspath(template_dir)

    # 遍历配置目录中的所有文件
    for root, _, files in os.walk(config_dir):
        # 跳过模板目录
        if os.path.abspath(root).startswith(template_abs_path):
            continue

        # 计算相对路径，用于查找对应的模板目录
        rel_path = os.path.relpath(root, config_dir)
        if rel_path == ".":  # 根目录
            continue

        # 构建对应的模板目录路径
        corresponding_template_dir = os.path.join(template_dir, rel_path)

        # 如果对应的模板目录不存在，跳过
        if not os.path.isdir(corresponding_template_dir):
            continue

        # 查找模板文件
        template_file_path = find_template_file(
            corresponding_template_dir, template_file_pattern
        )
        if not template_file_path:
            print(f"警告：在模板目录/{rel_path}中找不到模板文件")
            continue

        # 处理当前目录中的所有配置文件
        for file in files:
            if file.endswith(config_file_pattern):
                config_file_path = os.path.join(root, file)
                if process_file_with_template(config_file_path, template_file_path):
                    processed_count += 1

    return processed_count


def process_directories_recursive(
    config_dir: str,
    template_dir: str,
    config_file_pattern: str = ".json",
    template_file_pattern: str = ".json",
) -> int:
    """
    递归处理配置目录和模板目录中的JSON文件

    Args:
        config_dir: 源配置目录，包含配置文件
        template_dir: 模板目录，包含模板文件
        config_file_pattern: 配置文件的模式
        template_file_pattern: 模板文件的模式

    Returns:
        成功处理的文件数量
    """
    # 获取绝对路径，用于比较
    config_abs_path = os.path.abspath(config_dir)
    template_abs_path = os.path.abspath(template_dir)

    # 基本验证
    if config_abs_path == template_abs_path:
        print("错误：配置目录和模板目录不能相同")
        return 0

    if not os.path.isdir(config_dir):
        print(f"错误：配置目录不存在: {config_dir}")
        return 0

    if not os.path.isdir(template_dir):
        print(f"错误：模板目录不存在: {template_dir}")
        return 0

    processed_count = 0

    # 1. 处理特殊的+开头模板文件夹
    special_processed = process_special_template_folders(
        config_dir, template_dir, config_file_pattern, template_file_pattern
    )
    processed_count += special_processed

    # 2. 处理常规目录结构
    normal_processed = process_normal_template_folders(
        config_dir, template_dir, config_file_pattern, template_file_pattern
    )
    processed_count += normal_processed

    return processed_count


def main():
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description="JSON文件合并工具")
    parser.add_argument("-a", "--config-dir", type=str, help="包含配置文件的源目录")
    parser.add_argument("-b", "--template-dir", type=str, help="包含模板文件的目录")
    parser.add_argument(
        "-c",
        "--config-pattern",
        type=str,
        default=".json",
        help="配置文件的后缀模式（默认：.json）",
    )
    parser.add_argument(
        "-d",
        "--template-pattern",
        type=str,
        default=".json",
        help="模板文件的后缀模式（默认：.json）",
    )

    args = parser.parse_args()

    config_dir = args.config_dir
    template_dir = args.template_dir

    # 如果命令行没有提供参数，则使用交互模式
    if config_dir is None or template_dir is None:
        print("=== JSON文件合并工具 ===")
        config_dir = input("请输入源配置目录的路径（包含配置文件）: ").strip()
        template_dir = input("请输入模板目录的路径（包含模板文件）: ").strip()
        config_pattern = (
            input("请输入配置文件的后缀模式（直接回车使用默认值.json）: ").strip()
            or ".json"
        )
        template_pattern = (
            input("请输入模板文件的后缀模式（直接回车使用默认值.json）: ").strip()
            or ".json"
        )
    else:
        config_pattern = args.config_pattern
        template_pattern = args.template_pattern

    # 处理目录
    processed_count = process_directories_recursive(
        config_dir, template_dir, config_pattern, template_pattern
    )

    print(f"\n处理完成！共处理了 {processed_count} 个文件。")


if __name__ == "__main__":
    main()
