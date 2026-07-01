# Spec-003: 首页与Topic输入

## 1. 功能概述

首页是用户进入系统的第一个页面，承担以下职责：
- 展示品牌形象（LOGO + 项目名称）
- 提供Topic输入框
- 用户输入后启动文章生成流程

设计要求：简约科技风格，内容垂直水平居中，给用户留下良好的第一印象。

---

## 2. 技术选型

| 技术 | 用途 |
|------|------|
| Next.js App Router | 页面路由 |
| React Hook Form | 表单处理 |
| Zod | 输入校验 |
| Framer Motion | 入场动画 |
| Zustand | 项目状态管理 |

---

## 3. UI设计

### 3.1 页面布局

```
┌──────────────────────────────────────────────────────────────────┐
│                                                                    │
│                                                                    │
│                                                                    │
│                                                                    │
│                      ┌──────────────────┐                          │
│                      │   ✦ Article      │                          │
│                      │     Generate     │                          │
│                      │                  │                          │
│                      │  AI驱动的智能     │                          │
│                      │  博客文章生成平台 │                          │
│                      └──────────────────┘                          │
│                                                                    │
│                 ┌──────────────────────────────┐                   │
│                 │  🔍 请输入你的文章内容需求    │  [开始生成]       │
│                 └──────────────────────────────┘                   │
│                                                                    │
│                      示例: AI在教育领域的应用                       │
│                                                                    │
│                                                                    │
│                                                                    │
│                                                                    │
│                                                                    │
│                    ─────────────────────────                       │
│                     由阿里云百炼提供AI能力                          │
└──────────────────────────────────────────────────────────────────┘
```

### 3.2 视觉设计说明

| 元素 | 规格 |
|------|------|
| LOGO区域 | 项目名称 "Article Generate"，使用渐变色文字 |
| 副标题 | "AI驱动的智能博客文章生成平台"，中性色小字 |
| 输入框 | 宽度 max-w-2xl (672px)，圆角 xl，高度 h-14 |
| 按钮 | 渐变背景，圆角 xl，高度 h-14 |
| 示例提示 | 可点击的标签，点击后填入输入框 |
| 背景 | 网格线 + 渐变光效（全局设计系统） |
| 底部 | 技术提供方说明 |

### 3.3 交互设计

1. **页面加载**：内容渐入动画（fadeIn + slideUp）
2. **输入框聚焦**：边框变为主色，轻微放大阴影
3. **按钮Hover**：渐变色加深，阴影增强
4. **按钮点击**：缩放效果 + loading状态
5. **输入校验**：Topic长度2-200字符
6. **提交后**：loading动画 → 跳转至搜索进度页面

---

## 4. 数据模型设计

### 4.1 输入数据

```typescript
// frontend/src/types/topic.ts

export interface TopicInput {
  topic: string;
}

export interface TopicFormData {
  topic: string;
}

// 输入校验Schema
import { z } from 'zod';

export const topicSchema = z.object({
  topic: z
    .string()
    .min(2, '请输入至少2个字符')
    .max(200, '请输入不超过200个字符')
    .trim(),
});

export type TopicValidation = z.infer<typeof topicSchema>;
```

### 4.2 API响应

```typescript
// 创建项目响应
export interface CreateProjectResponse {
  project_id: string;
  topic: string;
  status: string;
  created_at: string;
}
```

---

## 5. API设计

### 5.1 创建项目接口

```
POST /api/projects
```

**Request Body:**
```json
{
  "topic": "AI在教育领域的应用"
}
```

**Response 201:**
```json
{
  "project_id": "550e8400-e29b-41d4-a716-446655440000",
  "topic": "AI在教育领域的应用",
  "status": "init",
  "created_at": "2024-01-01T00:00:00Z"
}
```

**Response 400:**
```json
{
  "detail": "Topic长度不符合要求"
}
```

### 5.2 后端实现

```python
# backend/app/api/endpoints/project.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.database import get_db
from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectResponse

router = APIRouter()

class TopicInput(BaseModel):
    topic: str = Field(..., min_length=2, max_length=200, description="文章主题")

@router.post("/projects", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    input: TopicInput,
    db: AsyncSession = Depends(get_db)
):
    """创建新项目"""
    project = Project(
        topic=input.topic,
        status="init"
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)
    
    return ProjectResponse(
        project_id=str(project.id),
        topic=project.topic,
        status=project.status,
        created_at=project.created_at.isoformat()
    )
```

