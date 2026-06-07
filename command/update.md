---
description: 检查 deep-research skill 是否有新版本可用，并执行更新
---

<command-instruction>
你是一个版本检查工具。任务是检查 deep-research skill 的本地版本是否落后于远程版本，如有更新则执行拉取。

## 检查流程

### Step 1 — 定位 skill 目录

通过以下路径查找 skill 目录：
- `find ~/.opencode/skills -name "VERSION" -path "*/deep-research/*"`
- `find ~/.config/opencode/skills -name "VERSION" -path "*/deep-research/*"`
- 或检查当前工作目录是否就是 skill 根目录（存在 VERSION 文件）

### Step 2 — 读取本地版本

读取 `VERSION` 文件内容获取版本号。如果找不到 → 提示"找不到 deep-research skill 目录"，给出手动克隆命令后退出。

### Step 3 — 获取远程版本

`webfetch(url="https://raw.githubusercontent.com/hoolulu/deep-research/main/VERSION")`
提取内容中的版本号。如果网络不可用 → 提示"无法连接到远程仓库，请检查网络"后退出。

### Step 4 — 比较版本

版本号格式为 `X.Y.Z`，逐段比较（major.minor.patch）：
- 本地 < 远程 → 提示有更新，展示 git log 最近几条记录作为更新说明，询问用户是否要更新
- 本地 >= 远程 → 提示已是最新
- 版本号格式无法解析 → 提示退出

### Step 5 — 执行更新（用户确认后）

先检测目录是否为 git 仓库（存在 `.git` 目录）：

**有 `.git` 的情况**：
1. 先 `git stash` 暂存本地修改（避免 pull 冲突）
2. `git pull` 拉取最新代码
3. 如果 stash 成功，`git stash pop` 恢复本地修改
4. 如有冲突 → 提示用户手动解决后重试

**无 `.git` 的情况**：
1. 用 `git clone https://github.com/hoolulu/deep-research.git {tmp_dir}` 克隆到临时目录
2. 将克隆内容复制到 skill 目录覆盖旧文件
3. 删除临时目录

**更新完成后**：
- 读取新 VERSION 文件确认更新后的版本号
- 提示用户重启 OpenCode 使改动生效（如有 Scrapling MCP 变更）

### 输出示例

```
当前版本：2.1.0
远程版本：2.2.0

📦 有新版本可用！最近更新：
- 修复目录生成规则
- 优化数据池结构

是否执行更新？[y/N]
```

更新完成后：

```
[✓] 已更新到 v2.2.0
ℹ️ 请重启 OpenCode 使更改生效（如有 MCP 变更）
```
</command-instruction>

<user-request>
$ARGUMENTS
</user-request>
