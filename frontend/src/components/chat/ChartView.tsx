import { useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { BarChart3, LineChart as LineChartIcon, PieChart as PieChartIcon } from "lucide-react";
import clsx from "clsx";
import { useTheme } from "../../context/ThemeContext";
import { AXIS_INK, getCategoricalPalette, GRID_LINE, SINGLE_SERIES } from "../../utils/chartColors";

type ChartKind = "bar" | "line" | "pie";

interface ChartViewProps {
  columns: string[];
  rows: Record<string, unknown>[];
  initialType: ChartKind;
  chartRef?: React.RefObject<HTMLDivElement | null>;
}

const CHART_OPTIONS: { type: ChartKind; label: string; icon: typeof BarChart3 }[] = [
  { type: "bar", label: "Bar", icon: BarChart3 },
  { type: "line", label: "Line", icon: LineChartIcon },
  { type: "pie", label: "Pie", icon: PieChartIcon },
];

export default function ChartView({ columns, rows, initialType, chartRef }: ChartViewProps) {
  const [chartType, setChartType] = useState<ChartKind>(initialType);
  const { theme } = useTheme();
  const isDark = theme === "dark";
  const palette = getCategoricalPalette(isDark);

  const { labelKey, valueKey } = useMemo(() => {
    const sample = rows[0] ?? {};
    const numeric = columns.find((c) => typeof sample[c] === "number");
    const label = columns.find((c) => c !== numeric) ?? columns[0];
    return { labelKey: label, valueKey: numeric ?? columns[1] };
  }, [columns, rows]);

  if (!labelKey || !valueKey || rows.length === 0) return null;

  const chartData = rows.slice(0, 25).map((r) => ({ ...r, [labelKey]: String(r[labelKey]) }));

  return (
    <div>
      <div className="mb-2 flex justify-end gap-1 rounded-lg bg-slate-100 p-1 dark:bg-slate-800 w-fit ml-auto">
        {CHART_OPTIONS.map(({ type, label, icon: Icon }) => (
          <button
            key={type}
            onClick={() => setChartType(type)}
            className={clsx(
              "flex items-center gap-1 rounded-md px-2.5 py-1 text-xs font-medium transition-colors",
              chartType === type
                ? "bg-white text-slate-900 shadow-sm dark:bg-slate-700 dark:text-slate-100"
                : "text-slate-500 dark:text-slate-400"
            )}
          >
            <Icon className="h-3.5 w-3.5" />
            {label}
          </button>
        ))}
      </div>

      <div ref={chartRef} className="h-72 w-full rounded-lg bg-white p-2 dark:bg-slate-900">
        <ResponsiveContainer width="100%" height="100%">
          {chartType === "bar" ? (
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke={isDark ? GRID_LINE.dark : GRID_LINE.light} vertical={false} />
              <XAxis dataKey={labelKey} tick={{ fontSize: 11, fill: AXIS_INK.light }} interval={0} angle={-25} textAnchor="end" height={60} />
              <YAxis tick={{ fontSize: 11, fill: AXIS_INK.light }} />
              <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8 }} />
              <Bar dataKey={valueKey} fill={isDark ? SINGLE_SERIES.dark : SINGLE_SERIES.light} radius={[4, 4, 0, 0]} />
            </BarChart>
          ) : chartType === "line" ? (
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke={isDark ? GRID_LINE.dark : GRID_LINE.light} vertical={false} />
              <XAxis dataKey={labelKey} tick={{ fontSize: 11, fill: AXIS_INK.light }} interval={0} angle={-25} textAnchor="end" height={60} />
              <YAxis tick={{ fontSize: 11, fill: AXIS_INK.light }} />
              <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8 }} />
              <Line
                type="monotone"
                dataKey={valueKey}
                stroke={isDark ? SINGLE_SERIES.dark : SINGLE_SERIES.light}
                strokeWidth={2}
                dot={{ r: 3 }}
              />
            </LineChart>
          ) : (
            <PieChart>
              <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8 }} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Pie data={chartData} dataKey={valueKey} nameKey={labelKey} outerRadius={90} label={{ fontSize: 11 }}>
                {chartData.map((_, i) => (
                  <Cell key={i} fill={palette[i % palette.length]} stroke={isDark ? "#0f172a" : "#ffffff"} strokeWidth={2} />
                ))}
              </Pie>
            </PieChart>
          )}
        </ResponsiveContainer>
      </div>
    </div>
  );
}
