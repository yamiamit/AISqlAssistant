import { useRef, useState } from "react";
import { AlertTriangle, Clock, Download, FileText, Image as ImageIcon, Rows3, Star } from "lucide-react";
import type { Message } from "../../types";
import SqlBlock from "./SqlBlock";
import ResultTable from "./ResultTable";
import ChartView from "./ChartView";
import Button from "../common/Button";
import SaveQueryModal from "../savedQueries/SaveQueryModal";
import { exportChartAsPng } from "../../utils/exportPng";
import * as exportApi from "../../api/export";

export default function MessageBubble({ message, dbConnectionId }: { message: Message; dbConnectionId: number | null }) {
  const [saveOpen, setSaveOpen] = useState(false);
  const chartRef = useRef<HTMLDivElement>(null);

  const hasResults = message.result_columns && message.result_rows;

  async function handleExportPng() {
    if (!chartRef.current) return;
    await exportChartAsPng(chartRef.current, `chart_${message.id}.png`);
  }

  return (
    <div className="flex flex-col gap-3">
      {/* User prompt */}
      <div className="ml-auto max-w-[80%] rounded-2xl rounded-tr-sm bg-indigo-600 px-4 py-2 text-sm text-white">
        {message.prompt_text}
      </div>

      {/* Assistant response */}
      <div className="mr-auto w-full max-w-[90%] rounded-2xl rounded-tl-sm border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
        {message.error_message ? (
          <div className="flex items-start gap-2 text-sm text-red-700 dark:text-red-300">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
            <div>
              <p className="font-medium">Couldn't complete that request</p>
              <p className="text-slate-600 dark:text-slate-400">{message.error_message}</p>
            </div>
          </div>
        ) : (
          <div className="flex flex-col gap-3">
            {message.generated_sql && <SqlBlock sql={message.generated_sql} />}

            {message.explanation && (
              <p className="text-sm text-slate-600 dark:text-slate-400">{message.explanation}</p>
            )}

            {(message.execution_time_ms != null || message.row_count != null) && (
              <div className="flex flex-wrap gap-4 text-xs text-slate-500 dark:text-slate-500">
                {message.execution_time_ms != null && (
                  <span className="flex items-center gap-1">
                    <Clock className="h-3.5 w-3.5" /> {message.execution_time_ms} ms
                  </span>
                )}
                {message.row_count != null && (
                  <span className="flex items-center gap-1">
                    <Rows3 className="h-3.5 w-3.5" /> {message.row_count} row{message.row_count === 1 ? "" : "s"}
                  </span>
                )}
              </div>
            )}

            {hasResults && <ResultTable columns={message.result_columns!} rows={message.result_rows!} />}

            {hasResults && message.chart_type && message.result_rows!.length > 0 && (
              <ChartView
                columns={message.result_columns!}
                rows={message.result_rows!}
                initialType={message.chart_type as "bar" | "line" | "pie"}
                chartRef={chartRef}
              />
            )}

            {message.generated_sql && (
              <div className="flex flex-wrap gap-2 border-t border-slate-100 pt-3 dark:border-slate-800">
                <Button size="sm" variant="secondary" onClick={() => setSaveOpen(true)}>
                  <Star className="h-3.5 w-3.5" /> Save Query
                </Button>
                {hasResults && (
                  <Button size="sm" variant="secondary" onClick={() => exportApi.exportCsv(message.id)}>
                    <Download className="h-3.5 w-3.5" /> Export CSV
                  </Button>
                )}
                {message.chart_type && (
                  <Button size="sm" variant="secondary" onClick={handleExportPng}>
                    <ImageIcon className="h-3.5 w-3.5" /> Export PNG
                  </Button>
                )}
                <Button size="sm" variant="secondary" onClick={() => exportApi.exportPdfReport(message.id)}>
                  <FileText className="h-3.5 w-3.5" /> Export PDF Report
                </Button>
              </div>
            )}
          </div>
        )}
      </div>

      {saveOpen && message.generated_sql && (
        <SaveQueryModal
          promptText={message.prompt_text}
          sqlText={message.generated_sql}
          dbConnectionId={dbConnectionId}
          onClose={() => setSaveOpen(false)}
          onSaved={() => setSaveOpen(false)}
        />
      )}
    </div>
  );
}
