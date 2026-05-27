# 桩基预测系统 — 部署与演示指南

## 在另一台电脑上运行

### 第一步：复制项目

将整个项目文件夹 `A桩基智能体` 复制到目标电脑（U盘、网盘或直接拷贝）。

### 第二步：安装 Python 依赖

目标电脑需要安装 **Python 3.10+**。

打开命令行（cmd 或 PowerShell），进入项目目录，运行：

```bash
pip install -r requirements.txt
```

如果项目中没有 `requirements.txt`，手动安装以下包：

```bash
pip install fastapi uvicorn sqlalchemy pandas numpy pykrige openpyxl python-multipart
```

### 第三步：构建前端（可选——如果只需演示已构建好的版本可跳过）

目标电脑需要安装 **Node.js 18+**。

```bash
cd client
npm install
npm run build
cd ..
```

> 如果项目已包含 `client/dist/` 目录（已构建好的前端），则**跳过此步**。

### 第四步：启动

```bash
python start.py
```

打开浏览器访问 **http://localhost:8000**。

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

## 文件说明

| 文件/目录 | 用途 |
|-----------|------|
| `start.py` | 一键启动脚本 |
| `server/` | FastAPI 后端代码 |
| `client/dist/` | 已构建的前端静态文件 |
| `projects/` | 项目数据库目录（自动创建） |
| `test_files/` | 测试数据文件（地勘+桩基Excel） |

---

## 注意事项

- 同一台电脑可运行多个项目，数据互相隔离
- 项目数据存储在 `projects/<id>.db` 中，可备份/删除
- 首次启动自动创建"默认项目"（空数据）
- 关闭命令行窗口即停止服务
