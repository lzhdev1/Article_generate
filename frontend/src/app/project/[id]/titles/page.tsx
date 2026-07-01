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
  const [selectingIndex, setSelectingIndex] = useState<number | null>(null)
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null)

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

  const handleSelect = async (title: Title, index: number) => {
    setSelectingIndex(index)
    try {
      const res = await fetch(`${API}/projects/${projectId}/workflow/select-title`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: title.content }),
      })
      if (res.ok) {
        setSelectedIndex(index)
        setTimeout(() => router.push(`/project/${projectId}/outline-config`), 1000)
      }
    } catch (err) {
      console.error(err)
    }
    setSelectingIndex(null)
  }

  const steps = [
    { id: "search", label: "搜索", status: "completed" },
    { id: "filter", label: "过滤", status: "completed" },
    { id: "extract", label: "提取", status: "completed" },
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
              <Card className={`transition-all duration-300 ${selectedIndex === index ? "border-primary bg-primary/5 shadow-lg shadow-primary/20" : "hover:border-primary/30 hover:shadow-md"}`}>
                <CardContent className="p-6">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-3">
                        <span className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/10 text-sm font-bold text-primary">{index + 1}</span>
                        <h3 className="text-xl font-semibold text-foreground">{title.content}</h3>
                        {selectedIndex === index && <Check className="h-5 w-5 text-accent" />}
                      </div>
                      <div className="mt-3 ml-11">
                        <span className="inline-block rounded-full bg-muted px-3 py-1 text-xs font-medium text-muted-foreground">{styleLabels[title.style] || title.style}</span>
                        <p className="mt-2 text-sm text-muted-foreground">{title.reasoning}</p>
                      </div>
                    </div>
                    {selectedIndex === null && (
                      <Button variant="outline" onClick={() => handleSelect(title, index)} disabled={selectingIndex !== null} className="shrink-0">
                        {selectingIndex === index ? <Loader2 className="h-4 w-4 animate-spin" /> : "选择"}
                      </Button>
                    )}
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
      </div>
    </div>
  )
}
