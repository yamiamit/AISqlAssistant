import { Sparkles } from "lucide-react";

interface ExampleQuestionChipsProps {
  onPick: (question: string) => void;
  disabled?: boolean;
}

// Shown above the chat input only when the active connection is the shared
// demo database (see ChatPage.tsx) -- one prompt per query shape, so a
// visitor immediately sees the range of things they can ask instead of
// staring at a blank input. Keep this list in sync with
// backend/demo/README.md's "Try these prompts" section.
const EXAMPLE_QUESTIONS = [
  "Which orders are still pending?",
  "What's the average order value by year?",
  "Show the top 10 customers by total amount spent",
  "Which product categories have generated the most revenue?",
  "Show monthly revenue for 2024",
];

export default function ExampleQuestionChips({ onPick, disabled }: ExampleQuestionChipsProps) {
  return (
    <div className="flex flex-wrap items-center gap-2 border-t border-slate-200 bg-white px-3 pt-3 dark:border-slate-800 dark:bg-slate-900">
      <span className="flex items-center gap-1 text-xs font-medium text-slate-400 dark:text-slate-500">
        <Sparkles className="h-3.5 w-3.5" /> Try:
      </span>
      {EXAMPLE_QUESTIONS.map((question) => (
        <button
          key={question}
          type="button"
          disabled={disabled}
          onClick={() => onPick(question)}
          className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs text-slate-600 transition-colors hover:border-indigo-300 hover:bg-indigo-50 hover:text-indigo-600 disabled:cursor-not-allowed disabled:opacity-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 dark:hover:border-indigo-500/50 dark:hover:bg-indigo-500/10 dark:hover:text-indigo-400"
        >
          {question}
        </button>
      ))}
    </div>
  );
}
