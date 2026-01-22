"""
题库转换脚本 - 将 Markdown 格式的题库转换为 JSON/CSV 格式
支持任意 Markdown 文件（默认: sampleQuiz.md）
"""
import re
import json
import csv
import sys
import argparse
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass


@dataclass
class ParsedQuestion:
    """解析后的题目数据结构"""
    quiz_no: str
    quiz_type: str  # '单选' | '多选' | '判断'
    content: str
    options: Dict[str, str]  # {'A': '...', 'B': '...', 'C': '...', 'D': '...'}
    correct_answer: str  # 'A' | 'B' | 'C' | 'D' or multiple answers
    answer_analysis: str
    vault_no: str


def parse_quiz_text_to_json(quiz_text: str, vault_no: str) -> List[Dict[str, Any]]:
    """
    将试题文本转换为JSON格式

    针对 sampleQuiz.md 的特殊格式：
    - 题目格式: "数字、 [类型]" (没有下划线)
    - 选项格式: " A：" (前面没有连字符)
    - 正确答案: "正确答案：X 你的答案：X" (需要忽略"你的答案")
    - 标题行: "单选题/多选题/判断题 （每题1分，共X道题）" (需要忽略)
    """
    # 将不间断空格（\u00A0）替换为普通空格，便于统一处理
    quiz_text = quiz_text.replace('\u00A0', ' ')

    # 按题型分组：先按题型标题分割
    # sampleQuiz.md 的格式： "单选题 （每题1分，共39道题）"
    type_sections = re.split(r'(单选题|多选题|判断题)\s*[（\(].*?[）\)]', quiz_text)
    sections = []
    for i in range(1, len(type_sections), 2):
        if i + 1 < len(type_sections):
            quiz_type_full = type_sections[i].strip()
            section_content = type_sections[i + 1]
            sections.append((quiz_type_full, section_content))

    result = []

    for quiz_type_full, section_content in sections:
        # 确定题型
        if '单选' in quiz_type_full:
            quiz_type = '单选'
        elif '多选' in quiz_type_full:
            quiz_type = '多选'
        elif '判断' in quiz_type_full:
            quiz_type = '判断'
        else:
            continue

        # 按题目分割：每个题目以"数字、"开头
        blocks = re.split(r'(?=\n\s*\d+、)', '\n' + section_content.strip())
        blocks = [block.strip() for block in blocks if block.strip()]

        for block in blocks:
            # 匹配：题号、[类型]、题干
            # sampleQuiz.md 格式: "1、 [单选] 题干内容"
            pattern = r'^(\d+)、\s*\[(单选|多选|判断)\]\s*(.*)'
            match = re.match(pattern, block, re.DOTALL)
            if not match:
                continue

            quiz_no = match.group(1)
            detected_type = match.group(2)
            rest = match.group(3).strip()

            # 提取"正确答案"或"正确选项"
            # sampleQuiz.md 格式: "正确答案：B 你的答案：B" 或 "正确选项：错 你的选项：错"
            # 需要忽略"你的答案/你的选项"部分
            ans_match = re.search(r'(?:正确答案|正确选项)：\s*([^你的]+?)(?=你的[答案选项]|解析：|\s*$)', rest, re.DOTALL)
            suggest_answer = ans_match.group(1).strip() if ans_match else ''

            # 提取"解析"
            ana_match = re.search(r'解析：\s*(.*)', rest, re.DOTALL)
            answer_analysis = ana_match.group(1).strip() if ana_match else ''

            # 题干 = 从开头到"正确答案"之前的内容
            if ans_match:
                quiz_body = rest[:ans_match.start()].strip()
            else:
                quiz_body = rest

            # 提取选项（单选题、多选题和判断题）
            options = {}
            if quiz_type in ['单选', '多选']:
                # sampleQuiz.md 格式: " A：" (前面可能有空格，但没有连字符)
                option_pattern = r'\s*[A-D][:：]\s*(.*?)(?=\n|$)'
                for option_match in re.finditer(option_pattern, quiz_body, re.DOTALL):
                    option_line = option_match.group(0)
                    # 提取选项字母和内容
                    option_match_detail = re.match(r'\s*([A-D])[:：]\s*(.*)', option_line, re.DOTALL)
                    if option_match_detail:
                        option_key = option_match_detail.group(1)
                        option_value = option_match_detail.group(2).strip()
                        options[option_key] = option_value

                # 从题干中移除选项部分，只保留真正的问题描述
                # 移除以 " A:"、" B:" 等开头的选项行
                quiz_body = re.sub(r'\s*[A-D][:：].*?(?=\n|$)', '', quiz_body, flags=re.DOTALL)
            elif quiz_type == '判断':
                # 判断题：设置标准选项
                options = {
                    'A': '对',
                    'B': '错'
                }

            # 清理题干中多余的空行
            quiz_body = re.sub(r'\n\s*\n+', '\n', quiz_body).strip()

            # 将解析结果转换为标准格式
            # quiz_type 映射: '单选' -> 'single_choice', '判断' -> 'true_false', '多选' -> 'multiple_choice'
            question_type_map = {
                '单选': 'single_choice',
                '多选': 'multiple_choice',
                '判断': 'true_false'
            }

            # 对于多选题，correct_answer可能是 "A,C,D" 这样的格式（逗号分隔）
            # 对于判断题，可能是 "对" 或 "错"，需要映射为 A/B
            # 对于单选题，直接使用 A/B/C/D

            if quiz_type == '多选':
                # 多选题：清理并标准化答案格式
                suggest_answer = suggest_answer.replace('，', ',').replace(' ', '')
                suggest_answer = ','.join(sorted(suggest_answer.split(',')))  # 按字母排序，避免乱序问题
            elif quiz_type == '判断':
                # 判断题特殊处理：对/错 或 √/×
                judge_patterns = {
                    r'对|√|A': 'A',
                    r'错|×|B': 'B'
                }
                for pattern, answer in judge_patterns.items():
                    if re.search(pattern, suggest_answer):
                        suggest_answer = answer
                        break
                # 如果没有找到，默认使用A
                if suggest_answer not in ['A', 'B']:
                    suggest_answer = 'A'
            elif quiz_type == '单选':
                # 单选题：确保答案是大写字母
                suggest_answer = suggest_answer.upper()
                if suggest_answer not in ['A', 'B', 'C', 'D']:
                    # 如果解析失败，尝试从选项中推断
                    if suggest_answer in options:
                        suggest_answer = suggest_answer.upper()
                    else:
                        suggest_answer = 'A'

            result.append({
                "vault_no": vault_no,
                "quiz_no": quiz_no,
                "quiz_type": quiz_type,
                "question_type": question_type_map.get(quiz_type, 'single_choice'),
                "content": quiz_body,
                "options": options if options else None,
                "correct_answer": suggest_answer,
                "explanation": answer_analysis,
                "course_type": "exam",
                "difficulty": 2
            })

    return result


