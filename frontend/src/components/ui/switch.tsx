"use client"

import * as React from "react"
import * as SwitchPrimitive from "@radix-ui/react-switch"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

const switchVariants = cva(
  "peer inline-flex h-6 w-11 shrink-0 cursor-pointer items-center rounded-full border-2 border-transparent transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:cursor-not-allowed disabled:opacity-50 backdrop-blur-sm",
  {
    variants: {
      variant: {
        default: "bg-input",
        glass: "bg-white/10 border-white/20 backdrop-blur-md",
        glassDark: "bg-black/10 border-white/10 backdrop-blur-md",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

const switchThumbVariants = cva(
  "pointer-events-none block h-5 w-5 rounded-full bg-background shadow-lg ring-0 transition-transform data-[state=checked]:translate-x-5 data-[state=unchecked]:translate-x-0 backdrop-blur-sm",
  {
    variants: {
      variant: {
        default: "bg-white/90",
        glass: "bg-white/80",
        glassDark: "bg-white/80",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

export interface SwitchProps
  extends React.ComponentPropsWithoutRef<typeof SwitchPrimitive.Root>,
    VariantProps<typeof switchVariants> {}

const Switch = React.forwardRef<React.ElementRef<typeof SwitchPrimitive.Root>, SwitchProps>(
  ({ className, variant, ...props }, ref) => (
    <SwitchPrimitive.Root
      className={cn(switchVariants({ variant, className }))}
      {...props}
      ref={ref}
    >
      <SwitchPrimitive.Thumb className={cn(switchThumbVariants({ variant }))} />
    </SwitchPrimitive.Root>
  )
)
Switch.displayName = SwitchPrimitive.Root.displayName

export { Switch, switchVariants, switchThumbVariants }
