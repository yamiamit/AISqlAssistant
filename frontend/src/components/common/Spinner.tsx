import { Loader2 } from "lucide-react";
import clsx from "clsx";

export default function Spinner({ className }: { className?: string }) {
  return <Loader2 className={clsx("h-5 w-5 animate-spin text-indigo-500", className)} />;
}
