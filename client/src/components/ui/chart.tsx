"use client"

import * as React from "react"
import * as RechartsPrimitive from "recharts"
import { cn } from "@/lib/utils"

const THEMES = { light: "", dark: ".dark" } as const

export type ChartConfig = {
  [k in string]: {
    label?: React.ReactNode
    icon?: React.ComponentType
    color?: string
    theme?: Record<keyof typeof THEMES, string>
  }
}

type ChartContextProps = { config: ChartConfig }

const ChartContext = React.createContext<ChartContextProps | null>(null)

function useChart() {
  const context = React.useContext(ChartContext)
  if (!context) throw new Error("useChart must be used within a ChartContainer.")
  return context
}

function ChartContainer({
  id,
  className,
  children,
  config,
  ...props
}: React.ComponentProps<"div"> & {
  config: ChartConfig
  children: React.ReactNode
}) {
  const uniqueId = React.useId()
  const chartId = `chart-${id || uniqueId.replace(/:/g, "")}`
  const containerRef = React.useRef<HTMLDivElement>(null)
  const [size, setSize] = React.useState({ width: 0, height: 0 })

  React.useEffect(() => {
    const node = containerRef.current
    if (!node) return

    const updateSize = () => {
      const rect = node.getBoundingClientRect()
      setSize({
        width: Math.max(0, Math.floor(rect.width)),
        height: Math.max(0, Math.floor(rect.height)),
      })
    }

    updateSize()
    const observer = new ResizeObserver(updateSize)
    observer.observe(node)
    return () => observer.disconnect()
  }, [])

  const canRenderChart = size.width > 0 && size.height > 0
  const chart =
    canRenderChart && React.isValidElement(children)
      ? React.cloneElement(
          children as React.ReactElement<{ width?: number; height?: number }>,
          { width: size.width, height: size.height }
        )
      : null

  return (
    <ChartContext.Provider value={{ config }}>
      <div
        ref={containerRef}
        data-chart={chartId}
        className={cn(
          "min-h-0 min-w-0 [&_.recharts-cartesian-axis-tick_text]:fill-muted-foreground [&_.recharts-cartesian-grid_line]:stroke-border/30 [&_.recharts-surface]:outline-none",
          className
        )}
        {...props}
      >
        <ChartStyle id={chartId} config={config} />
        {chart}
      </div>
    </ChartContext.Provider>
  )
}

const ChartStyle = ({ id, config }: { id: string; config: ChartConfig }) => {
  const colorConfig = Object.entries(config).filter(([, cfg]) => cfg.theme || cfg.color)
  if (!colorConfig.length) return null

  return (
    <style
      dangerouslySetInnerHTML={{
        __html: Object.entries(THEMES)
          .map(([theme, prefix]) =>
            [
              `${prefix} [data-chart=${id}] {`,
              ...colorConfig.map(([key, itemConfig]) => {
                const color =
                  itemConfig.theme?.[theme as keyof typeof itemConfig.theme] ||
                  itemConfig.color
                return color ? `  --color-${key}: ${color};` : null
              }),
              "}",
            ]
              .filter(Boolean)
              .join("\n")
          )
          .join("\n"),
      }}
    />
  )
}

const ChartTooltip = RechartsPrimitive.Tooltip

interface TooltipPayloadItem {
  dataKey?: string | number
  name?: string | number
  value?: string | number
  color?: string
  fill?: string
  payload?: Record<string, unknown>
}

interface ChartTooltipContentProps {
  active?: boolean
  payload?: TooltipPayloadItem[]
  label?: string | number
  className?: string
  hideLabel?: boolean
  hideIndicator?: boolean
  indicator?: "line" | "dot" | "dashed"
  nameKey?: string
  labelKey?: string
  formatter?: (value: string | number, name: string | number) => React.ReactNode
  labelFormatter?: (value: unknown, payload: TooltipPayloadItem[]) => React.ReactNode
  labelClassName?: string
  color?: string
}

