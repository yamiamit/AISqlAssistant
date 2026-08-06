import { type HTMLAttributes } from "react";
import clsx from "clsx";

export default function Card({ className, children, ...rest }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={clsx(
        "rounded-xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-900",
        className
      )}
      {...rest}
    >
      {children}
    </div>
  );
}
