"""
课程质量评估 Agent

该模块负责评估课程内容的质量，检测争议、谬误等问题，
生成质量报告并持久化为JSON文件（存储在course目录中）。

注意：质量评估报告不依赖业务数据库，完全独立存储。
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
import json
import re
from pathlib import Path
from datetime import datetime

from ..models import (
    Chapter,
    QualityReport,
    QualityIssue,
    IssueType,
    IssueSeverity,
)


@dataclass
class EvaluationContext:
    """评估上下文"""
    course_id: str
    course_title: str
    chapters: List[Chapter]
    evaluation_config: Dict[str, Any] = field(default_factory=dict)


class QualityEvaluator:
    """
    课程质量评估器
    
    使用规则引擎 + LLM（可选）进行质量检查
    
    检查维度：
    1. 内容完整性 - 是否有未完成的章节、缺失的解释
    2. 逻辑一致性 - 前后描述是否矛盾
    3. 准确性检查 - 技术描述是否正确
    4. 争议识别 - 是否包含有争议的观点
    5. 格式规范 - Markdown格式是否正确
    """
    
    # 需要特别关注的技术术语（可能有争议或快速演进）
    TECH_TERMS_TO_CHECK = [
        "LLM", "GPT", "大模型", "大语言模型",
        "Agent", "智能体",
        "RAG", "检索增强",
        "Transformer", "注意力机制",
        "Prompt", "提示词",
        "Fine-tuning", "微调",
    ]
    
    # 常见的需要版本说明的技术
    VERSION_SENSITIVE_TERMS = [
        "Python", "JavaScript", "React", "Vue",
        "PyTorch", "TensorFlow", "LangChain",
    ]
    
    def __init__(self, llm_client: Optional[Any] = None):
        """
        初始化评估器
        
        Args:
            llm_client: 可选的LLM客户端，用于更智能的评估
        """
        self.llm_client = llm_client
    
    def evaluate(self, context: EvaluationContext) -> QualityReport:
        """
        执行质量评估
        
        Args:
            context: 评估上下文
        
        Returns:
            质量评估报告
        """
        report = QualityReport(
            course_id=context.course_id,
            evaluated_at=datetime.now()
        )
        
        # 1. 检查内容完整性
        self._check_completeness(context, report)
        
        # 2. 检查逻辑一致性
        self._check_consistency(context, report)
        
        # 3. 检查准确性（规则部分）
        self._check_accuracy_rules(context, report)
        
        # 4. 检查争议内容
        self._check_controversial_content(context, report)
        
        # 5. 检查格式规范
        self._check_format(context, report)
        
        # 6. 如果有LLM客户端，执行智能评估
        if self.llm_client:
            self._llm_evaluation(context, report)
        
        # 计算总分
        report.calculate_overall_score()
        
        # 生成总结
        self._generate_summary(report)
        
        return report
    
    def _check_completeness(self, context: EvaluationContext, report: QualityReport):
        """检查内容完整性"""
        for chapter in context.chapters:
            # 检查空章节
            if not chapter.content.strip():
                report.add_issue(QualityIssue(
                    issue_type=IssueType.INCOMPLETE,
                    severity=IssueSeverity.HIGH,
                    file_name=chapter.file_name,
                    title=f"章节内容为空: {chapter.title}",
                    description=f"章节 '{chapter.title}' 没有任何内容",
                    suggestion="请补充章节内容或移除该章节"
                ))
                continue
            
            # 检查过短章节（可能是待完成）
            if chapter.word_count < 100:
                report.add_issue(QualityIssue(
                    issue_type=IssueType.INCOMPLETE,
                    severity=IssueSeverity.MEDIUM,
                    file_name=chapter.file_name,
                    title=f"章节内容过短: {chapter.title}",
                    description=f"章节 '{chapter.title}' 只有 {chapter.word_count} 字，可能未完成",
                    suggestion="请检查是否需要补充更多内容"
                ))
            
            # 检查TODO标记
            todos = re.findall(r'(TODO|FIXME|待完成|待补充|TBD)[:：]?\s*(.+)', chapter.content, re.IGNORECASE)
            for match in todos:
                report.add_issue(QualityIssue(
                    issue_type=IssueType.INCOMPLETE,
                    severity=IssueSeverity.MEDIUM,
                    file_name=chapter.file_name,
                    text_snippet=str(match),
                    title=f"发现待完成标记: {match[1][:50]}...",
                    description=f"在章节 '{chapter.title}' 中发现待完成标记",
                    suggestion="请完成标记的内容或移除标记"
                ))
    
    def _check_consistency(self, context: EvaluationContext, report: QualityReport):
        """检查逻辑一致性"""
        # 收集所有章节中的术语使用
        term_usage: Dict[str, List[str]] = {}
        
        for chapter in context.chapters:
            content = chapter.content
            
            # 检查术语定义是否一致
            # 例如：同一个术语在不同地方有不同的解释
            
            # 提取"xxx是"或"xxx是指"模式的定义
            definitions = re.findall(
                r'([^\n，。]{2,20})(?:是|是指|定义为)[：:]*([^\n。]+)',
                content
            )
            
            for term, definition in definitions:
                term = term.strip()
                if term not in term_usage:
                    term_usage[term] = []
                term_usage[term].append({
                    "chapter": chapter.title,
                    "definition": definition.strip()[:100]
                })
        
        # 检查重复定义（可能是前后不一致）
        for term, usages in term_usage.items():
            if len(usages) > 1:
                definitions = [u["definition"] for u in usages]
                # 简单检查：如果定义差异很大，可能是问题
                unique_defs = set(definitions)
                if len(unique_defs) > 1 and len(term) > 2:  # 忽略太短的术语
                    report.add_issue(QualityIssue(
                        issue_type=IssueType.QUESTION,
                        severity=IssueSeverity.LOW,
                        title=f"术语可能存在不一致定义: {term}",
                        description=f"术语 '{term}' 在不同章节有不同定义:\n" + 
                                  "\n".join([f"- {u['chapter']}: {u['definition']}" for u in usages[:3]]),
                        suggestion="请检查这些定义是否需要统一"
                    ))
    
    def _check_accuracy_rules(self, context: EvaluationContext, report: QualityReport):
        """使用规则检查准确性"""
        for chapter in context.chapters:
            content = chapter.content
            
            # 检查版本敏感的技术是否标注了版本
            for term in self.VERSION_SENSITIVE_TERMS:
                if term in content:
                    # 检查是否有版本号
                    version_pattern = rf'{term}\s*[\d.]+|{term}\s*[\(（].*版本.*[\)）]'
                    if not re.search(version_pattern, content):
                        # 检查是否有"版本"或"version"相关说明
                        if not re.search(rf'{term}.*(?:版本|version|v\d)', content, re.IGNORECASE):
                            report.add_issue(QualityIssue(
                                issue_type=IssueType.OUTDATED,
                                severity=IssueSeverity.LOW,
                                file_name=chapter.file_name,
                                title=f"可能缺少版本说明: {term}",
                                description=f"章节 '{chapter.title}' 中提到了 {term}，但没有说明使用的版本",
                                suggestion=f"建议添加 {term} 的版本信息，避免读者困惑"
                            ))
                            break  # 每个章节只报告一次
            
            # 检查代码块是否有语言标记
            code_blocks = re.findall(r'```(\w*)\n', content)
            for i, lang in enumerate(code_blocks):
                if not lang:
                    report.add_issue(QualityIssue(
                        issue_type=IssueType.SUGGESTION,
                        severity=IssueSeverity.LOW,
                        file_name=chapter.file_name,
                        title="代码块缺少语言标记",
                        description=f"章节 '{chapter.title}' 中第 {i+1} 个代码块没有指定语言",
                        suggestion="建议添加语言标记以获得更好的语法高亮，如 ```python"
                    ))
                    break  # 每个章节只报告一次
    
    def _check_controversial_content(self, context: EvaluationContext, report: QualityReport):
        """检查争议性内容"""
        for chapter in context.chapters:
            content = chapter.content
            
            # 检查技术术语中可能存在争议的表述
            for term in self.TECH_TERMS_TO_CHECK:
                if term in content:
                    # 检查是否有绝对的表述
                    absolute_patterns = [
                        rf'{term}[^。]*?(?:必须|一定|只能|不能|不可)[^。]*',
                        rf'{term}[^。]*?(?:最好|最优|最佳|最差)[^。]*',
                        rf'(?:只有|只有通过){term}[^。]*才能[^。]*',
                    ]
                    
                    for pattern in absolute_patterns:
                        matches = re.findall(pattern, content)
                        for match in matches:
                            report.add_issue(QualityIssue(
                                issue_type=IssueType.CONTROVERSIAL,
                                severity=IssueSeverity.MEDIUM,
                                file_name=chapter.file_name,
                                text_snippet=match[:100],
                                title=f"可能存在争议性表述（{term}相关）",
                                description=f"关于 {term} 的表述可能过于绝对：{match[:100]}",
                                suggestion="技术领域很少有绝对正确的方案，建议使用更中性的表述"
                            ))
            
            # 检查观点性表述（而非事实性表述）
            opinion_patterns = [
                (r'我认为[^。]*', "个人观点"),
                (r'我觉得[^。]*', "个人观点"),
                (r'显然[^。]*', "未经证明的断言"),
                (r'毫无疑问[^。]*', "未经证明的断言"),
            ]
            
            for pattern, issue_desc in opinion_patterns:
                matches = re.findall(pattern, content)
                for match in matches[:1]:  # 每种类型只报告一次
                    report.add_issue(QualityIssue(
                        issue_type=IssueType.SUGGESTION,
                        severity=IssueSeverity.LOW,
                        file_name=chapter.file_name,
                        text_snippet=match[:100],
                        title=f"发现{issue_desc}",
                        description=f"在章节 '{chapter.title}' 中发现：{match[:100]}",
                        suggestion="教程内容建议使用更客观的表述"
                    ))
    
    def _check_format(self, context: EvaluationContext, report: QualityReport):
        for chapter in context.chapters:
            content = chapter.content
            
            heading_levels = [len(h) for h in re.findall(r'^#{1,6}', content, re.MULTILINE)]
            for i in range(len(heading_levels) - 1):
                if heading_levels[i+1] - heading_levels[i] > 1:
                    report.add_issue(QualityIssue(
                        issue_type=IssueType.SUGGESTION,
                        severity=IssueSeverity.LOW,
                        file_name=chapter.file_name,
                        title="标题层级跳跃",
                        description=f"章节 '{chapter.title}' 中标题从 H{heading_levels[i]} 跳到 H{heading_levels[i+1]}",
                        suggestion="建议标题层级不要跳跃，保持层级连续"
                    ))
                    break
            
            # 检查未闭合的代码块
            code_block_count = content.count('```')
            if code_block_count % 2 != 0:
                report.add_issue(QualityIssue(
                    issue_type=IssueType.ERROR,
                    severity=IssueSeverity.HIGH,
                    file_name=chapter.file_name,
                    title="代码块未正确闭合",
                    description=f"章节 '{chapter.title}' 中代码块数量为 {code_block_count}，应该是偶数",
                    suggestion="请检查代码块的 ``` 标记是否成对出现"
                ))
            
            # 检查图片链接
            broken_images = re.findall(r'!\[([^\]]*)\]\(\s*\)', content)
            for alt_text in broken_images:
                report.add_issue(QualityIssue(
                    issue_type=IssueType.ERROR,
                    severity=IssueSeverity.MEDIUM,
                    file_name=chapter.file_name,
                    title="图片链接为空",
                    description=f"章节 '{chapter.title}' 中有图片缺少URL: {alt_text}",
                    suggestion="请补充图片的URL或移除该图片引用"
                ))
    
    def _llm_evaluation(self, context: EvaluationContext, report: QualityReport):
        """使用LLM进行更智能的评估（可选）"""
        if not self.llm_client:
            return
        
        # 将所有章节内容合并用于LLM评估
        full_content = "\n\n---\n\n".join([
            f"# {ch.title}\n\n{ch.content}"
            for ch in context.chapters
        ])
        
        # Langfuse 监控
        from app.llm.langfuse_wrapper import _get_langfuse_client
        from app.llm import get_llm_client
        from prompts import prompt_loader
        
        langfuse_client = _get_langfuse_client()
        trace = None
        start_time = datetime.now()
        
        # 截取内容用于 trace 记录
        max_content_length = prompt_loader.get_config("course_quality_evaluator", "max_content_length", 10000)
        truncated_content = full_content[:max_content_length]
        
        # 准备 trace 输入数据
        input_data = {
            "course_id": context.course_id,
            "course_title": context.course_title,
            "chapter_count": len(context.chapters),
            "content_length": len(full_content),
            "truncated": len(full_content) > max_content_length,
        }
        
        # 创建 Langfuse trace
        if langfuse_client:
            trace = langfuse_client.trace(
                name="course_quality_evaluation",
                input=input_data,
                tags=["course", "quality", "evaluation"],
            )
        
        error_occurred = None
        result_text = ""
        usage_info = None
        issues_found = 0
        
        try:
            # 使用PromptLoader加载提示词模板
            messages = prompt_loader.get_messages(
                "course_quality_evaluator",
                include_templates=["evaluation_request"],
                course_title=context.course_title,
                course_content=truncated_content
            )
            
            # 调用统一的LLM客户端（同步接口）
            llm = get_llm_client()
            response = llm.chat_sync(
                messages=messages,
                temperature=0.3
            )
            
            # 提取 usage 信息
            if response.usage:
                usage_info = {
                    "prompt_tokens": response.usage.get("prompt_tokens"),
                    "completion_tokens": response.usage.get("completion_tokens"),
                    "total_tokens": response.usage.get("total_tokens"),
                }
            
            # 解析结果
            result_text = response.content
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', result_text)
            if json_match:
                issues = json.loads(json_match.group(1))
                issues_found = len(issues)
                for issue in issues:
                    # 找到对应的章节
                    chapter_file = ""
                    for ch in context.chapters:
                        if ch.title == issue.get("chapter"):
                            chapter_file = ch.file_name
                            break
                    
                    report.add_issue(QualityIssue(
                        issue_type=IssueType(issue.get("issue_type", "suggestion")),
                        severity=IssueSeverity(issue.get("severity", "low")),
                        file_name=chapter_file,
                        title=issue.get("title", ""),
                        description=issue.get("description", ""),
                        suggestion=issue.get("suggestion", "")
                    ))
        except Exception as e:
            error_occurred = str(e)
            # LLM评估失败，记录但不影响整体流程
            report.recommendations.append(f"LLM评估未能完成: {str(e)}")
        finally:
            # 记录 trace 到 Langfuse
            if langfuse_client and trace:
                end_time = datetime.now()
                output_data = {
                    "issues_found": issues_found,
                    "response_length": len(result_text),
                    "response_preview": result_text[:500] if result_text else None,
                }
                if error_occurred:
                    output_data["error"] = error_occurred
                
                # 使用 generation 支持 usage 统计
                trace.generation(
                    name="llm_call",
                    input=input_data,
                    output=output_data,
                    model=llm.default_model if (llm := get_llm_client()) else None,
                    usage={
                        "input": usage_info.get("prompt_tokens") if usage_info else None,
                        "output": usage_info.get("completion_tokens") if usage_info else None,
                        "total": usage_info.get("total_tokens") if usage_info else None,
                    },
                    start_time=start_time,
                    end_time=end_time,
                    metadata={"duration_ms": (end_time - start_time).total_seconds() * 1000},
                )
                trace.update(output=output_data)
                langfuse_client.flush()
    
    def _generate_summary(self, report: QualityReport):
        """生成报告总结"""
        if report.total_issues == 0:
            report.summary = "课程内容质量良好，未发现明显问题。"
            return
        
        severity_desc = []
        if report.critical_issues > 0:
            severity_desc.append(f"{report.critical_issues}个严重问题")
        if report.high_issues > 0:
            severity_desc.append(f"{report.high_issues}个高优先级问题")
        if report.medium_issues > 0:
            severity_desc.append(f"{report.medium_issues}个中等问题")
        if report.low_issues > 0:
            severity_desc.append(f"{report.low_issues}个低优先级问题")
        
        type_counts = {}
        for issue in report.issues:
            type_name = issue.issue_type.value
            type_counts[type_name] = type_counts.get(type_name, 0) + 1
        
        type_desc = []
        type_names = {
            "controversial": "争议内容",
            "error": "错误",
            "outdated": "过时信息",
            "incomplete": "不完整",
            "suggestion": "建议",
            "question": "存疑",
        }
        for t, count in type_counts.items():
            type_desc.append(f"{type_names.get(t, t)}{count}个")
        
        report.summary = f"共发现{report.total_issues}个问题（{', '.join(severity_desc)}），" \
                        f"类型分布：{', '.join(type_desc)}。"
        
        # 添加整体建议
        if report.overall_score < 60:
            report.recommendations.append("课程质量评分较低，建议全面审核和修订")
        elif report.overall_score < 80:
            report.recommendations.append("课程质量一般，建议处理高优先级问题后再发布")
        else:
            report.recommendations.append("课程质量良好，可以处理一些改进建议以提升质量")


def save_quality_report(report: QualityReport, output_dir: Path) -> Path:
    """
    将质量报告保存为JSON文件
    
    注意：这是独立的文件存储，不依赖业务数据库
    
    Args:
        report: 质量报告
        output_dir: 输出目录（通常是course目录）
    
    Returns:
        保存的文件路径
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    report_path = output_dir / "quality_report.json"
    
    # 转换为可序列化的字典
    report_dict = {
        "report_id": report.report_id,
        "course_id": report.course_id,
        "overall_score": report.overall_score,
        "completeness_score": report.completeness_score,
        "consistency_score": report.consistency_score,
        "accuracy_score": report.accuracy_score,
        "total_issues": report.total_issues,
        "critical_issues": report.critical_issues,
        "high_issues": report.high_issues,
        "medium_issues": report.medium_issues,
        "low_issues": report.low_issues,
        "summary": report.summary,
        "recommendations": report.recommendations,
        "evaluated_at": report.evaluated_at.isoformat(),
        "evaluator_version": report.evaluator_version,
        "issues": [
            {
                "issue_id": issue.issue_id,
                "issue_type": issue.issue_type.value,
                "severity": issue.severity.value,
                "file_name": issue.file_name,
                "line_start": issue.line_start,
                "line_end": issue.line_end,
                "text_snippet": issue.text_snippet,
                "title": issue.title,
                "description": issue.description,
                "suggestion": issue.suggestion,
                "references": issue.references,
                "status": issue.status
            }
            for issue in report.issues
        ]
    }
    
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report_dict, f, ensure_ascii=False, indent=2)
    
    return report_path


