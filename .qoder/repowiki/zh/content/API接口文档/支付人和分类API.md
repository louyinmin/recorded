# 支付人和分类API

<cite>
**本文档引用的文件**
- [app.py](file://app.py)
- [common.js](file://assets/js/common.js)
- [settings.js](file://assets/js/settings.js)
- [settings.html](file://settings.html)
- [trip.js](file://assets/js/trip.js)
- [trip.html](file://trip.html)
- [recorded.md](file://recorded.md)
</cite>

## 更新摘要
**变更内容**
- 新增密码管理API端点 `/api/password` 的完整文档
- 更新认证机制说明，包含密码文件持久化
- 新增设置页面的前端实现细节
- 完善API接口说明，包含密码修改的完整流程

## 目录
1. [简介](#简介)
2. [项目结构](#项目结构)
3. [核心组件](#核心组件)
4. [架构概览](#架构概览)
5. [详细组件分析](#详细组件分析)
6. [依赖关系分析](#依赖关系分析)
7. [性能考虑](#性能考虑)
8. [故障排除指南](#故障排除指南)
9. [结论](#结论)

## 简介

recorded是一个基于Flask的旅游记账系统，提供了完整的支付人和分类管理API。该系统支持多旅行记账、自动数据去重、唯一性约束保证，以及与记账记录API的紧密协同工作。系统采用SQLite作为数据存储，实现了数据一致性保证和自动维护机制。

根据项目描述，系统主要面向旅游记账场景，支持交通工具、住宿、餐费、打车等默认分类，同时允许用户自定义分类和支付人。**新增功能**包括密码管理API，支持用户修改登录密码，并通过文件持久化机制确保密码更改的持久性。

## 项目结构

项目采用前后端分离的架构设计，主要文件组织如下：

```mermaid
graph TB
subgraph "后端 (Python Flask)"
APP[app.py<br/>主应用文件]
DB[(data.db<br/>SQLite数据库)]
PASS[(.password<br/>密码文件)]
end
subgraph "前端 (静态资源)"
HTML[HTML页面]
CSS[CSS样式]
JS[JavaScript文件]
end
subgraph "前端JavaScript模块"
COMMON[common.js<br/>API封装和工具函数]
SETTINGS[settings.js<br/>设置页面逻辑]
TRIP[trip.js<br/>旅行页面逻辑]
END
HTML --> JS
JS --> COMMON
JS --> SETTINGS
JS --> TRIP
COMMON --> APP
SETTINGS --> APP
TRIP --> APP
APP --> DB
APP --> PASS
```

**图表来源**
- [app.py:13-152](file://app.py#L13-L152)
- [common.js:1-239](file://assets/js/common.js#L1-L239)
- [settings.js:1-235](file://assets/js/settings.js#L1-L235)

**章节来源**
- [app.py:1-515](file://app.py#L1-L515)
- [recorded.md:1-9](file://recorded.md#L1-L9)

## 核心组件

### 数据库架构

系统使用SQLite作为数据存储，包含以下核心表结构：

```mermaid
erDiagram
PAYERS {
INTEGER id PK
TEXT name UK
}
CATEGORIES {
INTEGER id PK
TEXT name UK
}
TRIPS {
TEXT id PK
TEXT name
TEXT start_date
TEXT end_date
TEXT note
TEXT created_at
}
RECORDS {
TEXT id PK
TEXT trip_id FK
TEXT category
REAL amount
TEXT payer
TEXT date
TEXT note
}
PAYERS ||--o{ RECORDS : "used by"
CATEGORIES ||--o{ RECORDS : "categorized by"
TRIPS ||--o{ RECORDS : "contains"
```

**图表来源**
- [app.py:85-92](file://app.py#L85-L92)

### 默认分类初始化

系统在数据库初始化时自动创建默认分类，确保用户首次使用时有预设的分类选项：

- 交通工具（飞机/动车/自驾）
- 住宿  
- 餐费
- 打车

### 密码管理机制

**新增功能**：系统支持密码管理，包含以下特性：

- **密码文件持久化**：使用`.password`文件保存修改后的密码
- **动态密码获取**：优先从文件读取密码，回退到固定密码
- **安全验证**：登录时验证用户名和密码组合
- **密码修改**：支持用户修改登录密码

**章节来源**
- [app.py:18-42](file://app.py#L18-L42)
- [app.py:138-152](file://app.py#L138-L152)
- [app.py:43-98](file://app.py#L43-L98)

## 架构概览

系统采用RESTful API设计，前后端通过JSON进行数据交换。认证采用简单的token机制，所有API请求都需要携带Authorization头。**新增密码管理流程**如下：

```mermaid
sequenceDiagram
participant Client as 客户端
participant API as API服务器
participant DB as SQLite数据库
participant Auth as 认证服务
Client->>Auth : POST /api/login (用户名密码)
Auth->>Auth : 验证凭据从密码文件读取
Auth-->>Client : 返回token
Client->>API : POST /api/password (带token)
API->>Auth : 验证token
Auth-->>API : 验证通过
API->>API : 验证原密码
API->>API : 写入新密码到文件
API-->>Client : 成功响应
Client->>API : GET /api/payers (带token)
API->>Auth : 验证token
Auth-->>API : 验证通过
API->>DB : 查询支付人列表
DB-->>API : 返回支付人数据
API-->>Client : 支付人列表JSON
```

**图表来源**
- [app.py:126-152](file://app.py#L126-L152)
- [app.py:313-330](file://app.py#L313-L330)

## 详细组件分析

### 支付人管理API

#### GET /api/payers - 获取支付人列表

**功能描述**: 返回系统中所有已注册的支付人列表，按ID升序排列。

**请求参数**: 无

**响应数据**: 字符串数组，包含所有支付人姓名

**响应示例**:
```json
[
  "张三",
  "李四", 
  "王五"
]
```

**错误处理**: 
- 401 未登录或登录已过期
- 500 数据库查询异常

#### POST /api/payers - 创建支付人

**功能描述**: 创建新的支付人，使用INSERT OR IGNORE确保数据去重。

**请求参数**:
```json
{
  "name": "新支付人姓名"
}
```

**响应数据**:
```json
{
  "ok": true
}
```

**数据去重机制**:
系统使用SQLite的UNIQUE约束和INSERT OR IGNORE语句实现自动去重：
- UNIQUE约束防止重复姓名插入
- INSERT OR IGNORE跳过重复条目，避免抛出异常
- 保证支付人列表的唯一性和完整性

**错误处理**:
- 400 姓名不能为空
- 401 未登录或登录已过期
- 500 数据库操作异常

#### PUT /api/payers/<name> - 更新支付人

**功能描述**: 更新现有支付人的姓名，包含重复性检查和记录同步。

**请求参数**:
```json
{
  "name": "新支付人姓名"
}
```

**同步机制**:
- 检查新名称是否已存在
- 更新支付人名称
- 同步更新相关记录中的支付人字段

**错误处理**:
- 400 姓名不能为空或已存在
- 404 支付人不存在
- 401 未登录或登录已过期
- 500 数据库操作异常

#### DELETE /api/payers/<name> - 删除支付人

**功能描述**: 删除指定的支付人。

**错误处理**:
- 404 支付人不存在
- 401 未登录或登录已过期
- 500 数据库操作异常

**章节来源**
- [app.py:313-362](file://app.py#L313-L362)

### 分类管理API

#### GET /api/categories - 获取分类列表

**功能描述**: 返回系统中所有已注册的分类列表，按ID升序排列。

**请求参数**: 无

**响应数据**: 字符串数组，包含所有分类名称

**响应示例**:
```json
[
  "交通工具（飞机/动车/自驾）",
  "住宿",
  "餐费",
  "打车",
  "购物"
]
```

**错误处理**:
- 401 未登录或登录已过期
- 500 数据库查询异常

#### POST /api/categories - 创建分类

**功能描述**: 创建新的分类，使用INSERT OR IGNORE确保数据去重。

**请求参数**:
```json
{
  "name": "新分类名称"
}
```

**响应数据**:
```json
{
  "ok": true
}
```

**数据去重机制**:
与支付人类似，系统使用UNIQUE约束和INSERT OR IGNORE实现自动去重：
- UNIQUE约束确保分类名称唯一
- INSERT OR IGNORE处理重复插入请求
- 保持分类列表的完整性和一致性

**错误处理**:
- 400 分类名称不能为空
- 401 未登录或登录已过期
- 500 数据库操作异常

#### PUT /api/categories/<name> - 更新分类

**功能描述**: 更新现有分类的名称，包含重复性检查和记录同步。

**请求参数**:
```json
{
  "name": "新分类名称"
}
```

**同步机制**:
- 检查新名称是否已存在
- 更新分类名称
- 同步更新相关记录中的分类字段

**错误处理**:
- 400 分类名称不能为空或已存在
- 404 分类不存在
- 401 未登录或登录已过期
- 500 数据库操作异常

#### DELETE /api/categories/<name> - 删除分类

**功能描述**: 删除指定的分类。

**错误处理**:
- 404 分类不存在
- 401 未登录或登录已过期
- 500 数据库操作异常

**章节来源**
- [app.py:366-415](file://app.py#L366-L415)

### 密码管理API

#### POST /api/password - 修改密码

**功能描述**: 修改用户的登录密码，支持密码验证和持久化。

**请求参数**:
```json
{
  "oldPassword": "用户原密码",
  "newPassword": "新密码"
}
```

**验证规则**:
- 原密码必须正确
- 新密码长度至少3位
- 新密码不能为空

**持久化机制**:
- 将新密码写入`.password`文件
- 下次登录时从文件读取密码
- 失败时回退到固定密码

**响应数据**:
```json
{
  "ok": true
}
```

**错误处理**:
- 400 请填写完整或新密码至少3位或原密码错误
- 401 未登录或登录已过期
- 500 文件写入或数据库操作异常

**章节来源**
- [app.py:138-152](file://app.py#L138-L152)

### 与记账记录API的协同工作

系统中的记账记录API会自动维护支付人和分类的完整性：

```mermaid
sequenceDiagram
participant Client as 客户端
participant API as 记账API
participant DB as 数据库
Client->>API : POST /api/trips/{trip_id}/records
API->>API : 验证记录数据
API->>DB : 插入记账记录
API->>DB : INSERT OR IGNORE payers (自动维护)
API->>DB : INSERT OR IGNORE categories (自动维护)
DB-->>API : 操作完成
API-->>Client : 返回记录ID
Note over API,DB : 自动维护机制
API->>DB : 每次创建/更新记录时
API->>DB : 自动同步支付人和分类
```

**图表来源**
- [app.py:245-273](file://app.py#L245-L273)
- [app.py:275-301](file://app.py#L275-L301)

**章节来源**
- [app.py:245-273](file://app.py#L245-L273)
- [app.py:275-301](file://app.py#L275-L301)

## 依赖关系分析

### 前端集成

前端JavaScript通过统一的API封装层与后端交互，**新增设置页面**：

```mermaid
graph LR
subgraph "前端模块"
COMMON[common.js<br/>API封装]
SETTINGS[settings.js<br/>设置页面逻辑]
TRIP[trip.js<br/>页面逻辑]
HTML[trip.html<br/>页面结构]
SETTINGS_HTML[settings.html<br/>设置页面结构]
end
subgraph "后端API"
LOGIN[POST /api/login]
PASSWORD[POST /api/password]
PAYERS[GET/POST/PAYERS]
CATS[GET/POST/CATEGORIES]
RECORDS[POST /api/trips/{trip_id}/records]
END
COMMON --> LOGIN
COMMON --> PASSWORD
COMMON --> PAYERS
COMMON --> CATS
COMMON --> RECORDS
SETTINGS --> COMMON
SETTINGS_HTML --> SETTINGS
TRIP --> COMMON
HTML --> TRIP
```

**图表来源**
- [common.js:153-158](file://assets/js/common.js#L153-L158)
- [settings.js:123-151](file://assets/js/settings.js#L123-L151)

### 数据流分析

系统中的数据流向体现了完整的业务流程，**新增密码管理流程**：

```mermaid
flowchart TD
START[用户操作] --> LOAD[加载数据]
LOAD --> PAYERS[获取支付人列表]
LOAD --> CATEGORIES[获取分类列表]
LOAD --> RECORDS[获取记账记录]
PAYERS --> RENDER[渲染下拉框]
CATEGORIES --> RENDER
RENDER --> ADD[添加新记录]
ADD --> VALIDATE[验证数据]
VALIDATE --> SUCCESS{验证通过?}
SUCCESS --> |是| INSERT[插入记录]
SUCCESS --> |否| ERROR[显示错误]
INSERT --> SYNC[同步支付人/分类]
SYNC --> REFRESH[刷新页面]
REFRESH --> END[完成]
ERROR --> END
```

**图表来源**
- [settings.js:27-37](file://assets/js/settings.js#L27-L37)
- [settings.js:123-151](file://assets/js/settings.js#L123-L151)

**章节来源**
- [common.js:153-158](file://assets/js/common.js#L153-L158)
- [settings.js:123-151](file://assets/js/settings.js#L123-L151)

## 性能考虑

### 数据库优化

1. **索引策略**: 使用UNIQUE约束确保查询效率
2. **事务处理**: 所有数据库操作都在单个事务中执行
3. **连接池**: 使用Flask的g对象管理数据库连接
4. **WAL模式**: 启用Write-Ahead Logging提高并发性能

### 前端性能

1. **批量加载**: 使用Promise.all并行加载多个API请求
2. **本地缓存**: 支付人和分类数据在页面内缓存
3. **防抖处理**: 表单提交时禁用按钮防止重复提交
4. **增量更新**: 只在必要时刷新页面内容

### 密码管理性能

1. **文件I/O优化**: 密码文件读写采用异步方式
2. **缓存机制**: 登录时验证密码，减少文件读取次数
3. **错误处理**: 密码文件损坏时自动回退到固定密码

## 故障排除指南

### 常见问题及解决方案

#### 1. 认证失败
**症状**: 请求返回401状态码
**原因**: Token无效或已过期
**解决**: 重新登录获取新Token

#### 2. 数据重复插入
**症状**: POST请求返回成功但数据未更新
**原因**: 使用INSERT OR IGNORE处理重复数据
**解决**: 确保请求体包含正确的name字段

#### 3. 数据库锁定
**症状**: 请求超时或操作失败
**原因**: SQLite并发访问冲突
**解决**: 等待当前事务完成或重启应用

#### 4. 前端数据不同步
**症状**: 新增的支付人或分类未显示
**原因**: 前端缓存未刷新
**解决**: 刷新页面或调用refresh()方法

#### 5. 密码修改失败
**症状**: POST /api/password返回错误
**原因**: 原密码错误或新密码不符合要求
**解决**: 检查原密码是否正确，新密码长度至少3位

#### 6. 密码文件权限问题
**症状**: 无法修改密码或密码丢失
**原因**: .password文件权限不足或被删除
**解决**: 检查文件权限，确保应用有读写权限

**章节来源**
- [app.py:102-109](file://app.py#L102-L109)
- [app.py:145-152](file://app.py#L145-L152)
- [common.js:59-67](file://assets/js/common.js#L59-L67)

## 结论

recorded项目的支付人和分类管理API设计合理，实现了以下关键特性：

1. **数据完整性**: 通过UNIQUE约束和INSERT OR IGNORE确保数据唯一性
2. **自动维护**: 与记账记录API紧密集成，自动同步支付人和分类信息
3. **用户体验**: 前后端分离架构提供流畅的交互体验
4. **扩展性**: 支持自定义分类和支付人，满足多样化需求
5. **安全性**: **新增密码管理功能**，支持用户修改登录密码并持久化保存
6. **健壮性**: 密码文件损坏时自动回退到固定密码，确保系统可用性

系统采用简洁有效的技术方案，在保证功能完整性的同时保持了代码的可维护性。**新增的密码管理功能**进一步提升了系统的安全性和用户体验。建议在生产环境中考虑添加更完善的错误日志和监控机制，以进一步提升系统的可靠性。