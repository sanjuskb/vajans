import { CheckCircle2, Loader2, Clock, XCircle } from "lucide-react";

type StepStatus = "done" | "active" | "pending" | "error";

interface Step {
  label: string;
  sub?: string;
  status: StepStatus;
}

interface Props {
  steps: Step[];
}

export default function StatusTracker({ steps }: Props) {
  return (
    <div className="flex flex-col gap-2">
      {steps.map((step, i) => {
        const isDone = step.status === "done";
        const isActive = step.status === "active";
        const isError = step.status === "error";

        const iconColor = isDone
          ? "text-pass"
          : isActive
          ? "text-accent-primary"
          : isError
          ? "text-fail"
          : "text-text-tertiary";

        return (
          <div key={i} className="flex items-start gap-3">
            <div className="mt-0.5 flex-shrink-0">
              {isDone && <CheckCircle2 size={16} className={iconColor} />}
              {isActive && <Loader2 size={16} className={`${iconColor} animate-spin`} />}
              {isError && <XCircle size={16} className={iconColor} />}
              {step.status === "pending" && <Clock size={16} className={iconColor} />}
            </div>
            <div className="flex-1">
              <div className={`text-sm font-medium ${
                isDone || isActive ? "text-text-primary" : "text-text-tertiary"
              }`}>
                {step.label}
              </div>
              {step.sub && (
                <div className="text-xs text-text-tertiary mt-0.5">
                  {step.sub}
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
