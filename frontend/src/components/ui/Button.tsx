import React from "react";
import { motion } from "framer-motion";
import { clsx } from "clsx";

type Variant = "primary" | "secondary" | "danger" | "ghost" | "icon";
type Size = "sm" | "md" | "lg";

interface Props extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
  icon?: React.ReactNode;
  children?: React.ReactNode;
}

const variants: Record<Variant, string> = {
  primary:   "bg-accent-primary text-white hover:bg-accent-hover focus:bg-accent-hover",
  secondary: "bg-transparent text-text-secondary border border-border-active hover:bg-bg-hover focus:bg-bg-hover",
  danger:    "bg-fail text-white hover:bg-red-700 focus:bg-red-700",
  ghost:     "bg-transparent text-accent-text hover:text-accent-hover focus:text-accent-hover",
  icon:      "bg-transparent text-text-secondary hover:bg-bg-hover focus:bg-bg-hover w-8 h-8 p-0",
};

const sizes: Record<Size, string> = {
  sm: "h-7 px-2.5 text-xs",
  md: "h-9 px-4 text-sm",
  lg: "h-11 px-6 text-base",
};

export default function Button({
  variant = "primary",
  size = "md",
  loading,
  icon,
  children,
  disabled,
  className,
  ...props
}: Props) {
  return (
    <motion.button
      whileTap={disabled || loading ? undefined : { scale: 0.97 }}
      transition={{ type: "spring", stiffness: 500, damping: 30 }}
      {...(props as any)}
      disabled={disabled || loading}
      className={clsx(
        "inline-flex items-center justify-center gap-1.5",
        "font-medium tracking-wide whitespace-nowrap",
        "rounded-md transition-colors",
        "disabled:opacity-50 disabled:cursor-not-allowed",
        variants[variant],
        sizes[size],
        className
      )}
    >
      {loading && (
        <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
      )}
      {icon && !loading && icon}
      {children}
    </motion.button>
  );
}
