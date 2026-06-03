# 桩基预测系统 — 部署与演示指南

## 打包清单（复制这些即可运行）

### 必选文件

| 文件/目录 | 说明 |
|-----------|------|
| `start.py` | 一键启动脚本，uvicorn 入口 |
| `requirements.txt` | Python 依赖清单（9 个包） |
| `server/` | FastAPI 后端全部代码（api/ + core/ + models/ + services/ + main.py/database.py/schemas.py） |

### 前端（二选一）

| 文件/目录 | 说明 |
|-----------|------|
| `client/dist/` | **已构建好的前端静态文件**（推荐，无需 Node.js 即可运行） |

> 如果目标电脑需要修改前端源码并重新构建，则额外复制：
> - `client/package.json` — 前端依赖与脚本
> - `client/vite.config.ts` — Vite 构建配置
> - `client/tsconfig.json` / `tsconfig.app.json` / `tsconfig.node.json` — TypeScript 配置
> - `client/index.html` — HTML 入口
> - `client/src/` — React/TypeScript 源码（23 个文件）

### 测试数据（可选）

| 文件/目录 | 说明 |
|-----------|------|
| `test_files/` | 示例地勘 + 桩基 Excel/CSV 数据，用于演示导入 |

### 说明文档

| 文件/目录 | 说明 |
|-----------|------|
| `DEPLOY.md` | 本文件，部署与使用说明 |

---

## 不需要复制的文件

以下目录/文件仅用于开发，打包时请排除：

| 排除项 | 原因 |
|--------|------|
| `.git/` | Git 版本历史，与运行无关 |
| `node_modules/` | 前端依赖，体积巨大，可通过 `npm install` 重新安装 |
| `__pycache__/` / `*.pyc` | Python 字节码缓存 |
| `legacy/` | 旧 Tkinter 代码，仅保留参考 |
| `core/` | 旧版计算模块，已被 `server/core/` 替代 |
| `assets/` | 旧版 3D 场景 HTML |
| `docs/` | 设计文档与实施计划 |
| `ai_suggestions/` | AI 审计报告 |
| `CLAUDE.md` | Claude Code 配置文件，与运行无关 |
| `*.db` | 项目数据库文件，运行时自动生成 |
| `projects/` | 运行时自动创建 |
| `project_full_data.json` | 旧 JSON 数据，已废弃 |

---

## 在另一台电脑上运行

### 第一步：安装 Python 依赖

目标电脑需要安装 **Python 3.10+**。

```bash
pip install -r requirements.txt
```

### 第二步：启动

```bash
python start.py
```

浏览器打开 **http://localhost:8000**。

### 第三步（可选）：修改前端后重新构建

目标电脑需要安装 **Node.js 18+**。

```bash
cd client
npm install
npm run build
cd ..
```

> 已包含 `client/dist/` 则可跳过此步。

---

## 首次使用流程

1. 打开浏览器 → 看到 **项目选择页面**
2. 点击 **新建项目** 或选择已有项目 → 点击 **进入**
3. 在 **数据管理** 页：
   - 上传地勘 Excel 文件（如 `地勘报告修改版.xlsx`）
   - 上传桩基 Excel 文件（如 `西地块地下室桩基施工图.xlsx`）
   - 设置持力层（从下拉列表中选择，如 `65粉砂（持力层）`）
   - 点击 **应用**
4. 切换到 **3D 视图** → 查看桩基 + 土层分段着色
5. 点击任意桩 → 底部显示详细信息

---

## 注意事项

- 同一台电脑可运行多个项目，数据互相隔离
- 项目数据存储在 `projects/<id>.db` 中，可备份/删除
- 首次启动自动创建"默认项目"（空数据）
- 关闭命令行窗口即停止服务
