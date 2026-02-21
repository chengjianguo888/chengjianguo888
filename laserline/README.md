# LaserLine — 激光条纹中心线检测软件

全新独立开发的激光条纹中心线检测软件，基于 **Python 3 + PyQt5 + OpenCV + Matplotlib**。

---

## 项目结构

```
laserline/
├── app.py                  # 应用程序入口
├── __main__.py             # python -m laserline 支持
├── config.py               # 配置持久化（JSON）
├── requirements.txt        # 依赖清单
├── detection/
│   └── engine.py           # 检测引擎（4种算法 + 批量处理）
├── io/
│   ├── loader.py           # 图像加载器
│   └── exporter.py         # 数据导出（CSV / Excel / JSON）
├── ui/
│   ├── mainwindow.py       # 主窗口
│   ├── panels.py           # 控制面板组件
│   ├── widgets.py          # 可复用控件（缩放标签/Matplotlib画布）
│   └── batch_dialog.py     # 批量处理对话框
└── tests/
    └── test_detection.py   # 单元测试
```

---

## 安装

```bash
pip install -r laserline/requirements.txt
```

---

## 启动

```bash
# 方式一
python laserline/app.py

# 方式二（从仓库根目录）
python -m laserline
```

---

## 功能特点

### 检测算法（4种）
| 算法 | 说明 |
|------|------|
| 灰度重心法 | 灰度加权平均，鲁棒性强，适合大多数场景 |
| 高斯拟合法 | 对灰度分布拟合高斯函数，精度高 |
| 极值法 | 取每列最大值，速度最快 |
| Steger 亚像素法 | 基于 Hessian 特征值分析，亚像素级精度 |

### 图像预处理（4种滤波 + CLAHE）
- 高斯滤波 / 中值滤波 / 双边滤波 / 不滤波
- CLAHE 自适应对比度增强
- Otsu 自动阈值（或手动设置固定阈值）

### GUI 界面
- 深色主题
- 选项卡：图像视图 / 坐标折线图 / Y 分布直方图
- 鼠标滚轮缩放 + 双击重置
- 后台线程检测（UI 完全不卡顿）
- 检测统计面板（点数、Y min/max/mean/std、耗时）
- 实时检测模式（参数变化后 700ms 自动触发）
- 配置自动持久化（记忆上次使用的参数）

### 批量处理
- 选择目录，自动扫描所有图像
- 后台批量检测
- 自动导出汇总 Excel 报告 + 每张图的 CSV 文件

### 数据导出（3种格式）
- **CSV** — UTF-8-BOM，可直接用 Excel 打开
- **Excel (.xlsx)** — 含"坐标数据"和"统计信息"两个工作表
- **JSON** — 含坐标列表和统计摘要

---

## 运行测试

```bash
python -m pytest laserline/tests/ -v
# 或
python laserline/tests/test_detection.py
```

---

## 快捷键

| 操作 | 快捷键 |
|------|--------|
| 打开图像 | Ctrl+O |
| 批量处理 | Ctrl+B |
| 保存结果图像 | Ctrl+S |
| 导出 CSV | Ctrl+E |
| 导出 Excel | Ctrl+Shift+E |
| 导出 JSON | Ctrl+Shift+J |
| 放大 | Ctrl+= |
| 缩小 | Ctrl+- |
| 重置缩放 | Ctrl+0 |
| 退出 | Ctrl+Q |
