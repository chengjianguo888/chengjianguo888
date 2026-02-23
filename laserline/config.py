# -*- coding: utf-8 -*-
"""
laserline.config — 用户配置持久化
自动读写 ~/.laserline_config.json，保存上次使用的参数设置。
"""

import json
import os
from typing import Any, Dict

_CONFIG_PATH = os.path.expanduser("~/.laserline_config.json")

# 默认设置
_DEFAULTS: Dict[str, Any] = {
    "algorithm": "gray_centroid",
    "filter_type": "gaussian",
    "kernel_size": 5,
    "threshold": 0,          # 0 = Otsu 自动
    "clahe": False,
    "line_color": [0, 220, 80],   # RGB
    "line_width": 2,
    "last_dir": "",
    "window_geometry": None,
    "show_statistics": True,
}


def load() -> Dict[str, Any]:
    """从磁盘加载配置，缺失键用默认值补全。"""
    cfg = dict(_DEFAULTS)
    try:
        if os.path.exists(_CONFIG_PATH):
            with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
                saved = json.load(f)
            cfg.update({k: saved[k] for k in saved if k in _DEFAULTS})
    except Exception:
        pass
    return cfg


def save(cfg: Dict[str, Any]) -> None:
    """将配置写入磁盘。"""
    try:
        with open(_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