def convert_to_standard_format(parsed_data: List[Dict]) -> List[Dict[str, Any]]:
    """
    转换为标准格式（用于数据库导入）
    """
    standard_questions = []

    for item in parsed_data:
        question = {
            "course_type": "exam",
            "question_type": item["question_type"],
            "content": item["content"],
            "options": item["options"],
            "correct_answer": item["correct_answer"],
            "explanation": item["explanation"],
            "difficulty": item.get("difficulty", 2),
            "knowledge_points": [],  # 可以后续通过LLM提取
            "metadata": {
                "source": "vault_sample",
                "vault_no": item["vault_no"],
                "quiz_no": item["quiz_no"]
            }
        }
        standard_questions.append(question)

    return standard_questions


def save_to_json(data: List[Dict], output_path: Path):
    """保存为JSON格式"""
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✅ JSON文件已保存: {output_path}")
    print(f"   总题数: {len(data)}")


def save_to_csv(data: List[Dict], output_path: Path):
    """保存为CSV格式"""
    if not data:
        return

    fieldnames = [
        'course_type', 'question_type', 'content',
        'option_a', 'option_b', 'option_c', 'option_d',
        'correct_answer', 'explanation', 'difficulty'
    ]

    with open(str(output_path), 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for item in data:
            row = {
                'course_type': item['course_type'],
                'question_type': item['question_type'],
                'content': item['content'],
                'option_a': item['options'].get('A', '') if item.get('options') else '',
                'option_b': item['options'].get('B', '') if item.get('options') else '',
                'option_c': item['options'].get('C', '') if item.get('options') else '',
                'option_d': item.get('D', '') if item.get('options') else '',
                'correct_answer': item['correct_answer'],
                'explanation': item['explanation'],
                'difficulty': item.get('difficulty', 2)
            }
            writer.writerow(row)

    print(f"✅ CSV文件已保存: {output_path}")
    print(f"   总题数: {len(data)}")


def process_sample_quiz_file(vault_path: Path, output_dir: Path):
    """
    处理sampleQuiz.md文件

    Args:
        vault_path: vault文件路径
        output_dir: 输出目录
    """
    print(f"\n处理文件: {vault_path.name}")

    # 读取vault文件内容
    with open(vault_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 提取vault编号（从文件名中）
    vault_no = vault_path.stem.replace('sample', '')

    # 解析题目
    parsed_data = parse_quiz_text_to_json(content, vault_no)

    if not parsed_data:
        print(f"⚠️  未解析到任何题目")
        return []

    print(f"   解析到 {len(parsed_data)} 道题目")

    # 按题型统计
    type_stats = {}
    for item in parsed_data:
        qt = item['quiz_type']
        type_stats[qt] = type_stats.get(qt, 0) + 1

    print(f"   题型分布:")
    for qt, count in type_stats.items():
        print(f"     - {qt}: {count}题")

    # 转换为标准格式
    standard_data = convert_to_standard_format(parsed_data)

    # 保存文件
    output_dir.mkdir(parents=True, exist_ok=True)

    vault_name = vault_path.stem
    json_path = output_dir / f"{vault_name}.json"
    csv_path = output_dir / f"{vault_name}.csv"

    save_to_json(standard_data, json_path)
    save_to_csv(standard_data, csv_path)

    return standard_data


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='将 Markdown 格式的题库转换为 JSON/CSV 格式')
    parser.add_argument(
        '-f', '--file',
        type=str,
        default='sampleQuiz.md',
        help='输入文件名（默认: sampleQuiz.md）。文件应位于 scripts/data/input/ 目录'
    )
    parser.add_argument(
        '-i', '--input-dir',
        type=str,
        default=None,
        help='输入目录路径（默认: scripts/data/input/）'
    )
    parser.add_argument(
        '-o', '--output-dir',
        type=str,
        default=None,
        help='输出目录路径（默认: scripts/data/output/）'
    )
    args = parser.parse_args()

    script_dir = Path(__file__).parent
    input_dir = Path(args.input_dir) if args.input_dir else script_dir / "data" / "input"
    output_dir = Path(args.output_dir) if args.output_dir else script_dir / "data" / "output"

    print(f"脚本目录: {script_dir}")
    print(f"输入目录: {input_dir}")
    print(f"输出目录: {output_dir}\n")

    quiz_path = input_dir / args.file

    if not quiz_path.exists():
        print(f"❌ 文件不存在: {quiz_path}")
        print(f"\n提示：请确保文件位于 {input_dir} 目录下")
        sys.exit(1)

    all_questions = process_sample_quiz_file(quiz_path, output_dir)

    # 生成转换报告
    report_path = output_dir / f"{quiz_path.stem}_conversion_report.md"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(f"# {quiz_path.name} 数据转换报告\n\n")
        f.write(f"## 转换时间\n\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"## 源文件\n\n")
        f.write(f"- 输入目录: `{input_dir}`\n")
        f.write(f"- 源文件: `{quiz_path.name}`\n")
        f.write(f"- 输出目录: `{output_dir}`\n\n")
        f.write(f"## 转换结果\n\n")
        f.write(f"- 总题数: {len(all_questions)}\n")
        f.write(f"- 单选题: {sum(1 for q in all_questions if q['question_type'] == 'single_choice')}\n")
        f.write(f"- 多选题: {sum(1 for q in all_questions if q['question_type'] == 'multiple_choice')}\n")
        f.write(f"- 判断题: {sum(1 for q in all_questions if q['question_type'] == 'true_false')}\n")
        f.write(f"\n## 输出文件\n\n")
        f.write(f"- JSON: `{quiz_path.stem}.json`\n")
        f.write(f"- CSV: `{quiz_path.stem}.csv`\n")

    print(f"\n✅ 转换完成!")
    print(f"\n转换报告已保存: {report_path}")
    print(f"\n下一步:")
    print(f"  1. 检查转换结果: {output_dir / f'{quiz_path.stem}.json'}")
    print(f"  2. 如需导入数据库，运行:")
    print(f"     cd {script_dir}")
    print(f"     uv run python import_questions.py {output_dir / f'{quiz_path.stem}.json'}")


if __name__ == "__main__":
    from datetime import datetime
    main()
