"use client"

import { useEffect, useState } from "react"
import { useParams, useRouter } from "next/navigation"
import { motion } from "framer-motion"
import { CheckCircle, Loader2, Circle, AlertCircle } from "lucide-react"

const STAGES = [
  { key: "search", label: "网络检索", description: "搜索相关内容" },
  { key: "filter", label: "内容过滤", description: "筛选相关文章" },
  { key: "extract", label: "知识提取", description: "提取关键知识" },
  { key: "title", label: "标题生成", description: "生成候选标题" },
]

const STAGE_INDEX: Record<string, number> = {
  starting: 0,
  search_completed: 1,
  filter_completed: 2,
  extract_completed: 3,
  title_generated: 4,
}

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api"

export default function ProcessingPage() {
  const params = useParams()
  const router = useRouter()
  const projectId = params.id as string
  const [currentStage, setCurrentStage] = useState(0)
  const [status, setStatus] = useState<"running" | "completed" | "failed">("running")
  const [message, setMessage] = useState("正在启动工作流...")
  const [topic, setTopic] = useState("")

  useEffect(() => {
    ;(async () => {
      // 获取项目信息
      try {
        const res = await fetch(`${API}/projects/${projectId}`)
        if (res.ok) {
          const data = await res.json()
          setTopic(data.topic)
        }
      } catch {}

      // 启动工作流
      try {
        const res = await fetch(`${API}/projects/${projectId}/workflow/start`, {
          method: "POST",
        })

        if (!res.ok) {
          const err = await res.json().catch(() => ({}))
          throw new Error(err.detail || "启动失败")
        }

        const data = await res.json()
        const stage = data.status || "starting"
        const idx = STAGE_INDEX[stage] ?? 4

        if (stage === "title_generated" || data.titles?.length > 0) {
          setCurrentStage(4)
          setStatus("completed")
          setMessage("标题生成完成！即将跳转...")
          setTimeout(() => router.push(`/project/${projectId}/titles`), 1500)
        } else {
          setCurrentStage(idx)
          setMessage(STAGES[Math.min(idx, STAGES.length - 1)]?.description || "处理中...")
        }
      } catch (err) {
        setStatus("failed")
        setMessage(err instanceof Error ? err.message : "启动失败，请检查API Key配置")
      }
    })()
  }, [projectId])

  return (
    <div className="relative flex min-h-screen flex-col items-center justify-center bg-grid">
      <div className="pointer-events-none fixed inset-0 bg-mesh" />

      <motion.div className="relative z-10 w-full max-w-lg px-4" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
        <div className="mb-10 text-center">
          <h1 className="text-2xl font-bold text-foreground">正在处理</h1>
          {topic && <p className="mt-2 text-muted-foreground">主题：{topic}</p>}
        </div>

        <div className="space-y-4">
          {STAGES.map((stage, index) => {
            const done = index < currentStage
            const active = index === currentStage && status === "running"
            return (
              <motion.div
                key={stage.key}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.1 }}
                className={`flex items-center gap-4 rounded-xl border p-4 transition-all ${
                  active ? "border-primary bg-primary/5" : done ? "border-accent/30 bg-accent/5" : "border-border bg-white"
                }`}
              >
                <div className="shrink-0">
                  {done ? <CheckCircle className="h-6 w-6 text-accent" /> : active ? <Loader2 className="h-6 w-6 animate-spin text-primary" /> : <Circle className="h-6 w-6 text-muted-foreground/30" />}
                </div>
                <div className="flex-1">
                  <p className={`font-medium ${index > currentStage ? "text-muted-foreground" : "text-foreground"}`}>{stage.label}</p>
                  <p className="text-sm text-muted-foreground">{active ? message : stage.description}</p>
                </div>
                {done && <span className="text-xs font-medium text-accent">完成</span>}
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
