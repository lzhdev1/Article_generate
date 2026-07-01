import * as React from "react"
import { cn } from "@/lib/utils"

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  error?: string
}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, error, ...props }, ref) => {
    return (
      <div className="relative w-full">
        <input
          type={type}
          className={cn(
            "flex w-full rounded-xl border border-border bg-white px-4 py-3 text-base text-foreground placeholder:text-muted-foreground",
            "transition-all duration-200",
            "focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary",
            "hover:border-primary/40",
            "disabled:cursor-not-allowed disabled:opacity-50",
            error && "border-error focus:ring-error/20 focus:border-error",
            className
          )}
          ref={ref}
          {...props}
        />
        {error && <p className="mt-1.5 text-sm text-error">{error}</p>}
      </div>
    )
  }
)
Input.displayName = "Input"

export { Input }
