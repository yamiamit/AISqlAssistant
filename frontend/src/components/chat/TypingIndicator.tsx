export default function TypingIndicator() {
  return (
    <div className="flex items-center gap-1 rounded-lg bg-slate-100 px-3 py-2 w-fit dark:bg-slate-800">
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400 dark:bg-slate-500"
          style={{ animationDelay: `${i * 0.15}s` }}
        />
      ))}
    </div>
  );
}
