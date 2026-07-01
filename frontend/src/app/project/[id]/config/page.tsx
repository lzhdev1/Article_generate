"use client"

import { useState } from "react"
import { useParams, useRouter } from "next/navigation"
import { Image, Video, ListChecks, HelpCircle, Sparkles, Plus, Minus } from "lucide-react"
import { motion } from "framer-motion"

import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { StepIndicator } from "@/components/ui/step-indicator"

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api"

export default function ConfigPage() {
  const params = useParams()
  const router = useRouter()
  const projectId = params.id as string
  const [isSubmitting, setIsSubmitting] = useState(false)

  const [addImages, setAddImages] = useState(true)
  const [addVideos, setAddVideos] = useState(false)
  const [addSummary, setAddSummary] = useState(true)
  const [addFaq, setAddFaq] = useState(true)
  const [imageCount, setImageCount] = useState(3)
  const [faqCount, setFaqCount] = useState(5)

  const handleSubmit = async () => {
    setIsSubmitting(true)
    try {
      const configRes = await fetch(`${API_URL}/projects/${projectId}/workflow/save-article-config`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          article_config: { add_images: addImages, add_videos: addVideos, add_summary: addSummary, add_faq: addFaq, image_count: imageCount, faq_count: faqCount },
        }),
      })

      if (configRes.ok) {
        // 文章生成已触发，跳转到生成进度页
        router.push(`/project/${projectId}/generating`)
      } else {
        console.error("Failed to save article config")
      }
    } catch (err) {
      console.error(err)
    } finally {
      setIsSubmitting(false)
    }
  }

  const steps = [
    { id: "search", label: "搜索", status: "completed" },
    { id: "filter", label: "过滤", status: "completed" },
    { id: "extract", label: "提取", status: "completed" },
    { id: "title", label: "标题", status: "completed" },
    { id: "outline", label: "大纲", status: "completed" },
    { id: "config", label: "配置", status: "current" },
    { id: "generate", label: "生成", status: "upcoming" },
  ]

  return (
    <div className="min-h-screen bg-grid">
      <div className="pointer-events-none fixed inset-0 bg-mesh" />

      <div className="relative z-10 mx-auto max-w-3xl px-4 py-8">
        <StepIndicator steps={steps} className="mb-8" />

        <div className="mb-8 text-center">
          <h1 className="text-3xl font-bold text-foreground">最终配置</h1>
          <p className="mt-2 text-muted-foreground">配置文章生成的最后选项</p>
        </div>

        <div className="space-y-4">
          {/* 配图 */}
          <ConfigCard
            icon={<Image className="h-6 w-6 text-blue-600" />}
            iconBg="bg-blue-100"
            title="文章配图"
            description="在文章中自动插入相关配图"
            checked={addImages}
            onChange={setAddImages}
          >
            {addImages && (
              <NumberControl value={imageCount} onChange={setImageCount} min={1} max={10} label="图片数量" />
            )}
          </ConfigCard>

          {/* 视频 */}
          <ConfigCard
            icon={<Video className="h-6 w-6 text-purple-600" />}
            iconBg="bg-purple-100"
            title="视频嵌入"
            description="在文章中嵌入相关视频内容"
            checked={addVideos}
            onChange={setAddVideos}
          />

          {/* 要点总结 */}
          <ConfigCard
            icon={<ListChecks className="h-6 w-6 text-green-600" />}
            iconBg="bg-green-100"
            title="要点总结"
            description="在文章末尾添加核心要点总结"
            checked={addSummary}
            onChange={setAddSummary}
          />

          {/* FAQ */}
          <ConfigCard
            icon={<HelpCircle className="h-6 w-6 text-orange-600" />}
            iconBg="bg-orange-100"
            title="FAQ常见问题"
            description="在文章末尾添加常见问题解答"
            checked={addFaq}
            onChange={setAddFaq}
          >
            {addFaq && (
              <NumberControl value={faqCount} onChange={setFaqCount} min={1} max={10} label="问题数量" />
            )}
          </ConfigCard>
        </div>

        {/* 预览 */}
        <Card className="mt-6 bg-muted/50">
          <CardContent className="p-6">
            <p className="text-sm font-medium text-foreground">附加内容预览</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {addImages && <Tag>✓ 配图 ({imageCount}张)</Tag>}
              {addVideos && <Tag>✓ 视频</Tag>}
              {addSummary && <Tag>✓ 要点总结</Tag>}
              {addFaq && <Tag>✓ FAQ ({faqCount}个)</Tag>}
            </div>
          </CardContent>
        </Card>

        {/* 按钮 */}
        <div className="mt-8 flex justify-end">
          <Button size="xl" onClick={handleSubmit} isLoading={isSubmitting}>
            <Sparkles className="mr-2 h-5 w-5" />
            开始生成文章
          </Button>
        </div>
      </div>
    </div>
  )
}

function ConfigCard({ icon, iconBg, title, description, checked, onChange, children }: {
  icon: React.ReactNode
  iconBg: string
  title: string
  description: string
  checked: boolean
  onChange: (v: boolean) => void
  children?: React.ReactNode
}) {
  return (
    <Card>
      <CardContent className="flex items-start gap-4 p-6">
        <div className={`rounded-lg ${iconBg} p-3`}>{icon}</div>
        <div className="flex-1">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-medium">{title}</h3>
            <Switch checked={checked} onChange={onChange} />
          </div>
          <p className="mt-1 text-sm text-muted-foreground">{description}</p>
          {children && <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} className="mt-3">{children}</motion.div>}
        </div>
      </CardContent>
    </Card>
  )
}

function Switch({ checked, onChange }: { checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <button
      onClick={() => onChange(!checked)}
      className={`relative h-6 w-11 rounded-full transition-colors ${checked ? "bg-primary" : "bg-muted"}`}
    >
      <span className={`absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition-transform ${checked ? "left-[22px]" : "left-0.5"}`} />
    </button>
  )
}

function NumberControl({ value, onChange, min, max, label }: { value: number; onChange: (v: number) => void; min: number; max: number; label: string }) {
  return (
    <div className="flex items-center gap-3">
      <span className="text-sm text-muted-foreground">{label}:</span>
      <button onClick={() => onChange(Math.max(min, value - 1))} className="flex h-8 w-8 items-center justify-center rounded-lg border border-border hover:bg-muted"><Minus className="h-4 w-4" /></button>
      <span className="w-8 text-center font-medium">{value}</span>
      <button onClick={() => onChange(Math.min(max, value + 1))} className="flex h-8 w-8 items-center justify-center rounded-lg border border-border hover:bg-muted"><Plus className="h-4 w-4" /></button>
    </div>
  )
}

function Tag({ children }: { children: React.ReactNode }) {
  return <span className="rounded-full bg-accent/10 px-3 py-1 text-xs font-medium text-accent-600">{children}</span>
}
