"""
提示词加载器

提供提示词的加载、渲染和缓存功能。
支持 YAML 格式的提示词配置文件和 Jinja2 模板渲染。
"""

import yaml
from pathlib import Path
from jinja2 import Template, TemplateError
from typing import Dict, Any, List, Optional
import threading


class PromptLoadError(Exception):
    """提示词加载异常"""
    pass


class PromptRenderError(Exception):
    """提示词渲染异常"""
    pass


class PromptLoader:
    """
    提示词加载器
    
    功能：
    - 从 YAML 文件加载提示词配置
    - 支持 Jinja2 模板变量替换
    - 支持热重载（可配置）
    - 线程安全的缓存机制
    
    使用示例：
        loader = PromptLoader()
        
        # 获取完整消息列表
        messages = loader.get_messages("ai_assistant", course_content="...")
        
        # 仅渲染系统提示词
        system_prompt = loader.render("ai_assistant", suggestion_count=5)
    """
    
    def __init__(
        self, 
        templates_dir: Optional[Path] = None,
        enable_cache: bool = True,
        auto_reload: bool = False
    ):
        """
        初始化提示词加载器
        
        Args:
            templates_dir: 提示词模板目录路径，默认为 prompts/templates/
            enable_cache: 是否启用缓存
            auto_reload: 是否自动重载（每次读取时检查文件变更）
        """
        if templates_dir is None:
            self.templates_dir = Path(__file__).parent / "templates"
        else:
            self.templates_dir = Path(templates_dir)
        self.enable_cache = enable_cache
        self.auto_reload = auto_reload
        self._cache: Dict[str, Dict] = {}
        self._file_mtimes: Dict[str, float] = {}
        self._lock = threading.Lock()
    
    def _check_file_modified(self, name: str) -> bool:
        """检查文件是否被修改"""
        file_path = self.templates_dir / f"{name}.yaml"
        if not file_path.exists():
            return False
        
        current_mtime = file_path.stat().st_mtime
        last_mtime = self._file_mtimes.get(name, 0)
        
        return current_mtime > last_mtime
    
    def load(self, name: str) -> Dict[str, Any]:
        """
        加载提示词配置
        
        Args:
            name: 提示词名称（不含 .yaml 后缀）
            
        Returns:
            提示词配置字典
            
        Raises:
            PromptLoadError: 文件不存在或格式错误
        """
        with self._lock:
            # 检查是否需要重新加载
            if self.enable_cache and name in self._cache:
                if not self.auto_reload or not self._check_file_modified(name):
                    return self._cache[name]
            
            file_path = self.templates_dir / f"{name}.yaml"
            
            if not file_path.exists():
                raise PromptLoadError(f"Prompt template not found: {file_path}")
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
            except yaml.YAMLError as e:
                raise PromptLoadError(f"Failed to parse YAML: {e}")
            
            # 验证必要字段
            if 'system_prompt' not in config:
                raise PromptLoadError(f"Missing required field 'system_prompt' in {name}.yaml")
            
            # 更新缓存
            if self.enable_cache:
                self._cache[name] = config
                self._file_mtimes[name] = file_path.stat().st_mtime
            
            return config
    
    def render(
        self, 
        name: str, 
        template_key: str = "system_prompt",
        **variables
    ) -> str:
        """
        渲染提示词模板
        
        Args:
            name: 提示词名称
            template_key: 要渲染的模板键，默认为 system_prompt
            **variables: 模板变量
            
        Returns:
            渲染后的提示词字符串
            
        Raises:
            PromptRenderError: 模板渲染失败
        """
        config = self.load(name)
        
        # 获取模板内容
        if template_key == "system_prompt":
            template_content = config.get('system_prompt', '')
        else:
            templates = config.get('templates', {})
            template_content = templates.get(template_key, '')
        
        if not template_content:
            raise PromptRenderError(f"Template '{template_key}' not found in {name}.yaml")
        
        # 合并默认变量和传入变量
        defaults = config.get('variables', {})
        merged_vars = {**defaults, **variables}
        
        try:
            template = Template(template_content)
            return template.render(**merged_vars)
        except TemplateError as e:
            raise PromptRenderError(f"Failed to render template: {e}")
    
    def get_messages(
        self, 
        name: str, 
        include_templates: Optional[List[str]] = None,
        **variables
    ) -> List[Dict[str, str]]:
        """
        获取完整的消息列表
        
        构建标准的 OpenAI 格式消息列表，包括：
        1. 系统提示词（system_prompt）
        2. 额外的模板内容（如课程上下文）
        
        Args:
            name: 提示词名称
            include_templates: 要包含的额外模板列表
            **variables: 模板变量
            
        Returns:
            OpenAI 格式的消息列表
        """
        config = self.load(name)
        messages = []
        
        # 添加系统提示词
        system_content = self.render(name, "system_prompt", **variables)
        messages.append({"role": "system", "content": system_content})
        
        # 添加额外的模板内容
        if include_templates:
            for template_key in include_templates:
                try:
                    content = self.render(name, template_key, **variables)
                    if content:
                        messages.append({"role": "system", "content": content})
                except PromptRenderError:
                    pass  # 忽略不存在的模板
        
        return messages
    
    def get_config(self, name: str, key: str, default: Any = None) -> Any:
        """
        获取提示词配置中的特定值
        
        Args:
            name: 提示词名称
            key: 配置键
            default: 默认值
            
        Returns:
            配置值
        """
        config = self.load(name)
        return config.get(key, default)
    
    def clear_cache(self, name: Optional[str] = None):
        """
        清除缓存
        
        Args:
            name: 指定提示词名称，为 None 时清除所有缓存
        """
        with self._lock:
            if name:
                self._cache.pop(name, None)
                self._file_mtimes.pop(name, None)
            else:
                self._cache.clear()
                self._file_mtimes.clear()
    
    def list_prompts(self) -> List[str]:
        """
        列出所有可用的提示词模板
        
        Returns:
            提示词名称列表
        """
        if not self.templates_dir.exists():
            return []
        
        return [
            f.stem for f in self.templates_dir.glob("*.yaml")
        ]


# 全局默认实例
prompt_loader = PromptLoader(enable_cache=True, auto_reload=False)
