/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Surface
        'bg-primary':    '#0B0F1A',
        'bg-secondary':  '#111827',
        'bg-tertiary':   '#1C2333',
        'bg-hover':      '#1F2937',
        'border-subtle': '#1E2A3B',
        'border-active': '#2D3F57',

        // Brand
        'accent-primary': '#2563EB',
        'accent-hover':   '#1D4ED8',
        'accent-muted':   '#1E3A5F',
        'accent-text':    '#60A5FA',

        // Verdicts
        'pass':          '#059669',
        'pass-bg':       '#064E3B',
        'pass-text':     '#D1FAE5',
        'fail':          '#DC2626',
        'fail-bg':       '#450A0A',
        'fail-text':     '#FCA5A5',
        'uncertain':     '#D97706',
        'uncertain-bg':  '#451A03',
        'uncertain-text':'#FCD34D',
        'review':        '#7C3AED',
        'review-bg':     '#2E1065',
        'review-text':   '#C4B5FD',

        // Text
        'text-primary':   '#F9FAFB',
        'text-secondary': '#9CA3AF',
        'text-tertiary':  '#6B7280',
        'text-inverse':   '#111827',

        // Functional
        'info':    '#0EA5E9',
        'warning': '#F59E0B',
        'danger':  '#EF4444',
        'success': '#10B981',
        'neutral': '#6B7280',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      fontSize: {
        'display':  ['2.25rem',   { lineHeight: '1.2', fontWeight: '700' }],
        'h1':       ['1.875rem',  { lineHeight: '1.2', fontWeight: '700' }],
        'h2':       ['1.5rem',    { lineHeight: '1.2', fontWeight: '600' }],
        'h3':       ['1.25rem',   { lineHeight: '1.2', fontWeight: '600' }],
        'h4':       ['1.125rem',  { lineHeight: '1.2', fontWeight: '500' }],
        'body':     ['0.9375rem', { lineHeight: '1.6', fontWeight: '400' }],
        'body-sm':  ['0.875rem',  { lineHeight: '1.6', fontWeight: '400' }],
        'caption':  ['0.8125rem', { lineHeight: '1.4', fontWeight: '400' }],
      },
      borderRadius: {
        sm:  '4px',
        md:  '6px',
        lg:  '8px',
        xl:  '12px',
        '2xl': '16px',
      },
      boxShadow: {
        hover: '0 0 0 1px #2D3F57',
      },
    },
  },
  plugins: [],
}
