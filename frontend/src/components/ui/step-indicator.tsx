import { cn } from "@/lib/utils"
import { Check } from "lucide-react"

interface Step {
  id: string
  label: string
  status: "completed" | "current" | "upcoming"
}

interface StepIndicatorProps {
  steps: Step[]
  className?: string
}

export function StepIndicator({ steps, className }: StepIndicatorProps) {
  return (
    <div className={cn("flex items-center justify-center", className)}>
      {steps.map((step, index) => (
        <div key={step.id} className="flex items-center">
          <div className="flex flex-col items-center">
            <div
              className={cn(
                "flex h-10 w-10 items-center justify-center rounded-full border-2 transition-all duration-300",
                step.status === "completed" && "border-accent bg-accent text-white",
                step.status === "current" && "border-primary bg-primary text-white shadow-lg shadow-primary/30",
                step.status === "upcoming" && "border-border bg-white text-muted-foreground"
              )}
            >
              {step.status === "completed" ? (
                <Check className="h-5 w-5" />
              ) : (
                <span className="text-sm font-medium">{index + 1}</span>
              )}
            </div>
            <span
              className={cn(
                "mt-2 text-xs font-medium",
                step.status === "completed" && "text-accent-600",
                step.status === "current" && "text-primary-600",
                step.status === "upcoming" && "text-muted-foreground"
              )}
            >
              {step.label}
            </span>
          </div>

          {index < steps.length - 1 && (
            <div
              className={cn(
                "mx-2 h-0.5 w-8 sm:w-16 transition-all duration-300",
                step.status === "completed" ? "bg-accent" : "bg-border"
              )}
            />
          )}
        </div>
      ))}
    </div>
  )
}
