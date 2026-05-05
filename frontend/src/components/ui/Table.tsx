import React from "react";
import { clsx } from "clsx";

interface Column<T> {
  key: keyof T | string;
  header: string;
  render?: (value: any, row: T) => React.ReactNode;
  className?: string;
}

interface TableProps<T> {
  data: T[];
  columns: Column<T>[];
  onRowClick?: (row: T) => void;
  className?: string;
  emptyMessage?: string;
}

export default function Table<T extends Record<string, any>>({
  data,
  columns,
  onRowClick,
  className,
  emptyMessage = "No data available"
}: TableProps<T>) {
  if (data.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-text-secondary">{emptyMessage}</p>
      </div>
    );
  }

  return (
    <div className={clsx("overflow-x-auto", className)}>
      <table className="w-full">
        <thead>
          <tr className="bg-bg-primary border-b border-border-subtle">
            {columns.map((column, index) => (
              <th
                key={column.key as string}
                className={clsx(
                  "text-left text-caption font-semibold text-text-secondary uppercase tracking-wider px-4 py-3",
                  column.className
                )}
              >
                {column.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, rowIndex) => (
            <tr
              key={rowIndex}
              onClick={() => onRowClick?.(row)}
              className={clsx(
                "bg-bg-secondary border-b border-border-subtle hover:bg-bg-hover transition-colors",
                onRowClick && "cursor-pointer"
              )}
            >
              {columns.map((column) => {
                const value = row[column.key as keyof T];
                const content = column.render ? column.render(value, row) : value;

                return (
                  <td
                    key={column.key as string}
                    className={clsx(
                      "px-4 py-3.5 text-body text-text-primary",
                      column.className
                    )}
                  >
                    {content}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}