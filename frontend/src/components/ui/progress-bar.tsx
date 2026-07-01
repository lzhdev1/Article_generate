import { cn } from "@/lib/utils"

interface ProgressBarProps {
  value: number
  label?: string
  showValue?: boolean
  className?: string
  variant?: "default" | "success" | "gradient"
}

export function ProgressBar({
  value,
  label,
  showValue = true,
  className,
  variant = "default",
}: ProgressBarProps) {
  const clampedValue = Math.min(100, Math.max(0, value))

  const variantClasses = {
    default: "bg-primary-500",
    success: "bg-accent-500",
    gradient: "bg-gradient-to-r from-primary-500 to-accent-500",
  }

  return (
    <div className={cn("w-full", className)}>
      {(label || showValue) && (
        <div className="mb-2 flex items-center justify-between">
          {label && <span className="text-sm font-medium text-foreground">{label}</span>}
          {showValue && <span className="text-sm font-medium text-muted-foreground">{clampedValue}%</span>}
        </div>
      )}
      <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
        <div
          className={cn("h-full rounded-full transition-all duration-500 ease-out", variantClasses[variant])}
          style={{ width: `${clampedValue}%` }}
        />
      </div>
    </div>
  )
}
