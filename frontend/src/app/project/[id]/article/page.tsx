"use client"

import { useEffect, useState } from "react"
import { useParams, useRouter } from "next/navigation"
import { motion } from "framer-motion"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import { ArrowLeft, FileText, Clock, Shield, Download, Copy, ListChecks, HelpCircle, Sparkles, ChevronDown, ChevronUp } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { LoadingSpinner } from "@/components/ui/loading"

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api"

interface ArticleData {
  topic: string
  selected_title: string
  article: string
  summary: string | null
  faq: { question: string; answer: string }[]
  verification_passed: boolean
  retry_count: number
}

export default function ArticlePage() {
  const params = useParams()
  const router = useRouter()
  const projectId = params.id as string
  const [data, setData] = useState<ArticleData | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [showSummary, setShowSummary] = useState(true)
  const [faqOpen, setFaqOpen] = useState<Record<number, boolean>>({})

  useEffect(() => {
    loadArticle()
  }, [projectId])

  const loadArticle = async () => {
    try {
      const res = await fetch(`${API_URL}/projects/${projectId}/workflow/state`)
      if (res.ok) {
        const json = await res.json()
        setData(json.data)
      }
    } catch (err) {
      console.error(err)
    } finally {
      setIsLoading(false)
    }
  }

  const handleCopy = async () => {
    if (data?.article) {
      await navigator.clipboard.writeText(data.article)
    }
  }

  const handleExportMd = () => {
    if (!data?.article) return
    const blob = new Blob([data.article], { type: "text/markdown" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = `${data.selected_title || "article"}.md`
    a.click()
    URL.revokeObjectURL(url)
  }

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  if (!data || !data.article) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-center">
          <p className="text-muted-foreground">文章未找到</p>
          <Button variant="outline" className="mt-4" onClick={() => router.push("/")}>返回首页</Button>
        </div>
      </div>
    )
  }

  const wordCount = data.article.length
  const readingTime = Math.ceil(wordCount / 400)

  return (
    <div className="min-h-screen bg-grid">
      <div className="pointer-events-none fixed inset-0 bg-mesh" />

      {/* 顶栏 */}
      <div className="sticky top-0 z-20 border-b border-border bg-white/80 backdrop-blur-sm">
        <div className="mx-auto flex max-w-4xl items-center justify-between px-4 py-3">
          <Button variant="ghost" onClick={() => router.push("/")}>
            <ArrowLeft className="mr-2 h-4 w-4" />返回首页
          </Button>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={handleCopy}>
              <Copy className="mr-1 h-3 w-3" />复制
            </Button>
            <Button variant="outline" size="sm" onClick={handleExportMd}>
              <Download className="mr-1 h-3 w-3" />Markdown
            </Button>
          </div>
        </div>
      </div>

      <div className="relative z-10 mx-auto max-w-4xl px-4 py-8">
        {/* 标题 */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
          <h1 className="text-4xl font-bold leading-tight text-foreground">{data.selected_title}</h1>
          <div className="mt-4 flex flex-wrap items-center gap-4 text-sm text-muted-foreground">
            <span className="flex items-center gap-1"><FileText className="h-4 w-4" />{wordCount.toLocaleString()}字</span>
            <span className="flex items-center gap-1"><Clock className="h-4 w-4" />约{readingTime}分钟</span>
            <span className="flex items-center gap-1"><Shield className="h-4 w-4" />验证: {data.verification_passed ? "通过" : "待确认"}</span>
          </div>
        </motion.div>

        {/* 要点总结 */}
        {data.summary && (
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="mb-6">
            <Card className="bg-gradient-to-r from-primary-50 to-accent-50">
              <CardHeader className="pb-3">
                <div className="flex cursor-pointer items-center justify-between" onClick={() => setShowSummary(!showSummary)}>
                  <CardTitle className="flex items-center gap-2 text-base"><ListChecks className="h-5 w-5 text-primary" />要点总结</CardTitle>
                  {showSummary ? <ChevronUp className="h-4 w-4 text-muted-foreground" /> : <ChevronDown className="h-4 w-4 text-muted-foreground" />}
                </div>
              </CardHeader>
              {showSummary && (
                <CardContent>
                  <div className="prose prose-sm max-w-none text-foreground">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{data.summary}</ReactMarkdown>
                  </div>
                </CardContent>
              )}
            </Card>
          </motion.div>
        )}

        {/* 正文 */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }} className="mb-8">
          <Card>
            <CardContent className="p-8">
              <div className="prose prose-lg max-w-none">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{data.article}</ReactMarkdown>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* FAQ */}
        {data.faq && data.faq.length > 0 && (
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }} className="mb-8">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-lg"><HelpCircle className="h-5 w-5 text-warning" />常见问题</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {data.faq.map((item, index) => (
                  <div key={index} className="border-b border-border pb-4 last:border-0">
                    <div className="flex cursor-pointer items-start justify-between" onClick={() => setFaqOpen({ ...faqOpen, [index]: !faqOpen[index] })}>
                      <p className="flex-1 font-medium text-foreground">Q: {item.question}</p>
                      {faqOpen[index] ? <ChevronUp className="ml-2 h-4 w-4 shrink-0 text-muted-foreground" /> : <ChevronDown className="ml-2 h-4 w-4 shrink-0 text-muted-foreground" />}
                    </div>
                    {faqOpen[index] && (
                      <motion.p initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} className="mt-2 text-muted-foreground">
                        A: {item.answer}
                      </motion.p>
                    )}
                  </div>
                ))}
              </CardContent>
            </Card>
          </motion.div>
        )}

        {/* 底部 */}
        <div className="flex justify-center pt-4">
          <Button size="lg" variant="secondary" onClick={() => router.push("/")}>
            <Sparkles className="mr-2 h-4 w-4" />生成新文章
          </Button>
        </div>
      </div>
    </div>
  )
}
