import os
import json
import argparse
import sys
from typing import Dict, Any, List, Tuple


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
    for root, dirs, files in os.walk(dir_path):
        for file in files:
            if file.endswith(file_pattern):
                return os.path.join(root, file)
    return ""


def process_config_file(config_file_path: str, template_file_path: str) -> bool:
    """处理单个配置文件"""
    # 读取模板文件
    template_data = read_json_file(template_file_path)
    if not template_data:
        print(f"警告：无法读取模板文件: {template_file_path}")
        return False

    # 读取配置文件
    config_data = read_json_file(config_file_path)
    if not config_data:
        return False

    # 检查配置文件中是否包含outbounds字段
    if "outbounds" not in config_data:
        print(f"警告：配置文件中没有outbounds字段: {config_file_path}")
        return False

    # 创建模板文件的副本
    result_data = template_data.copy()
    # 保留配置文件中的remarks字段（如果存在）
    if "remarks" in config_data:
        result_data["remarks"] = config_data["remarks"]
    # 将配置文件的outbounds字段复制到结果中
    result_data["outbounds"] = config_data["outbounds"]

    # 保存回配置文件
    if save_json_file(config_file_path, result_data):
        print(f"成功处理: {config_file_path}")
        return True
    return False


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
    processed_count = 0

    # 获取绝对路径，用于比较
    config_abs_path = os.path.abspath(config_dir)
    template_abs_path = os.path.abspath(template_dir)

    # 检查配置目录是否等于模板目录
    if config_abs_path == template_abs_path:
        print("错误：配置目录和模板目录不能相同")
        return 0

    # 确保目录存在
    if not os.path.isdir(config_dir):
        print(f"错误：配置目录不存在: {config_dir}")
        return 0

    if not os.path.isdir(template_dir):
        print(f"错误：模板目录不存在: {template_dir}")
        return 0

    # 遍历配置目录中的所有文件
    for root, dirs, files in os.walk(config_dir):
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
                if process_config_file(config_file_path, template_file_path):
                    processed_count += 1

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
