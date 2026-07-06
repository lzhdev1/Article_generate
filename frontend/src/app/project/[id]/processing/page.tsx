"use client"

import { useEffect, useState, useRef } from "react"
import { useParams, useRouter } from "next/navigation"
import { motion } from "framer-motion"
import { CheckCircle, Loader2, Circle, AlertCircle } from "lucide-react"

// 主节点和子步骤定义
const MAIN_NODES = [
  {
    key: "title_generate",
    label: "标题生成",
    subSteps: [
      { key: "search", label: "搜索相关内容" },
      { key: "filter", label: "筛选文章内容" },
      { key: "analyze", label: "分析搜索结果" },
      { key: "generate", label: "生成候选标题" },
    ],
  },
  {
    key: "outline_generate",
    label: "大纲生成",
    subSteps: [
      { key: "search", label: "分析标题和配置" },
      { key: "extract", label: "提取文章结构" },
      { key: "analyze", label: "生成专业提示词" },
      { key: "generate", label: "生成大纲" },
    ],
  },
  {
    key: "final_config",
    label: "最终配置",
    subSteps: [{ key: "config", label: "填写文章配置" }],
  },
  {
    key: "article_generate",
    label: "文章生成",
    subSteps: [
      { key: "match_evidence", label: "分析证据需求" },
      { key: "search", label: "搜索相关内容" },
      { key: "generate", label: "生成文章" },
    ],
  },
]

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api"

interface ProgressState {
  [mainNode: string]: {
    [subStep: string]: "pending" | "running" | "completed"
  }
}

