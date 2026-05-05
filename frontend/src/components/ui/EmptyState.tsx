import React from "react";
import Button from "./Button";

interface Props {
  icon: React.ReactNode;
  title: string;
  description?: string;
  action?: { label: string; onClick: () => void };
  className?: string;
}

export default function EmptyState({ icon, title, description, action, className }: Props) {
  return (
    <div className={`flex flex-col items-center justify-center py-16 px-8 text-center ${className}`}>
      <div className="text-text-tertiary mb-6 opacity-50">
        {icon}
      </div>
      <p className="text-base font-semibold text-text-secondary mb-2">{title}</p>
      {description && (
        <p className="text-sm text-text-tertiary max-w-md">{description}</p>
      )}
      {action && (
        <div className="mt-8">
          <Button variant="primary" onClick={action.onClick}>{action.label}</Button>
        </div>
      )}
    </div>
  );
}
