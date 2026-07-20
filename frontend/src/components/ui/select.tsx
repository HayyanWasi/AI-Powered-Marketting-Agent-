"use client"

import * as React from "react"
import * as SelectPrimitive from "@radix-ui/react-select"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"
import { ChevronDown } from "lucide-react"

const selectVariants = cva(
  "flex h-10 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 backdrop-blur-sm",
  {
    variants: {
      variant: {
        default:
          "bg-background border-input text-foreground",
        glass:
          "bg-white/10 border-white/20 backdrop-blur-md text-foreground hover:bg-white/20",
        glassDark:
          "bg-black/10 border-white/10 backdrop-blur-md text-foreground hover:bg-black/20",
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

export interface SelectProps
  extends React.ComponentPropsWithoutRef<typeof SelectPrimitive.Root>,
    VariantProps<typeof selectVariants> {
  placeholder?: string
}

const Select = React.forwardRef<typeof SelectPrimitive.Trigger, SelectProps>(
  ({ className, variant, size, children, placeholder, ...props }, ref) => {
    return (
      <SelectPrimitive.Root {...props}>
        <SelectPrimitive.Trigger
          ref={ref}
          className={cn(selectVariants({ variant, size, className }))}
        >
          <SelectPrimitive.Value placeholder={placeholder} />
          <SelectPrimitive.Icon asChild>
            <ChevronDown className="h-4 w-4 opacity-50" />
          </SelectPrimitive.Icon>
        </SelectPrimitive.Trigger>
        <SelectPrimitive.Portal>
          <SelectPrimitive.Content
            className={cn(
              "relative z-50 min-w-[8rem] overflow-hidden rounded-md border bg-popover text-popover-foreground shadow-md data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95 data-[state=closed]:slide-out-to-left-1/2 data-[state=open]:slide-in-from-left-1/2 data-[state=closed]:slide-out-to-top-[var(--radix-select-trigger-height)] data-[state=open]:slide-in-from-top-[var(--radix-select-trigger-height)]",
              "bg-popover border-popover backdrop-blur-md"
            )}
            position="popper"
            sideOffset={4}
          >
            <SelectPrimitive.Viewport className="p-1">
              {children}
            </SelectPrimitive.Viewport>
            <SelectPrimitive.ScrollUpButton className="flex cursor-default items-center justify-center py-1" />
            <SelectPrimitive.ScrollDownButton className="flex cursor-default items-center justify-center py-1" />
          </SelectPrimitive.Content>
        </SelectPrimitive.Portal>
      </SelectPrimitive.Root>
    )
  }
)
Select.displayName = SelectPrimitive.Root.displayName

export { Select, selectVariants }

const SelectItem = SelectPrimitive.Item

export { SelectItem }
