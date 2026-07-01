"use client"

import { useEffect, useState } from "react"
import { useParams, useRouter } from "next/navigation"
import { motion } from "framer-motion"
import { Sparkles, FileText, Shield, Check } from "lucide-react"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { StepIndicator } from "@/components/ui/step-indicator"
import { ProgressBar } from "@/components/ui/progress-bar"

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api"

export default function GeneratingPage() {
  const params = useParams()
  const router = useRouter()
  const projectId = params.id as string
  const [progress, setProgress] = useState(0)
  const [status, setStatus] = useState<"generating" | "verifying" | "completed">("generating")

  useEffect(() => {
    // 文章生成已在config页面触发，这里只轮询状态
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`${API_URL}/projects/${projectId}/workflow/state`)
        if (res.ok) {
          const data = await res.json()
          const stage = data.data?.current_stage
          if (stage === "completed" || stage === "verification_completed") {
            clearInterval(interval)
            setStatus("completed")
            setProgress(100)
            setTimeout(() => router.push(`/project/${projectId}/article`), 1500)
          } else if (stage === "verification_failed") {
            clearInterval(interval)
            setProgress(95)
          } else {
            setProgress(Math.min(90, progress + 5))
          }
        }
      } catch (err) {
        console.error(err)
      }
    }, 3000)

    return () => clearInterval(interval)
  }, [projectId, progress])

  const steps = [
    { id: "search", label: "搜索", status: "completed" },
    { id: "filter", label: "过滤", status: "completed" },
    { id: "extract", label: "提取", status: "completed" },
    { id: "title", label: "标题", status: "completed" },
    { id: "outline", label: "大纲", status: "completed" },
    { id: "config", label: "配置", status: "completed" },
    { id: "generate", label: "生成", status: "current" },
  ]

  return (
    <div className="min-h-screen bg-grid">
      <div className="pointer-events-none fixed inset-0 bg-mesh" />

      <div className="relative z-10 mx-auto max-w-3xl px-4 py-8">
        <StepIndicator steps={steps} className="mb-8" />

        {/* 中央动画 */}
        <div className="mb-8 flex flex-col items-center">
          <motion.div animate={{ rotate: 360 }} transition={{ duration: 2, repeat: Infinity, ease: "linear" }}>
            <Sparkles className="h-16 w-16 text-primary" />
          </motion.div>
          <h1 className="mt-4 text-2xl font-bold text-foreground">
            {status === "generating" && "正在生成文章"}
            {status === "verifying" && "正在验证内容"}
            {status === "completed" && "文章生成完成！"}
          </h1>
          <p className="mt-2 text-muted-foreground">
            {status === "generating" && "AI正在根据您的大纲撰写文章..."}
            {status === "verifying" && "AI正在验证文章中的事实和数据..."}
            {status === "completed" && "即将跳转到文章页面..."}
          </p>
        </div>

        {/* 进度 */}
        <Card className="mb-6">
          <CardContent className="p-6">
            <ProgressBar value={progress} label="生成进度" variant={status === "completed" ? "success" : "gradient"} />
          </CardContent>
        </Card>

        {/* 步骤 */}
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <FileText className="h-5 w-5 text-primary" />
                内容生成
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <Step label="收集参考资料" done={true} />
                <Step label="逐章节撰写内容" done={progress > 30} active={progress <= 80} />
                <Step label="生成要点总结与FAQ" done={progress > 80} />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <Shield className="h-5 w-5 text-primary" />
                内容验证
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <Step label="事实可靠性检查" done={status !== "generating"} active={status === "verifying"} />
                <Step label="信息时效性检查" done={status === "completed"} />
                <Step label="内容真实性检查" done={status === "completed"} />
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}

function Step({ label, done, active }: { label: string; done: boolean; active?: boolean }) {
  return (
    <div className="flex items-center gap-2 text-sm">
      {done ? (
        <Check className="h-4 w-4 text-accent" />
      ) : active ? (
        <div className="h-4 w-4 animate-pulse rounded-full border-2 border-primary" />
      ) : (
        <div className="h-4 w-4 rounded-full border-2 border-border" />
      )}
      <span className={done ? "text-foreground" : "text-muted-foreground"}>{label}</span>
    </div>
  )
}
