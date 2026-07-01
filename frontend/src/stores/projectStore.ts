// frontend/src/stores/projectStore.ts

import { create } from "zustand"
import { persist } from "zustand/middleware"

interface Project {
  project_id: string
  topic: string
  status: string
  created_at: string
}

interface ProjectState {
  currentProject: Project | null
  setProject: (project: Project) => void
  clearProject: () => void
}

export const useProjectStore = create<ProjectState>()(
  persist(
    (set) => ({
      currentProject: null,
      setProject: (project) => set({ currentProject: project }),
      clearProject: () => set({ currentProject: null }),
    }),
    { name: "article-generator-project" }
  )
)
