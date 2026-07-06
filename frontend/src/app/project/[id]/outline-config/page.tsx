"use client"

import { useState } from "react"
import { useParams, useRouter } from "next/navigation"
import { motion } from "framer-motion"
import { ArrowLeft, ArrowRight, Loader2 } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { StepIndicator } from "@/components/ui/step-indicator"
import { ProgressModal, OUTLINE_STATUS_MAP } from "@/components/progress-modal"
import { cn } from "@/lib/utils"

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api"

const WORD_COUNT_OPTIONS = [
  { value: 1000, label: "短文", desc: "~1000字" },
  { value: 2000, label: "标准", desc: "~2000字" },
  { value: 3000, label: "长文", desc: "~3000字" },
  { value: 5000, label: "深度长文", desc: "~5000字" },
]

const READABILITY_OPTIONS = [
  { value: "easy", label: "通俗易懂", emoji: "📗" },
  { value: "general", label: "一般水平", emoji: "📘" },
  { value: "moderate", label: "中等专业", emoji: "📙" },
  { value: "advanced", label: "专业深度", emoji: "📕" },
]

const TONE_OPTIONS = [
  { value: "casual", label: "轻松随意", emoji: "😎" },
  { value: "conversational", label: "对话式", emoji: "💬" },
  { value: "professional", label: "专业严谨", emoji: "👔" },
  { value: "formal", label: "正式学术", emoji: "🎓" },
  { value: "humorous", label: "幽默风趣", emoji: "😄" },
  { value: "authoritative", label: "权威指导", emoji: "🏆" },
]

const POV_OPTIONS = [
  { value: "first_person", label: "第一人称", example: "我认为..." },
  { value: "second_person", label: "第二人称", example: "你可以..." },
  { value: "third_person", label: "第三人称", example: "研究发现..." },
]