---

## 6. 代码实现

### 6.1 首页组件

```tsx
// frontend/src/app/page.tsx

"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { motion } from "framer-motion"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { Sparkles, ArrowRight, Loader2 } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { topicSchema, type TopicValidation } from "@/types/topic"
import { api } from "@/services/api"
import { useProjectStore } from "@/stores/projectStore"
import { cn } from "@/lib/utils"

// 示例Topics
const exampleTopics = [
  "AI在教育领域的应用",
  "2024年最值得学习的编程语言",
  "远程办公的最佳实践",
  "可持续发展的商业模式",
]

// 动画变体
const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.15,
      delayChildren: 0.2,
    },
  },
}

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.5, ease: [0.4, 0, 0.2, 1] },
  },
}

export default function HomePage() {
  const router = useRouter()
  const [isSubmitting, setIsSubmitting] = useState(false)
  const { setProject } = useProjectStore()

  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors },
  } = useForm<TopicValidation>({
    resolver: zodResolver(topicSchema),
  })

  const onSubmit = async (data: TopicValidation) => {
    setIsSubmitting(true)
    try {
      const response = await api.project.create(data.topic)
      setProject(response)
      router.push(`/project/${response.project_id}/processing`)
    } catch (error) {
      console.error("Failed to create project:", error)
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleExampleClick = (topic: string) => {
    setValue("topic", topic)
  }

  return (
    <div className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden px-4">
      {/* 背景装饰 */}
      <div className="pointer-events-none absolute inset-0">
        {/* 渐变光圈 */}
        <div className="absolute left-1/2 top-1/4 h-[500px] w-[500px] -translate-x-1/2 rounded-full bg-primary-500/10 blur-[100px]" />
        <div className="absolute bottom-1/4 right-1/4 h-[300px] w-[300px] rounded-full bg-accent-500/10 blur-[80px]" />
      </div>

      <motion.div
        className="relative z-10 flex w-full max-w-2xl flex-col items-center"
        variants={containerVariants}
        initial="hidden"
        animate="visible"
      >
        {/* LOGO区域 */}
        <motion.div variants={itemVariants} className="mb-8 text-center">
          <div className="mb-4 flex items-center justify-center gap-2">
            <Sparkles className="h-8 w-8 text-primary-500" />
            <h1 className="bg-gradient-to-r from-primary-500 via-primary-600 to-accent-500 bg-clip-text text-5xl font-bold text-transparent">
              Article Generate
            </h1>
          </div>
          <p className="text-lg text-neutral-500">
            AI驱动的智能博客文章生成平台
          </p>
        </motion.div>

        {/* 输入表单 */}
        <motion.form
          variants={itemVariants}
          onSubmit={handleSubmit(onSubmit)}
          className="w-full"
        >
          <div className="flex gap-3">
            <div className="flex-1">
              <Input
                {...register("topic")}
                placeholder="请输入你的文章内容需求"
                error={errors.topic?.message}
                disabled={isSubmitting}
                className="h-14 text-lg"
              />
            </div>
            <Button
              type="submit"
              size="xl"
              isLoading={isSubmitting}
              className="shrink-0"
            >
              {isSubmitting ? (
                <Loader2 className="mr-2 h-5 w-5 animate-spin" />
              ) : (
                <>
                  开始生成
                  <ArrowRight className="ml-2 h-5 w-5" />
                </>
              )}
            </Button>
          </div>
        </motion.form>

        {/* 示例提示 */}
        <motion.div variants={itemVariants} className="mt-6">
          <p className="mb-3 text-center text-sm text-neutral-400">
            试试这些示例：
          </p>
          <div className="flex flex-wrap justify-center gap-2">
            {exampleTopics.map((topic) => (
              <button
                key={topic}
                type="button"
                onClick={() => handleExampleClick(topic)}
                className={cn(
                  "rounded-full border border-neutral-200 bg-white/50 px-4 py-1.5",
                  "text-sm text-neutral-600 backdrop-blur-sm",
                  "transition-all duration-200",
                  "hover:border-primary-300 hover:bg-primary-50 hover:text-primary-600",
                  "active:scale-95"
                )}
              >
                {topic}
              </button>
            ))}
          </div>
        </motion.div>
      </motion.div>

      {/* 底部信息 */}
      <motion.div
        className="absolute bottom-8 text-center"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1, duration: 0.5 }}
      >
        <p className="text-sm text-neutral-400">
          由阿里云百炼提供AI能力支持
        </p>
      </motion.div>
    </div>
  )
}
```

