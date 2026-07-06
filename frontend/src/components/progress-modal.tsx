/**
 * 进度弹窗组件
 * 支持三种模式：标题生成、大纲生成、文章生成
 */

import { motion, AnimatePresence } from "framer-motion"
import { IconCheck, IconLoading, IconCircle } from "@/components/icons"

// 步骤定义
export const TITLE_STEPS = [
  { key: "search", label: "搜索相关内容", description: "正在搜索网络内容作为参考...", estimatedTime: "15-30 秒" },
  { key: "filter", label: "过滤相关内容", description: "筛选博客类型的相关内容...", estimatedTime: "5-10 秒" },
  { key: "extract", label: "提取知识", description: "从搜索结果中提取知识...", estimatedTime: "10-20 秒" },
  { key: "generate", label: "生成标题", description: "生成候选标题...", estimatedTime: "20-40 秒" },
]

export const OUTLINE_STEPS = [
  { key: "crawl", label: "爬取文章", description: "爬取与主题相关的文章...", estimatedTime: "10-20 秒" },
  { key: "analyze_structure", label: "分析提纲", description: "分析文章的提纲和风格...", estimatedTime: "10-15 秒" },
  { key: "analyze_content", label: "分析内容", description: "深入分析文章内容...", estimatedTime: "10-20 秒" },
  { key: "generate", label: "生成大纲", description: "生成优质文章大纲...", estimatedTime: "20-30 秒" },
]

export const ARTICLE_STEPS = [
  { key: "search", label: "搜索相关内容", description: "搜索与标题和大纲相关的内容...", estimatedTime: "15-30 秒" },
  { key: "analyze", label: "分析内容", description: "分析搜索到的内容...", estimatedTime: "10-20 秒" },
  { key: "generate", label: "生成文章", description: "撰写文章内容...", estimatedTime: "60-90 秒" },
]

// 步骤状态映射
export const TITLE_STATUS_MAP: Record<string, number> = {
  starting: 0,
  search_completed: 1,
  filter_completed: 2,
  extract_completed: 3,
  title_generated: 4,
  wait_title_selection: 4,
}

export const OUTLINE_STATUS_MAP: Record<string, number> = {
  starting: 0,
  outline_config_set: 0,
  crawl_completed: 1,
  analyze_completed: 2,
  outline_generated: 3,
  wait_outline_selection: 3,
}

export const ARTICLE_STATUS_MAP: Record<string, number> = {
  starting: 0,
  article_config_set: 0,
  search_completed: 1,
  article_generated: 2,
  verification_completed: 2,
  verification_failed: 2,
  completed: 3,
}

type StepList = typeof TITLE_STEPS | typeof OUTLINE_STEPS | typeof ARTICLE_STEPS

interface ProgressModalProps {
  isOpen: boolean
  mode: "title" | "outline" | "article"
  currentStep: number
  status: "running" | "completed" | "failed"
  message?: string
  topic?: string
}

export function ProgressModal({
  isOpen,
  mode,
  currentStep,
  status,
  message,
  topic,
}: ProgressModalProps) {
  // 根据模式选择步骤列表
  const steps: StepList = mode === "title" ? TITLE_STEPS : mode === "outline" ? OUTLINE_STEPS : ARTICLE_STEPS

  // 模式标题
  const modeTitle = mode === "title" ? "生成标题" : mode === "outline" ? "生成大纲" : "生成文章"
  const modeDescription = mode === "title" ? "搜索内容并生成候选标题" : mode === "outline" ? "分析内容并生成文章大纲" : "撰写完整文章内容"

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-center justify-center p-4"
        >
          {/* 背景遮罩 - 点击不关闭 */}
          <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" />

          {/* 弹窗内容 */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            transition={{ type: "spring", duration: 0.5 }}
            className="relative w-full max-w-lg rounded-2xl border border-border bg-white p-6 shadow-2xl"
          >
            {/* 标题 */}
            <div className="mb-6">
              <h2 className="text-xl font-bold text-foreground">正在{modeTitle}</h2>
              {topic && (
                <p className="mt-1 text-sm text-muted-foreground">
                  主题：{topic}
                </p>
              )}
              <p className="mt-2 text-xs text-muted-foreground">{modeDescription}</p>
            </div>

            {/* 步骤列表 */}
            <div className="space-y-3">
              {steps.map((step, index) => {
                const stepDone = index < currentStep
                const stepActive = index === currentStep && status === "running"
                const stepPending = index > currentStep

                return (
                  <motion.div
                    key={step.key}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: index * 0.1 }}
                    className={`flex items-start gap-3 rounded-lg p-3 transition-all ${
                      stepActive ? "bg-primary/5" :
                      stepDone ? "bg-accent/5" :
                      "opacity-40"
                    }`}
                  >
                    {/* 状态图标 */}
                    <div className="shrink-0 mt-0.5">
                      {stepDone ? (
                        <IconCheck className="h-5 w-5 text-accent" />
                      ) : stepActive ? (
                        <IconLoading className="h-5 w-5 animate-spin text-primary" />
                      ) : (
                        <IconCircle className="h-5 w-5 text-muted-foreground/30" />
                      )}
                    </div>

                    {/* 内容 */}
                    <div className="flex-1">
                      <p className={`text-sm font-medium ${
                        stepPending ? "text-muted-foreground" : "text-foreground"
                      }`}>
                        {step.label}
                      </p>
                      <p className="mt-1 text-xs text-muted-foreground">
                        {step.description}
                      </p>

                      {/* 预估时间 */}
                      {stepActive && (
                        <p className="mt-2 text-xs text-primary/70">
                          预计需要 {step.estimatedTime}，请耐心等待...
                        </p>
                      )}
                    </div>

                    {/* 完成标记 */}
                    {stepDone && (
                      <span className="shrink-0 text-xs font-medium text-accent">
                        完成
                      </span>
                    )}
                  </motion.div>
                )
              })}
            </div>

            {/* 底部状态 */}
            <div className="mt-6 border-t border-border pt-4">
              {status === "running" && (
                <div className="flex items-center justify-center gap-2 text-sm text-muted-foreground">
                  <IconLoading className="h-4 w-4 animate-spin text-primary" />
                  <span>{currentStep < steps.length ? steps[currentStep].description : "正在处理中..."}</span>
                </div>
              )}

              {status === "completed" && (
                <motion.p
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="text-center text-sm font-medium text-accent"
                >
                  {mode === "title" ? "标题生成完成！即将跳转..." :
                   mode === "outline" ? "大纲生成完成！即将跳转..." :
                   "文章生成完成！即将展示..."}
                </motion.p>
              )}

              {status === "failed" && (
                <motion.p
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="text-center text-sm text-error"
                >
                  {message || "生成失败，请重试"}
                </motion.p>
              )}
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
