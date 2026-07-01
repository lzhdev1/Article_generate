// frontend/src/services/api.ts

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api"

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || "请求失败")
  }
  return res.json()
}

export interface ProjectResponse {
  project_id: string
  topic: string
  status: string
  created_at: string
}

export const api = {
  project: {
    create: (topic: string) =>
      request<ProjectResponse>("/projects", {
        method: "POST",
        body: JSON.stringify({ topic }),
      }),
    get: (id: string) => request<ProjectResponse>(`/projects/${id}`),
  },
}