def load_quality_report(report_path: Path) -> Optional[QualityReport]:
    """
    从JSON文件加载质量报告
    
    Args:
        report_path: 报告文件路径
    
    Returns:
        质量报告对象，如果文件不存在则返回None
    """
    if not report_path.exists():
        return None
    
    with open(report_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    report = QualityReport(
        report_id=data["report_id"],
        course_id=data["course_id"],
        overall_score=data["overall_score"],
        completeness_score=data["completeness_score"],
        consistency_score=data["consistency_score"],
        accuracy_score=data["accuracy_score"],
        total_issues=data["total_issues"],
        critical_issues=data["critical_issues"],
        high_issues=data["high_issues"],
        medium_issues=data["medium_issues"],
        low_issues=data["low_issues"],
        summary=data["summary"],
        recommendations=data["recommendations"],
        evaluated_at=datetime.fromisoformat(data["evaluated_at"]),
        evaluator_version=data["evaluator_version"]
    )
    
    for issue_data in data.get("issues", []):
        report.issues.append(QualityIssue(
            issue_id=issue_data["issue_id"],
            issue_type=IssueType(issue_data["issue_type"]),
            severity=IssueSeverity(issue_data["severity"]),
            file_name=issue_data["file_name"],
            line_start=issue_data.get("line_start"),
            line_end=issue_data.get("line_end"),
            text_snippet=issue_data["text_snippet"],
            title=issue_data["title"],
            description=issue_data["description"],
            suggestion=issue_data["suggestion"],
            references=issue_data.get("references", []),
            status=issue_data["status"]
        ))
    
    return report