### 6.2 API服务

```typescript
// frontend/src/services/api.ts

import axios from 'axios';
import type { CreateProjectResponse } from '@/types/topic';

const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
});

// 请求拦截器
apiClient.interceptors.request.use((config) => {
  return config;
});

// 响应拦截器
apiClient.interceptors.response.use(
  (response) => response.data,
  (error) => {
    console.error('API Error:', error);
    return Promise.reject(error);
  }
);

export const api = {
  project: {
    create: async (topic: string): Promise<CreateProjectResponse> => {
      return apiClient.post('/projects', { topic });
    },
    get: async (projectId: string) => {
      return apiClient.get(`/projects/${projectId}`);
    },
  },
};
```

### 6.3 状态管理

```typescript
// frontend/src/stores/projectStore.ts

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface Project {
  project_id: string;
  topic: string;
  status: string;
  created_at: string;
}

interface ProjectState {
  currentProject: Project | null;
  setProject: (project: Project) => void;
  clearProject: () => void;
}

export const useProjectStore = create<ProjectState>()(
  persist(
    (set) => ({
      currentProject: null,
      setProject: (project) => set({ currentProject: project }),
      clearProject: () => set({ currentProject: null }),
    }),
    {
      name: 'article-generator-project',
    }
  )
);
```

---

## 7. 路由设计

```
/                          → 首页（Topic输入）
/project/[id]/processing   → 处理进度页面
/project/[id]/titles       → 标题选择页面
/project/[id]/outline      → 大纲配置页面
/project/[id]/outlines     → 大纲选择页面
/project/[id]/config       → 最终配置页面
/project/[id]/article      → 文章展示页面
```

---

## 8. 错误处理

### 8.1 输入校验错误

| 错误 | 提示信息 |
|------|----------|
| 输入为空 | "请输入文章主题" |
| 长度不足 | "请输入至少2个字符" |
| 超出长度 | "请输入不超过200个字符" |

### 8.2 API错误处理

```typescript
// frontend/src/services/errorHandler.ts

export class ApiError extends Error {
  constructor(
    public status: number,
    public message: string,
    public code?: string
  ) {
    super(message);
  }
}

export function handleApiError(error: unknown): string {
  if (error instanceof ApiError) {
    switch (error.status) {
      case 400:
        return '请求参数错误，请检查输入';
      case 401:
        return '请登录后再试';
      case 429:
        return '请求过于频繁，请稍后再试';
      case 500:
        return '服务器错误，请稍后再试';
      default:
        return error.message || '未知错误';
    }
  }
  
  if (error instanceof TypeError && error.message.includes('fetch')) {
    return '网络连接失败，请检查网络';
  }
  
  return '发生未知错误，请重试';
}
```

---

## 9. 性能优化

1. **代码分割**：首页组件独立chunk
2. **图片优化**：使用 next/image 优化Logo
3. **字体优化**：使用 next/font 预加载字体
4. **输入防抖**：输入校验使用防抖处理
5. **静态生成**：首页可SSG预渲染

---

## 10. 验收标准

### 10.1 功能验收

- [ ] 页面正常加载，无控制台错误
- [ ] LOGO和项目名称正确显示
- [ ] 输入框可正常输入文字
- [ ] 示例标签可点击并填入输入框
- [ ] 提交按钮点击后进入loading状态
- [ ] 提交成功后跳转至进度页面
- [ ] 输入校验正确（空值、长度）
- [ ] 错误信息正确显示

### 10.2 UI验收

- [ ] 内容垂直水平居中
- [ ] 渐变色文字效果正常
- [ ] 背景网格和光效正常显示
- [ ] 按钮hover/active效果正常
- [ ] 入场动画流畅

### 10.3 响应式验收

- [ ] 移动端 (375px) 布局正确，输入框和按钮垂直排列
- [ ] 平板 (768px) 布局正确
- [ ] 桌面 (1280px+) 布局正确

### 10.4 兼容性验收

- [ ] Chrome 最新版正常
- [ ] Safari 最新版正常
- [ ] Firefox 最新版正常
- [ ] Edge 最新版正常
