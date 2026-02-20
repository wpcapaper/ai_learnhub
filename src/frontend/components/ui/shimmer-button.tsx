import { cn } from "@/lib/utils"
import { motion, type MotionProps } from "motion/react"

interface ShimmerButtonProps extends MotionProps {
  shimmerColor?: string
  shimmerSize?: string
  borderRadius?: string
  shimmerDuration?: string
  background?: string
  className?: string
  children?: React.ReactNode
  onClick?: () => void
  disabled?: boolean
  type?: "button" | "submit" | "reset"
}

export const ShimmerButton = ({
  shimmerColor = "#ffffff",
  shimmerSize = "0.1em",
  borderRadius = "100px",
  shimmerDuration = "3s",
  background = "linear-gradient(90deg, #3b82f6, #8b5cf6, #3b82f6)",
  className,
  children,
  onClick,
  disabled,
  type = "button",
  ...props
}: ShimmerButtonProps) => {
  return (
    <motion.button
      type={type}
      className={cn(
        "relative inline-flex items-center justify-center overflow-hidden font-medium transition-all duration-300",
        className
      )}
      style={{
        borderRadius,
        background,
        opacity: disabled ? 0.5 : 1,
        cursor: disabled ? "not-allowed" : "pointer"
      }}
      onClick={disabled ? undefined : onClick}
      disabled={disabled}
      {...props}
    >
      <div
        className="absolute inset-0 overflow-hidden"
        style={{ borderRadius }}
      >
        <div
          className="absolute inset-0 animate-shimmer"
          style={{
            background: `linear-gradient(90deg, transparent, ${shimmerColor}, transparent)`,
            transform: "translateX(-100%)",
            animation: `shimmer ${shimmerDuration} infinite`,
          }}
        />
      </div>
      <span className="relative z-10">{children}</span>
    </motion.button>
  )
}
