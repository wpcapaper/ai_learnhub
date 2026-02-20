"use client"

import { motion, useInView, useScroll, useTransform } from "motion/react"
import { forwardRef, useRef } from "react"

import { cn } from "@/lib/utils"

export interface AnimatedGradientTextProps {
  className?: string
  children: React.ReactNode
}

export const AnimatedGradientText = forwardRef<
  HTMLDivElement,
  AnimatedGradientTextProps
>(({ className, children }, ref) => {
  const scopeRef = useRef<HTMLDivElement>(null)
  const { scrollYProgress } = useScroll({
    target: scopeRef,
    offset: ["start end", "end start"],
  })

  const opacity = useTransform(scrollYProgress, [0, 0.5, 1], [0, 1, 0])
  const y = useTransform(scrollYProgress, [0, 0.5, 1], [50, 0, -50])

  return (
    <div ref={scopeRef} className="relative">
      <motion.div
        ref={ref}
        style={{ opacity, y }}
        className={cn(
          "relative flex flex-col overflow-hidden",
          className
        )}
      >
        <motion.span
          initial={{ backgroundPosition: "0 50%" }}
          animate={{ backgroundPosition: ["0, 50%", "100% 50%", "0 50%"] }}
          transition={{
            duration: 5,
            repeat: Infinity,
            ease: "linear",
            repeatType: "loop",
          }}
          className="bg-[linear-gradient(90deg,var(--gradient-from),var(--gradient-via),var(--gradient-to),var(--gradient-from))] bg-[length:200%_auto] bg-clip-text text-transparent [--gradient-from:#ffaa40] [--gradient-to:#9c40ff] [--gradient-via:#3b82f6]"
        >
          {children}
        </motion.span>
      </motion.div>
    </div>
  )
})

AnimatedGradientText.displayName = "AnimatedGradientText"