const ChartTooltipContent = React.forwardRef<HTMLDivElement, ChartTooltipContentProps>(
  (
    {
      active,
      payload,
      className,
      indicator = "dot",
      hideLabel = false,
      hideIndicator = false,
      label,
      labelFormatter,
      labelClassName,
      formatter,
      color,
      nameKey,
      labelKey,
    },
    ref
  ) => {
    const { config } = useChart()

    const tooltipLabel = React.useMemo(() => {
      if (hideLabel || !payload?.length) return null
      const [item] = payload
      const key = `${labelKey || item.dataKey || item.name || "value"}`
      const itemConfig = config[key]
      const value =
        !labelKey && typeof label === "string"
          ? config[label]?.label || label
          : itemConfig?.label

      if (labelFormatter) {
        return (
          <div className={cn("font-medium", labelClassName)}>
            {labelFormatter(value, payload)}
          </div>
        )
      }
      if (!value) return null
      return <div className={cn("font-medium", labelClassName)}>{String(value)}</div>
    }, [label, labelFormatter, payload, hideLabel, labelClassName, config, labelKey])

    if (!active || !payload?.length) return null

    return (
      <div
        ref={ref}
        className={cn(
          "grid min-w-32 items-start gap-1.5 rounded-lg border border-border/50 bg-card px-2.5 py-1.5 text-xs shadow-xl",
          className
        )}
      >
        {tooltipLabel}
        <div className="grid gap-1.5">
          {payload.map((item, index) => {
            const key = `${nameKey || item.name || item.dataKey || "value"}`
            const itemConfig = config[key]
            const indicatorColor = color || (item.payload?.fill as string) || item.color
            const indicatorClass =
              indicator === "line"
                ? "h-3 w-1"
                : indicator === "dashed"
                  ? "h-0 w-3 border-t border-dashed bg-transparent"
                  : "h-2.5 w-2.5"

            return (
              <div
                key={index}
                className={cn(
                  "flex w-full items-center gap-2",
                )}
              >
                {!hideIndicator && (
                  <div
                    className={cn("shrink-0 rounded-[2px]", indicatorClass)}
                    style={{ backgroundColor: indicatorColor }}
                  />
                )}
                <div className="flex flex-1 justify-between leading-none items-center">
                  <span className="text-muted-foreground">
                    {itemConfig?.label ?? String(item.name ?? "")}
                  </span>
                  {item.value !== undefined && (
                    <span className="font-mono font-medium tabular-nums text-foreground ml-2">
                      {formatter
                        ? formatter(item.value, item.name ?? "")
                        : item.value.toLocaleString()}
                    </span>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      </div>
    )
  }
)
ChartTooltipContent.displayName = "ChartTooltipContent"

interface LegendPayloadItem {
  value?: string | number
  color?: string
  dataKey?: string | number
}

interface ChartLegendContentProps {
  payload?: LegendPayloadItem[]
  verticalAlign?: "top" | "bottom" | "middle"
  hideIcon?: boolean
  nameKey?: string
  className?: string
}

const ChartLegend = RechartsPrimitive.Legend

const ChartLegendContent = React.forwardRef<HTMLDivElement, ChartLegendContentProps>(
  ({ className, hideIcon = false, payload, verticalAlign = "bottom", nameKey }, ref) => {
    const { config } = useChart()
    if (!payload?.length) return null

    return (
      <div
        ref={ref}
        className={cn(
          "flex items-center justify-center gap-4",
          verticalAlign === "top" ? "pb-3" : "pt-3",
          className
        )}
      >
        {payload.map((item, i) => {
          const key = `${nameKey || item.dataKey || "value"}`
          const itemConfig = config[key]
          return (
            <div key={i} className="flex items-center gap-1.5">
              {itemConfig?.icon && !hideIcon ? (
                <itemConfig.icon />
              ) : (
                <div
                  className="h-2 w-2 shrink-0 rounded-[2px]"
                  style={{ backgroundColor: item.color }}
                />
              )}
              <span className="text-xs text-muted-foreground">
                {String(itemConfig?.label ?? item.value ?? "")}
              </span>
            </div>
          )
        })}
      </div>
    )
  }
)
ChartLegendContent.displayName = "ChartLegendContent"

export {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  ChartLegend,
  ChartLegendContent,
  ChartStyle,
}
