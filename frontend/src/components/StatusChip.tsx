import { STATUS_LABEL } from "@/lib/format";
import type { RunStatus } from "@/lib/types";

const STYLE: Record<RunStatus, string> = {
  running: "bg-line text-ink",
  waiting: "bg-terracotta text-paper",
  done: "bg-met text-paper",
  stopped: "bg-line text-muted",
  error: "bg-ink text-paper",
};

export function StatusChip({ status }: { status: RunStatus }) {
  return (
    <span
      className={`inline-block whitespace-nowrap rounded-full px-2.5 py-0.5 font-mono text-[11px] uppercase tracking-wider ${STYLE[status]}`}
    >
      {STATUS_LABEL[status]}
    </span>
  );
}
