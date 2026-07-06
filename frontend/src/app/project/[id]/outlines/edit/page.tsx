"use client"

import { useEffect, useState } from "react"
import { useParams, useRouter } from "next/navigation"
import { motion } from "framer-motion"
import { ArrowLeft, ArrowRight, Plus, Trash2, GripVertical, Loader2, Check } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
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

export default function OutlineEditPage() {
  const params = useParams()
  const router = useRouter()
  const projectId = params.id as string
  const [outline, setOutline] = useState<Outline | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)

  useEffect(() => {
    loadOutline()
  }, [projectId])

  const loadOutline = async () => {
    try {
      // 先从 sessionStorage 读取（用户从选择页面带来的数据）
      const stored = sessionStorage.getItem(`outline-edit-${projectId}`)
      if (stored) {
        setOutline(JSON.parse(stored))
        return
      }
      // 否则从后端状态读取
      const res = await fetch(`${API_URL}/projects/${projectId}/workflow/state`)
      if (res.ok) {
        const data = await res.json()
        setOutline(data.data?.selected_outline || null)
      }
    } catch (err) {
      console.error(err)
    } finally {
      setIsLoading(false)
    }
  }

  const updateSection = (index: number, field: keyof Section, value: string | number | string[]) => {
    if (!outline) return
    const newSections = [...outline.content.sections]
    newSections[index] = { ...newSections[index], [field]: value }
    setOutline({ ...outline, content: { ...outline.content, sections: newSections } })
  }

  const updateSubtopic = (sIndex: number, tIndex: number, value: string) => {
    if (!outline) return
    const newSections = [...outline.content.sections]
    const newSubtopics = [...newSections[sIndex].subtopics]
    newSubtopics[tIndex] = value
    newSections[sIndex] = { ...newSections[sIndex], subtopics: newSubtopics }
    setOutline({ ...outline, content: { ...outline.content, sections: newSections } })
  }

  const addSubtopic = (sIndex: number) => {
    if (!outline) return
    const newSections = [...outline.content.sections]
    newSections[sIndex] = { ...newSections[sIndex], subtopics: [...newSections[sIndex].subtopics, ""] }
    setOutline({ ...outline, content: { ...outline.content, sections: newSections } })
  }

  const removeSubtopic = (sIndex: number, tIndex: number) => {
    if (!outline) return
    const newSections = [...outline.content.sections]
    newSections[sIndex] = { ...newSections[sIndex], subtopics: newSections[sIndex].subtopics.filter((_, i) => i !== tIndex) }
    setOutline({ ...outline, content: { ...outline.content, sections: newSections } })
  }

  const addSection = () => {
    if (!outline) return
    const newSection: Section = { heading: "", description: "", subtopics: [], word_count: 300 }
    setOutline({ ...outline, content: { ...outline.content, sections: [...outline.content.sections, newSection] } })
  }

  const removeSection = (index: number) => {
    if (!outline) return
    setOutline({ ...outline, content: { ...outline.content, sections: outline.content.sections.filter((_, i) => i !== index) } })
  }

  const moveSection = (from: number, to: number) => {
    if (!outline || to < 0 || to >= outline.content.sections.length) return
    const newSections = [...outline.content.sections]
    const [item] = newSections.splice(from, 1)
    newSections.splice(to, 0, item)
    setOutline({ ...outline, content: { ...outline.content, sections: newSections } })
  }

  const handleSave = async () => {
    if (!outline) return
    setIsSaving(true)
    try {
      const res = await fetch(`${API_URL}/projects/${projectId}/workflow/select-outline`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ outline }),
      })
      if (res.ok) {
        sessionStorage.removeItem(`outline-edit-${projectId}`)
        router.push(`/project/${projectId}/config`)
      }
    } catch (err) {
      console.error(err)
    } finally {
      setIsSaving(false)
    }
  }

  const steps = [
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

  if (!outline) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-center">
          <p className="text-muted-foreground">未找到大纲数据</p>
          <Button variant="outline" className="mt-4" onClick={() => router.back()}>返回</Button>
        </div>
      </div>
    )
  }

  const sections = outline.content.sections || []
  const totalWords = sections.reduce((sum, s) => sum + (s.word_count || 0), 0)

  return (
    <div className="min-h-screen bg-grid">
      <div className="pointer-events-none fixed inset-0 bg-mesh" />

      <div className="relative z-10 mx-auto max-w-3xl px-4 py-8">
        <StepIndicator steps={steps} className="mb-8" />

        <div className="mb-8 text-center">
          <h1 className="text-3xl font-bold text-foreground">编辑大纲</h1>
          <p className="mt-2 text-muted-foreground">调整大纲结构和内容，使其更符合您的需求</p>
        </div>

        {/* 大纲标题和风格 */}
        <Card className="mb-6">
          <CardContent className="p-6 space-y-4">
            <div>
              <label className="text-sm font-medium text-foreground">文章标题</label>
              <input
                type="text"
                value={outline.content.title || ""}
                onChange={(e) => setOutline({ ...outline, content: { ...outline.content, title: e.target.value } })}
                className="mt-1 w-full rounded-lg border border-border bg-white px-4 py-2 text-lg font-medium focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
              />
            </div>
            <div>
              <label className="text-sm font-medium text-foreground">设计思路</label>
              <textarea
                value={outline.reasoning || ""}
                onChange={(e) => setOutline({ ...outline, reasoning: e.target.value })}
                className="mt-1 min-h-[60px] w-full rounded-lg border border-border bg-white px-4 py-2 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
              />
            </div>
          </CardContent>
        </Card>

        {/* 章节列表 */}
        <div className="space-y-4">
          {sections.map((section, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.05 }}
            >
              <Card className={cn(
                "transition-all",
                index === 0 && "border-t-4 border-t-primary"
              )}>
                <CardHeader className="pb-3">
                  <div className="flex items-center gap-2">
                    <div className="flex flex-col gap-0.5">
                      <button
                        onClick={() => moveSection(index, index - 1)}
                        disabled={index === 0}
                        className="rounded p-0.5 text-muted-foreground hover:bg-muted disabled:opacity-30"
                        title="上移"
                      >
                        <GripVertical className="h-4 w-4" />
                      </button>
                    </div>
                    <span className="flex h-7 w-7 items-center justify-center rounded-full bg-primary/10 text-sm font-bold text-primary">
                      {index + 1}
                    </span>
                    <input
                      type="text"
                      value={section.heading}
                      onChange={(e) => updateSection(index, "heading", e.target.value)}
                      placeholder="章节标题"
                      className="flex-1 text-lg font-medium text-foreground focus:outline-none border-b border-transparent focus:border-primary"
                    />
                    <div className="flex items-center gap-1">
                      <input
                        type="number"
                        value={section.word_count || 0}
                        onChange={(e) => updateSection(index, "word_count", parseInt(e.target.value) || 0)}
                        className="w-16 rounded border border-border px-2 py-1 text-xs text-center focus:border-primary focus:outline-none"
                        title="预计字数"
                      />
                      <span className="text-xs text-muted-foreground">字</span>
                      <button
                        onClick={() => removeSection(index)}
                        className="ml-2 rounded p-1 text-muted-foreground hover:bg-error/10 hover:text-error"
                        title="删除章节"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                </CardHeader>

                <CardContent className="pt-0">
                  <div className="ml-9">
                    <textarea
                      value={section.description}
                      onChange={(e) => updateSection(index, "description", e.target.value)}
                      placeholder="描述本章节的主要内容..."
                      className="w-full rounded-lg border border-border bg-white px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
                    />

                    {/* 子主题 */}
                    {section.subtopics && section.subtopics.length > 0 && (
                      <div className="mt-3 space-y-2">
                        {section.subtopics.map((topic, tIndex) => (
                          <div key={tIndex} className="flex items-center gap-2">
                            <span className="h-1.5 w-1.5 rounded-full bg-primary/40" />
                            <input
                              type="text"
                              value={topic}
                              onChange={(e) => updateSubtopic(index, tIndex, e.target.value)}
                              placeholder="子主题"
                              className="flex-1 rounded border border-border px-2 py-1 text-sm focus:border-primary focus:outline-none"
                            />
                            <button
                              onClick={() => removeSubtopic(index, tIndex)}
                              className="rounded p-0.5 text-muted-foreground hover:text-error"
                            >
                              <Trash2 className="h-3 w-3" />
                            </button>
                          </div>
                        ))}
                      </div>
                    )}

                    <button
                      onClick={() => addSubtopic(index)}
                      className="mt-2 flex items-center gap-1 text-xs text-primary hover:text-primary-600"
                    >
                      <Plus className="h-3 w-3" />
                      添加子主题
                    </button>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </div>

        {/* 添加章节 */}
        <button
          onClick={addSection}
          className="mt-4 flex w-full items-center justify-center gap-2 rounded-xl border-2 border-dashed border-border py-3 text-sm font-medium text-muted-foreground transition-all hover:border-primary/40 hover:bg-primary/5 hover:text-primary"
        >
          <Plus className="h-4 w-4" />
          添加新章节
        </button>

        {/* 统计 */}
        <div className="mt-6 flex items-center justify-between rounded-lg bg-muted/50 px-4 py-3">
          <span className="text-sm text-muted-foreground">
            共 {sections.length} 个章节，预计 {totalWords.toLocaleString()} 字
          </span>
        </div>

        {/* 按钮 */}
        <div className="mt-8 flex items-center justify-between">
          <Button variant="secondary" size="lg" onClick={() => router.back()}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            返回
          </Button>
          <Button size="lg" onClick={handleSave} disabled={isSaving}>
            {isSaving ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                保存中...
              </>
            ) : (
              <>
                <Check className="mr-2 h-4 w-4" />
                确认大纲，进入配置
                <ArrowRight className="ml-2 h-4 w-4" />
              </>
            )}
          </Button>
        </div>
      </div>
    </div>
  )
}
