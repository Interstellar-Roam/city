# UV 快速设置指南

## 什么是 uv？

uv 是一个用 Rust 编写的极速 Python 包管理工具，由 Astral（Ruff 的开发者）开发。

### 为什么选择 uv？

- ⚡ **极速**: 比 pip 快 10-100 倍
- 🔧 **简单**: 自动管理 Python 版本和虚拟环境
- 🔄 **兼容**: 完全兼容 pip 和 requirements.txt
- 🎯 **可靠**: 确定性的依赖解析

## 安装 uv

### macOS / Linux

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Windows

```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 验证安装

```bash
uv --version
# 输出: uv 0.x.x
```

## 项目中使用 uv

### 1. 安装项目依赖

```bash
# 自动创建 Python 3.12 虚拟环境并安装所有依赖
uv sync
```

这会：
- 检测 `.python-version` 文件中的 Python 版本（3.12）
- 如果需要，自动下载并安装 Python 3.12
- 创建虚拟环境（`.venv` 目录）
- 安装 `pyproject.toml` 中定义的所有依赖

### 2. 运行脚本

```bash
# 方式一：使用 uv run（推荐）
uv run python scripts/init_db.py
uv run python scripts/test_api.py

# 方式二：激活虚拟环境后直接运行
source .venv/bin/activate
python scripts/init_db.py
```

### 3. 启动服务

```bash
# 开发模式
uv run uvicorn app.main:app --reload

# 生产模式
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 4. 添加新依赖

```bash
# 添加生产依赖
uv add package-name

# 添加开发依赖
uv add --dev package-name

# 示例：添加 requests
uv add requests
```

### 5. 更新依赖

```bash
# 更新所有依赖
uv sync --upgrade

# 更新特定包
uv add package-name@latest
```

## 常用命令

### 项目管理

```bash
# 初始化新项目
uv init

# 安装依赖
uv sync

# 安装生产依赖（不含开发依赖）
uv sync --no-dev

# 清理虚拟环境
uv venv --clear
```

### 包管理

```bash
# 添加依赖
uv add package-name

# 添加指定版本
uv add package-name==1.2.3

# 添加开发依赖
uv add --dev pytest

# 移除依赖
uv remove package-name

# 显示已安装的包
uv pip list

# 冻结依赖
uv pip freeze > requirements.txt
```

### Python 管理

```bash
# 列出可用的 Python 版本
uv python list

# 安装特定版本的 Python
uv python install 3.12

# 设置项目的 Python 版本
uv python pin 3.12

# 显示当前使用的 Python
uv python find
```

### 运行命令

```bash
# 在虚拟环境中运行命令
uv run command

# 示例
uv run python -m pytest
uv run black .
uv run ruff check .
```

## 一键启动脚本

项目提供了 `start.sh` 脚本，自动完成所有步骤：

```bash
./start.sh
```

脚本会：
1. ✅ 检查 uv 是否安装
2. ✅ 检查 Docker 服务状态
3. ✅ 安装所有依赖
4. ✅ 提示初始化数据库
5. ✅ 启动开发服务器

## 开发工作流

### 日常开发

```bash
# 1. 启动服务（自动重载）
uv run uvicorn app.main:app --reload

# 2. 在另一个终端运行测试
uv run pytest

# 3. 代码格式化
uv run black .
uv run ruff check .
```

### 添加新功能

```bash
# 1. 创建功能分支
git checkout -b feature/new-feature

# 2. 安装新的依赖（如果需要）
uv add new-package

# 3. 编写代码和测试
# ...

# 4. 运行测试
uv run pytest

# 5. 提交代码
git add .
git commit -m "Add new feature"
```

## 故障排查

### 问题：Python 版本不匹配

```bash
# 检查项目 Python 版本
cat .python-version

# 安装正确的 Python 版本
uv python install 3.12

# 重新创建虚拟环境
uv venv --clear
uv sync
```

### 问题：依赖安装失败

```bash
# 清理缓存
uv cache clean

# 重新安装
uv sync --reinstall
```

### 问题：虚拟环境损坏

```bash
# 删除虚拟环境
rm -rf .venv

# 重新创建
uv sync
```

### 问题：找不到模块

```bash
# 确保使用 uv run
uv run python your_script.py

# 而不是直接运行
python your_script.py  # ❌ 不会使用虚拟环境
```

## 性能对比

| 操作 | pip | uv | 提升 |
|------|-----|----|----|
| 安装依赖 | ~30s | ~2s | 15x |
| 创建虚拟环境 | ~5s | ~0.2s | 25x |
| 解析依赖 | ~10s | ~0.5s | 20x |

## 最佳实践

1. **总是使用 `uv run`**: 确保在正确的虚拟环境中运行
2. **提交 `.python-version`**: 让团队使用相同的 Python 版本
3. **定期更新依赖**: `uv sync --upgrade` 保持依赖最新
4. **使用开发依赖**: 将测试、格式化工具放在 `dev-dependencies`
5. **锁文件**: uv 会自动创建 `uv.lock`，提交到版本控制

## 参考资源

- [uv 官方文档](https://docs.astral.sh/uv/)
- [uv GitHub](https://github.com/astral-sh/uv)
- [从 pip 迁移到 uv](https://docs.astral.sh/uv/guides/integrations/pip/)