export default function OutlineConfigPage() {
  const params = useParams()
  const router = useRouter()
  const projectId = params.id as string
  const [isSubmitting, setIsSubmitting] = useState(false)

  const [wordCount, setWordCount] = useState(2000)
  const [readability, setReadability] = useState("general")
  const [tone, setTone] = useState("professional")
  const [pov, setPov] = useState("third_person")
  const [requirements, setRequirements] = useState("")
  const [showProgress, setShowProgress] = useState(false)
  const [outlineStep, setOutlineStep] = useState(0)
  const [progressStatus, setProgressStatus] = useState<"running" | "completed" | "failed">("running")
  const [progressMessage, setProgressMessage] = useState("")

  const handleSubmit = async () => {
    setIsSubmitting(true)
    setShowProgress(true)
    setProgressStatus("running")
    setOutlineStep(0)
    setProgressMessage("")

    try {
      // 保存配置
      const configRes = await fetch(`${API_URL}/projects/${projectId}/workflow/save-outline-config`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          outline_config: {
            word_count: wordCount,
            readability,
            tone_of_voice: tone,
            point_of_view: pov,
            additional_requirements: requirements,
          },
        }),
      })

      if (!configRes.ok) throw new Error("保存配置失败")

      // 轮询状态
      const pollInterval = setInterval(async () => {
        try {
          const res = await fetch(`${API_URL}/projects/${projectId}/workflow/state`)
          if (res.ok) {
            const data = await res.json()
            const stage = data.current_stage || "unknown"
            const idx = OUTLINE_STATUS_MAP[stage] ?? 0
            setOutlineStep(idx)

            if (stage === "outline_generated" || data.data?.outlines?.length > 0) {
              setProgressStatus("completed")
              setProgressMessage("大纲生成完成！")
              clearInterval(pollInterval)

              setTimeout(() => {
                setShowProgress(false)
                router.push(`/project/${projectId}/outlines`)
              }, 1500)
            }
          }
        } catch (err) {
          console.error(err)
        }
      }, 2000)

    } catch (err) {
      console.error(err)
      setProgressStatus("failed")
      setProgressMessage(err instanceof Error ? err.message : "发生错误")
    } finally {
      setIsSubmitting(false)
    }
  }

  const steps = [
    { id: "title", label: "标题", status: "completed" },
    { id: "outline", label: "大纲", status: "current" },
    { id: "config", label: "配置", status: "upcoming" },
    { id: "generate", label: "生成", status: "upcoming" },
  ]

  return (
    <div className="min-h-screen bg-grid">
      <div className="pointer-events-none fixed inset-0 bg-mesh" />

      <div className="relative z-10 mx-auto max-w-3xl px-4 py-8">
        <StepIndicator steps={steps} className="mb-8" />

        <div className="mb-8 text-center">
          <h1 className="text-3xl font-bold text-foreground">大纲生成配置</h1>
          <p className="mt-2 text-muted-foreground">填写以下需求，帮助我们生成最合适的大纲</p>
        </div>

        <div className="space-y-6">
          {/* 字数 */}
          <Card>
            <CardHeader><CardTitle className="text-lg">📝 文章字数</CardTitle></CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                {WORD_COUNT_OPTIONS.map((opt) => (
                  <button
                    key={opt.value}
                    onClick={() => setWordCount(opt.value)}
                    className={cn(
                      "rounded-xl border-2 p-4 text-center transition-all",
                      wordCount === opt.value
                        ? "border-primary bg-primary/5"
                        : "border-border hover:border-primary/30"
                    )}
                  >
                    <p className="font-medium">{opt.label}</p>
                    <p className="mt-1 text-xs text-muted-foreground">{opt.desc}</p>
                  </button>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* 可读性 */}
          <Card>
            <CardHeader><CardTitle className="text-lg">📖 可读性</CardTitle></CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-3">
                {READABILITY_OPTIONS.map((opt) => (
                  <button
                    key={opt.value}
                    onClick={() => setReadability(opt.value)}
                    className={cn(
                      "rounded-xl border-2 px-4 py-3 transition-all",
                      readability === opt.value
                        ? "border-primary bg-primary/5"
                        : "border-border hover:border-primary/30"
                    )}
                  >
                    <span className="mr-1">{opt.emoji}</span>
                    <span className="font-medium">{opt.label}</span>
                  </button>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* 语调 */}
          <Card>
            <CardHeader><CardTitle className="text-lg">🎭 语调/写作风格</CardTitle></CardHeader>
            <CardContent>
              <div className="grid grid-cols-3 gap-3 sm:grid-cols-6">
                {TONE_OPTIONS.map((opt) => (
                  <button
                    key={opt.value}
                    onClick={() => setTone(opt.value)}
                    className={cn(
                      "flex flex-col items-center rounded-xl border-2 p-3 transition-all",
                      tone === opt.value
                        ? "border-primary bg-primary/5"
                        : "border-border hover:border-primary/30"
                    )}
                  >
                    <span className="text-2xl">{opt.emoji}</span>
                    <span className="mt-1 text-xs font-medium">{opt.label}</span>
                  </button>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* 视角 */}
          <Card>
            <CardHeader><CardTitle className="text-lg">👤 人称视角</CardTitle></CardHeader>
            <CardContent>
              <div className="space-y-3">
                {POV_OPTIONS.map((opt) => (
                  <button
                    key={opt.value}
                    onClick={() => setPov(opt.value)}
                    className={cn(
                      "flex w-full items-center rounded-xl border-2 p-4 text-left transition-all",
                      pov === opt.value
                        ? "border-primary bg-primary/5"
                        : "border-border hover:border-primary/30"
                    )}
                  >
                    <div className="flex-1">
                      <p className="font-medium">{opt.label}</p>
                    </div>
                    <code className="text-xs text-muted-foreground">{opt.example}</code>
                  </button>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* 额外要求 */}
          <Card>
            <CardHeader><CardTitle className="text-lg">✨ 额外要求 (可选)</CardTitle></CardHeader>
            <CardContent>
              <textarea
                value={requirements}
                onChange={(e) => setRequirements(e.target.value)}
                placeholder="请输入您的额外要求..."
                className="min-h-[100px] w-full rounded-xl border border-border p-4 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
              />
            </CardContent>
          </Card>
        </div>

        {/* 按钮 */}
        <div className="mt-8 flex items-center justify-between">
          <Button variant="secondary" size="lg" onClick={() => router.back()}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            上一步
          </Button>
          <Button size="lg" onClick={handleSubmit} disabled={isSubmitting}>
            {isSubmitting ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                生成中...
              </>
            ) : (
              <>
                生成大纲
                <ArrowRight className="ml-2 h-4 w-4" />
              </>
            )}
          </Button>
        </div>
      </div>

      {/* 进度弹窗 */}
      <ProgressModal
        isOpen={showProgress}
        mode="outline"
        currentStep={outlineStep}
        status={progressStatus}
        message={progressMessage}
        topic={""}
      />
    </div>
  )
}