export default function ProcessingPage() {
  const params = useParams()
  const router = useRouter()
  const projectId = params.id as string
  const [progress, setProgress] = useState<ProgressState>({})
  const [status, setStatus] = useState<"running" | "completed" | "failed">("running")
  const [message, setMessage] = useState("正在启动工作流...")
  const [topic, setTopic] = useState("")
  const eventSourceRef = useRef<EventSource | null>(null)

  useEffect(() => {
    // 获取项目信息
    ;(async () => {
      try {
        const res = await fetch(`${API}/projects/${projectId}`)
        if (res.ok) {
          const data = await res.json()
          setTopic(data.topic)
        }
      } catch {}
    })()

    // 使用 SSE 接收进度事件
    const eventSource = new EventSource(`${API}/projects/${projectId}/workflow/start-stream`)
    eventSourceRef.current = eventSource

    // 监听 progress 事件
    eventSource.addEventListener("progress", (event) => {
      try {
        const data = JSON.parse(event.data)
        const mainNode = data.main_node
        const subStep = data.sub_step
        const timestamp = new Date().toISOString()

        console.log(`[SSE] Received progress event at ${timestamp}:`, { mainNode, subStep, message: data.message })

        // 更新进度状态
        setProgress((prev) => {
          const newProgress = { ...prev }
          if (!newProgress[mainNode]) {
            newProgress[mainNode] = {}
          }

          // 将当前子步骤标记为完成
          newProgress[mainNode][subStep] = "completed"

          // 找到下一个子步骤并标记为运行中
          const mainNodeDef = MAIN_NODES.find((n) => n.key === mainNode)
          if (mainNodeDef) {
            const subStepIndex = mainNodeDef.subSteps.findIndex((s) => s.key === subStep)
            if (subStepIndex < mainNodeDef.subSteps.length - 1) {
              const nextSubStep = mainNodeDef.subSteps[subStepIndex + 1].key
              newProgress[mainNode][nextSubStep] = "running"
            }
          }

          console.log(`[SSE] Updated progress state:`, newProgress)
          return newProgress
        })

        setMessage(data.message || "处理中...")
      } catch (e) {
        console.error("Failed to parse progress event:", e)
      }
    })

    // 监听 completed 事件
    eventSource.addEventListener("completed", (event) => {
      try {
        const data = JSON.parse(event.data)
        setStatus("completed")
        setMessage("标题生成完成！即将跳转...")
        eventSource.close()
        setTimeout(() => router.push(`/project/${projectId}/titles`), 1500)
      } catch (e) {
        console.error("Failed to parse completed event:", e)
      }
    })

    // 监听 error 事件（来自服务器的工作流错误）
    eventSource.addEventListener("error", (event) => {
      try {
        const data = JSON.parse(event.data)
        setStatus("failed")
        setMessage(data.message || "工作流出错")
        eventSource.close()
      } catch (e) {
        console.error("Failed to parse error event:", e)
      }
    })

    // 连接错误（网络问题等）
    eventSource.onerror = () => {
      if (eventSource.readyState === EventSource.CLOSED) {
        return // 正常关闭
      }
      setStatus("failed")
      setMessage("连接中断，请刷新页面重试")
      eventSource.close()
    }

    // 清理
    return () => {
      eventSource.close()
    }
  }, [projectId])

  return (
    <div className="relative flex min-h-screen flex-col items-center justify-center bg-grid">
      <div className="pointer-events-none fixed inset-0 bg-mesh" />

      <motion.div className="relative z-10 w-full max-w-2xl px-4" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
        <div className="mb-10 text-center">
          <h1 className="text-2xl font-bold text-foreground">正在处理</h1>
          {topic && <p className="mt-2 text-muted-foreground">主题：{topic}</p>}
        </div>

        <div className="space-y-6">
          {MAIN_NODES.map((mainNode, mainIndex) => {
            const mainProgress = progress[mainNode.key] || {}
            const hasStarted = Object.keys(mainProgress).length > 0
            const allCompleted = mainNode.subSteps.every((s) => mainProgress[s.key] === "completed")
            const isRunning = hasStarted && !allCompleted

            return (
              <motion.div
                key={mainNode.key}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: mainIndex * 0.1 }}
                className={`rounded-xl border p-5 transition-all ${
                  isRunning ? "border-primary bg-primary/5" : allCompleted ? "border-accent/30 bg-accent/5" : "border-border bg-white"
                }`}
              >
                <div className="mb-3 flex items-center gap-3">
                  <div className="shrink-0">
                    {allCompleted ? (
                      <CheckCircle className="h-5 w-5 text-accent" />
                    ) : isRunning ? (
                      <Loader2 className="h-5 w-5 animate-spin text-primary" />
                    ) : (
                      <Circle className="h-5 w-5 text-muted-foreground/30" />
                    )}
                  </div>
                  <h3 className={`font-semibold ${!hasStarted ? "text-muted-foreground" : "text-foreground"}`}>
                    {mainNode.label}
                  </h3>
                  {allCompleted && <span className="ml-auto text-xs font-medium text-accent">完成</span>}
                </div>

                {hasStarted && (
                  <div className="ml-8 space-y-2">
                    {mainNode.subSteps.map((subStep) => {
                      const subStatus = mainProgress[subStep.key] || "pending"
                      return (
                        <div key={subStep.key} className="flex items-center gap-2 text-sm">
                          {subStatus === "completed" ? (
                            <CheckCircle className="h-4 w-4 text-accent" />
                          ) : subStatus === "running" ? (
                            <Loader2 className="h-4 w-4 animate-spin text-primary" />
                          ) : (
                            <Circle className="h-4 w-4 text-muted-foreground/30" />
                          )}
                          <span className={subStatus === "pending" ? "text-muted-foreground" : "text-foreground"}>
                            {subStep.label}
                          </span>
                        </div>
                      )
                    })}
                  </div>
                )}
              </motion.div>
            )
          })}
        </div>

        {status === "failed" && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="mt-6 flex items-center gap-2 rounded-xl border border-error/30 bg-error/5 p-4">
            <AlertCircle className="h-5 w-5 text-error" />
            <p className="text-sm text-error">{message}</p>
          </motion.div>
        )}

        {status === "completed" && (
          <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="mt-6 text-center text-sm text-accent">
            即将跳转到标题选择页面...
          </motion.p>
        )}
      </motion.div>
    </div>
  )
}
