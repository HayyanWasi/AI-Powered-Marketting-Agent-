"use client"

import * as React from "react"
import * as InputPrimitive from "@radix-ui/react-select"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

const inputVariants = cva(
  "flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 backdrop-blur-sm",
  {
    variants: {
      variant: {
        default: "bg-background border-input",
        glass: "bg-white/10 border-white/20 backdrop-blur-md text-foreground placeholder:text-foreground/50 hover:bg-white/20 focus:bg-white/20",
        glassDark: "bg-black/10 border-white/10 backdrop-blur-md text-foreground placeholder:text-foreground/50 hover:bg-black/20 focus:bg-black/20",
      },
      size: {
        default: "h-10 px-3 py-2",
        sm: "h-9 px-2",
        lg: "h-11 px-4",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

export interface InputProps
  extends React.InputHTMLAttributes<HTMLInputElement>,
    VariantProps<typeof inputVariants> {}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, variant, size, ...props }, ref) => {
    return (
      <input
        ref={ref}
        className={cn(inputVariants({ variant, size, className }))}
        {...props}
      />
    )
  }
)
Input.displayName = "Input"

export { Input, inputVariants }
