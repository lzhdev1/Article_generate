"use client"

import { useEffect, useState } from "react"
import { useParams, useRouter } from "next/navigation"
import { motion } from "framer-motion"
import { Check, Loader2 } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { StepIndicator } from "@/components/ui/step-indicator"
import { LoadingSpinner } from "@/components/ui/loading"

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api"

interface Title { content: string; style: string; reasoning: string }

const styleLabels: Record<string, string> = {
  trend_list: "数字列表型", question: "问题引导型", authority: "权威专业型",
  emotional: "情感共鸣型", contrast: "对比冲突型", comprehensive: "全面解析型", general: "通用型",
}

export default function TitlesPage() {
  const params = useParams()
  const router = useRouter()
  const projectId = params.id as string
  const [titles, setTitles] = useState<Title[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null)
  const [isConfirming, setIsConfirming] = useState(false)

  useEffect(() => {
    ;(async () => {
      try {
        const res = await fetch(`${API}/projects/${projectId}/workflow/state`)
        if (res.ok) {
          const data = await res.json()
          setTitles(data.data?.titles || [])
        }
      } catch {}
      setIsLoading(false)
    })()
  }, [projectId])

  // 纯本地选择，不调用API
  const handleSelect = (index: number) => {
    setSelectedIndex(index)
  }

  // 确认后调用API，保存到标题并跳转到大纲配置页面
  const handleConfirm = async () => {
    if (selectedIndex === null) return

    setIsConfirming(true)
    try {
      const res = await fetch(`${API}/projects/${projectId}/workflow/select-title`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: titles[selectedIndex].content }),
      })

      if (!res.ok) throw new Error("保存标题失败")

      // 跳转到大纲配置页面（大纲还未生成，需要用户先填写配置）
      router.push(`/project/${projectId}/outline-config`)
    } catch (err) {
      console.error(err)
      alert(err instanceof Error ? err.message : "发生错误")
    } finally {
      setIsConfirming(false)
    }
  }

  const steps = [
    { id: "title", label: "标题", status: "current" },
    { id: "outline", label: "大纲", status: "upcoming" },
    { id: "config", label: "配置", status: "upcoming" },
    { id: "generate", label: "生成", status: "upcoming" },
  ]

  if (isLoading) return <div className="flex min-h-screen items-center justify-center"><LoadingSpinner size="lg" /></div>

  return (
    <div className="min-h-screen bg-grid">
      <div className="pointer-events-none fixed inset-0 bg-mesh" />
      <div className="relative z-10 mx-auto max-w-4xl px-4 py-8">
        <StepIndicator steps={steps} className="mb-8" />
        <div className="mb-8 text-center">
          <h1 className="text-3xl font-bold text-foreground">请选择一个标题</h1>
          <p className="mt-2 text-muted-foreground">基于已提取的知识，为您生成了{titles.length}个候选标题</p>
        </div>

        <div className="space-y-4">
          {titles.map((title, index) => (
            <motion.div key={index} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: index * 0.1 }}>
              <Card className={`cursor-pointer transition-all duration-300 ${selectedIndex === index ? "border-primary bg-primary/5 shadow-lg shadow-primary/20" : "hover:border-primary/30 hover:shadow-md"}`}
                onClick={() => handleSelect(index)}
              >
                <CardContent className="p-6">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 flex items-start gap-3">
                      <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/10 text-sm font-bold text-primary">{index + 1}</span>
                      <div>
                        <div className="flex items-center gap-2">
                          <h3 className="text-xl font-semibold text-foreground">{title.content}</h3>
                          {selectedIndex === index && <Check className="h-5 w-5 text-accent" />}
                        </div>
                        <div className="mt-2">
                          <span className="inline-block rounded-full bg-muted px-3 py-1 text-xs font-medium text-muted-foreground">{styleLabels[title.style] || title.style}</span>
                          <p className="mt-2 text-sm text-muted-foreground">{title.reasoning}</p>
                        </div>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </div>

        {titles.length === 0 && (
          <div className="py-20 text-center">
            <p className="text-muted-foreground">没有找到标题数据</p>
            <Button variant="outline" className="mt-4" onClick={() => router.push("/")}>返回首页</Button>
          </div>
        )}

        {/* 确认按钮 */}
        {selectedIndex !== null && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="mt-8 flex justify-center"
          >
            <Button size="lg" onClick={handleConfirm} disabled={isConfirming} className="px-8">
              {isConfirming ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  处理中...
                </>
              ) : (
                "确认选择，继续下一步"
              )}
            </Button>
          </motion.div>
        )}
      </div>
    </div>
  )
}
