/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Surface — CSS vars so they adapt to dark/light theme
        'bg-primary':    'var(--bg-primary)',
        'bg-secondary':  'var(--bg-secondary)',
        'bg-tertiary':   'var(--bg-tertiary)',
        'bg-hover':      'var(--bg-hover)',
        'border-subtle': 'var(--border-subtle)',
        'border-active': 'var(--border-active)',

        // Brand — accent hex stays (same in both themes)
        'accent-primary': '#2563EB',
        'accent-hover':   '#1D4ED8',
        'accent-muted':   'var(--accent-muted)',
        'accent-text':    'var(--accent-text)',

        // Verdicts — solid stays hex, bg/text via CSS vars
        'pass':          '#059669',
        'pass-bg':       'var(--pass-bg)',
        'pass-text':     'var(--pass-text)',
        'fail':          '#DC2626',
        'fail-bg':       'var(--fail-bg)',
        'fail-text':     'var(--fail-text)',
        'uncertain':     '#D97706',
        'uncertain-bg':  'var(--uncertain-bg)',
        'uncertain-text':'var(--uncertain-text)',
        'review':        '#7C3AED',
        'review-bg':     'var(--review-bg)',
        'review-text':   'var(--review-text)',

        // Text — CSS vars
        'text-primary':   'var(--text-primary)',
        'text-secondary': 'var(--text-secondary)',
        'text-tertiary':  'var(--text-tertiary)',
        'text-inverse':   'var(--bg-primary)',

        // Functional — same in both themes
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
