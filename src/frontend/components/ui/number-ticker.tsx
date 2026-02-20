"use client"

import { motion, useInView, useSpring, useTransform } from "motion/react"
import { useEffect, useRef, useState } from "react"

import { cn } from "@/lib/utils"

interface NumberTickerProps {
  value: number
  direction?: "up" | "down"
  className?: string
  style?: React.CSSProperties
  delay?: number
  decimals?: number
}

export function NumberTicker({
  value,
  direction = "up",
  className,
  style,
  delay = 0,
  decimals = 0,
}: NumberTickerProps) {
  const ref = useRef<HTMLSpanElement>(null)
  const motionValue = useSpring(direction === "down" ? value : 0, {
    damping: 60,
    stiffness: 100,
  })
  const isInView = useInView(ref, { once: true, margin: "0px" })

  useEffect(() => {
    if (isInView) {
      const timeoutId = setTimeout(() => {
        motionValue.set(direction === "down" ? 0 : value)
      }, delay * 1000)
      return () => clearTimeout(timeoutId)
    }
  }, [motionValue, isInView, delay, value, direction])

  const displayValue = useTransform(motionValue, (latest) => {
    return Intl.NumberFormat("en-US", {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    }).format(latest)
  })

  return (
    <motion.span
      ref={ref}
      className={cn(
        "tabular-nums tracking-wider text-black dark:text-white",
        className
      )}
      style={style}
    >
      <motion.span>{displayValue}</motion.span>
    </motion.span>
  )
}
