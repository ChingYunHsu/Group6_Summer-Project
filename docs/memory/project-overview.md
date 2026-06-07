# ClearPath 项目概览

## 基本信息
- **项目名称**: ClearPath
- **目标**: 为行动不便人群提供曼哈顿无障碍设施导航
- **数据范围**: 仅曼哈顿区

## 技术栈
- **后端**: Flask (Python)
- **数据库**: MySQL (clearpath)
- **前端**: 待确认

## 仓库结构
```
src/
├── app.py              # Flask 应用入口
├── main.py             # 主程序
├── settings.py         # 配置管理
├── mock_data.py        # 模拟数据
└── api/
    ├── health.py       # 健康检查
    ├── venues.py       # 场馆 API
    ├── reports.py      # 用户报告
    └── insights.py     # 洞察分析

Data+ML/
└── test/6.2-6.5_DB/
    ├── database_build.ipynb      # ETL 流程
    └── 001_clearpath_schema.sql  # 数据库 Schema
```

## 数据库连接
- **Host**: 127.0.0.1:3306
- **User**: clearpath_app
- **Password**: clearpath_app
- **Database**: clearpath

## 主要表
| 表名 | 用途 |
|------|------|
| venues | 核心场馆表 |
| restroom_profiles | 卫生间信息 |
| healthcare_profiles | 医疗设施 |
| emergency_assets | AED 设备 |
| pedestrian_ramps | 行人坡道 |
| user_reports | 用户报告 |
| venue_language | 语言支持 |

## 当前分支
- `main`: 主分支
- `alex`: 开发分支
