"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { motion } from "framer-motion"
import { Sparkles, ArrowRight, Loader2 } from "lucide-react"

const exampleTopics = [
  "AI在教育领域的应用",
  "2024年最值得学习的编程语言",
  "远程办公的最佳实践",
  "可持续发展的商业模式",
]

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.15, delayChildren: 0.2 },
  },
}

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.5, ease: [0.4, 0, 0.2, 1] },
  },
}

export default function HomePage() {
  const router = useRouter()
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [topic, setTopic] = useState("")
  const [error, setError] = useState("")

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError("")

    if (topic.trim().length < 2) {
      setError("请输入至少2个字符")
      return
    }
    if (topic.length > 200) {
      setError("请输入不超过200个字符")
      return
    }

    setIsSubmitting(true)
    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api"}/projects`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ topic: topic.trim() }),
        }
      )

      if (!res.ok) throw new Error("创建项目失败")

      const data = await res.json()
      router.push(`/project/${data.project_id}/processing`)
    } catch (err) {
      setError(err instanceof Error ? err.message : "发生错误，请重试")
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden bg-grid">
      {/* 背景光效 */}
      <div className="pointer-events-none absolute inset-0 bg-mesh" />

      {/* 渐变光圈 */}
      <div className="pointer-events-none absolute left-1/2 top-1/4 h-[500px] w-[500px] -translate-x-1/2 rounded-full bg-primary/10 blur-[100px]" />
      <div className="pointer-events-none absolute bottom-1/4 right-1/4 h-[300px] w-[300px] rounded-full bg-accent/10 blur-[80px]" />

      <motion.div
        className="relative z-10 flex w-full max-w-2xl flex-col items-center px-4"
        variants={containerVariants}
        initial="hidden"
        animate="visible"
      >
        {/* LOGO */}
        <motion.div variants={itemVariants} className="mb-10 text-center">
          <div className="mb-4 flex items-center justify-center gap-3">
            <Sparkles className="h-10 w-10 text-primary" />
            <h1 className="text-gradient text-5xl font-bold tracking-tight sm:text-6xl">
              Article Generate
            </h1>
          </div>
          <p className="text-lg text-muted-foreground">
            AI驱动的智能博客文章生成平台
          </p>
        </motion.div>

        {/* 输入表单 */}
        <motion.form onSubmit={onSubmit} variants={itemVariants} className="w-full">
          <div className="flex flex-col gap-3 sm:flex-row">
            <input
              type="text"
              value={topic}
              onChange={(e) => {
                setTopic(e.target.value)
                if (error) setError("")
              }}
              placeholder="请输入你的文章内容需求"
              disabled={isSubmitting}
              className="h-14 flex-1 rounded-xl border border-border bg-white px-5 text-lg text-foreground placeholder:text-muted-foreground transition-all focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary hover:border-primary/50 disabled:opacity-50"
            />
            <button
              type="submit"
              disabled={isSubmitting}
              className="flex h-14 items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-primary to-primary-600 px-8 text-lg font-medium text-white shadow-lg shadow-primary/20 transition-all hover:shadow-xl hover:shadow-primary/30 active:scale-[0.98] disabled:opacity-50"
            >
              {isSubmitting ? (
                <Loader2 className="h-5 w-5 animate-spin" />
              ) : (
                <>
                  开始生成
                  <ArrowRight className="h-5 w-5" />
                </>
              )}
            </button>
          </div>
          {error && <p className="mt-2 text-sm text-error">{error}</p>}
        </motion.form>

        {/* 示例 */}
        <motion.div variants={itemVariants} className="mt-8">
          <p className="mb-3 text-center text-sm text-muted-foreground">
            试试这些示例：
          </p>
          <div className="flex flex-wrap justify-center gap-2">
            {exampleTopics.map((t) => (
              <button
                key={t}
                type="button"
                onClick={() => setTopic(t)}
                className="rounded-full border border-border bg-white/60 px-4 py-1.5 text-sm text-muted-foreground backdrop-blur-sm transition-all hover:border-primary/40 hover:bg-primary/5 hover:text-primary active:scale-95"
              >
                {t}
              </button>
            ))}
          </div>
        </motion.div>
      </motion.div>

      {/* 底部 */}
      <motion.p
        className="absolute bottom-8 text-sm text-muted-foreground"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1 }}
      >
        由阿里云百炼提供AI能力支持
      </motion.p>
    </div>
  )
}
