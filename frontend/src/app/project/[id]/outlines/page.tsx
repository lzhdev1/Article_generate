"use client"

import { useEffect, useState } from "react"
import { useParams, useRouter } from "next/navigation"
import { motion } from "framer-motion"
import { Check, Loader2, FileText, ChevronDown, ChevronUp } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle, CardFooter } from "@/components/ui/card"
import { StepIndicator } from "@/components/ui/step-indicator"
import { LoadingSpinner } from "@/components/ui/loading"
import { cn } from "@/lib/utils"

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api"

interface Section {
  heading: string
  description: string
  subtopics: string[]
  word_count: number
}

interface Outline {
  content: { title: string; sections: Section[] }
  reasoning: string
  style: string
}

const styleLabels: Record<string, string> = {
  comprehensive: "全面系统型",
  problem_solution: "问题-解决型",
  step_by_step: "循序渐进型",
  comparison: "对比分析型",
  case_study: "案例分析型",
  general: "通用型",
}

export default function OutlinesPage() {
  const params = useParams()
  const router = useRouter()
  const projectId = params.id as string
  const [outlines, setOutlines] = useState<Outline[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [selectingIndex, setSelectingIndex] = useState<number | null>(null)
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null)
  const [expandedId, setExpandedId] = useState<number | null>(null)

  useEffect(() => {
    loadOutlines()
  }, [projectId])

  const loadOutlines = async () => {
    try {
      const res = await fetch(`${API_URL}/projects/${projectId}/workflow/state`)
      if (res.ok) {
        const data = await res.json()
        setOutlines(data.data?.outlines || [])
      }
    } catch (err) {
      console.error(err)
    } finally {
      setIsLoading(false)
    }
  }

  const handleSelect = async (outline: Outline, index: number) => {
    setSelectingIndex(index)
    try {
      const res = await fetch(`${API_URL}/projects/${projectId}/workflow/select-outline`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ outline }),
      })

      if (res.ok) {
        setSelectedIndex(index)
        setTimeout(() => {
          router.push(`/project/${projectId}/config`)
        }, 1000)
      }
    } catch (err) {
      console.error(err)
      setSelectingIndex(null)
    }
  }

  const steps = [
    { id: "search", label: "搜索", status: "completed" },
    { id: "filter", label: "过滤", status: "completed" },
    { id: "extract", label: "提取", status: "completed" },
    { id: "title", label: "标题", status: "completed" },
    { id: "outline", label: "大纲", status: "current" },
    { id: "config", label: "配置", status: "upcoming" },
    { id: "generate", label: "生成", status: "upcoming" },
  ]

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-grid">
      <div className="pointer-events-none fixed inset-0 bg-mesh" />

      <div className="relative z-10 mx-auto max-w-6xl px-4 py-8">
        <StepIndicator steps={steps} className="mb-8" />

        <div className="mb-8 text-center">
          <h1 className="text-3xl font-bold text-foreground">请选择一个大纲</h1>
          <p className="mt-2 text-muted-foreground">为您生成了{outlines.length}个不同风格的大纲</p>
        </div>

        <div className={cn("grid gap-6", outlines.length >= 3 ? "md:grid-cols-3" : "md:grid-cols-2")}>
          {outlines.map((outline, index) => {
            const sections = outline.content?.sections || []

            return (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
              >
                <Card
                  className={cn(
                    "flex h-full flex-col transition-all duration-300",
                    selectedIndex === index
                      ? "border-primary bg-primary/5 shadow-lg shadow-primary/20"
                      : "hover:border-primary/30 hover:shadow-md"
                  )}
                >
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-lg">方案 {String.fromCharCode(65 + index)}</CardTitle>
                      <span className="rounded-full bg-muted px-3 py-1 text-xs font-medium">
                        {styleLabels[outline.style] || outline.style}
                      </span>
                    </div>
                  </CardHeader>

                  <CardContent className="flex-1">
                    <div className="space-y-3">
                      {sections.map((section, sIndex) => (
                        <div key={sIndex} className="flex items-start gap-3">
                          <FileText className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
                          <div className="flex-1">
                            <p className="text-sm font-medium text-foreground">{section.heading}</p>
                            <p className="text-xs text-muted-foreground">约{section.word_count}字</p>
                          </div>
                        </div>
                      ))}
                    </div>

                    <button
                      onClick={() => setExpandedId(expandedId === index ? null : index)}
                      className="mt-4 flex items-center gap-1 text-sm text-primary hover:text-primary-600"
                    >
                      {expandedId === index ? (
                        <>收起 <ChevronUp className="h-4 w-4" /></>
                      ) : (
                        <>查看详情 <ChevronDown className="h-4 w-4" /></>
                      )}
                    </button>

                    {expandedId === index && (
                      <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: "auto", opacity: 1 }}
                        className="mt-3 space-y-3 border-t pt-3"
                      >
                        {sections.map((section, sIndex) => (
                          <div key={sIndex}>
                            <p className="text-sm font-medium">{section.heading}</p>
                            <p className="text-xs text-muted-foreground">{section.description}</p>
                            {section.subtopics?.length > 0 && (
                              <div className="mt-1 flex flex-wrap gap-1">
                                {section.subtopics.map((t, tIndex) => (
                                  <span key={tIndex} className="rounded bg-muted px-2 py-0.5 text-xs text-muted-foreground">
                                    {t}
                                  </span>
                                ))}
                              </div>
                            )}
                          </div>
                        ))}
                        <div className="border-t pt-3">
                          <p className="text-sm font-medium">设计思路</p>
                          <p className="text-xs text-muted-foreground">{outline.reasoning}</p>
                        </div>
                      </motion.div>
                    )}
                  </CardContent>

                  <CardFooter>
                    <Button
                      className="w-full"
                      variant={selectedIndex === index ? "default" : "outline"}
                      onClick={() => handleSelect(outline, index)}
                      disabled={selectingIndex !== null}
                    >
                      {selectingIndex === index ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : selectedIndex === index ? (
                        <>
                          <Check className="mr-2 h-4 w-4" />
                          已选择
                        </>
                      ) : (
                        "选择此大纲"
                      )}
                    </Button>
                  </CardFooter>
                </Card>
              </motion.div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
