/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Warm dark theme with improved readability
        background: {
          DEFAULT: 'hsl(30 10% 14%)', // Warm dark brown-gray
          secondary: 'hsl(30 8% 18%)', // Slightly lighter warm tone
          tertiary: 'hsl(30 6% 22%)', // Card backgrounds
          elevated: 'hsl(30 5% 26%)', // Elevated surfaces
        },
        foreground: {
          DEFAULT: 'hsl(30 20% 94%)', // Warm off-white for better readability
          secondary: 'hsl(30 10% 75%)', // Warm gray for secondary text
          tertiary: 'hsl(30 8% 55%)', // Muted warm gray
          muted: 'hsl(30 6% 45%)', // Very muted text
        },
        border: {
          DEFAULT: 'hsla(30 10% 80% / 0.12)', // Warm subtle borders
          strong: 'hsla(30 10% 80% / 0.18)', // Stronger borders
          input: 'hsla(30 10% 80% / 0.15)',
        },
        // Primary warm accent color (softer)
        primary: {
          DEFAULT: 'hsl(25 70% 48%)', // Softer warm orange
          hover: 'hsl(25 70% 53%)',
          foreground: 'hsl(30 20% 98%)',
        },
        secondary: {
          DEFAULT: 'hsl(30 10% 25%)',
          hover: 'hsl(30 10% 30%)',
          foreground: 'hsl(30 20% 94%)',
        },
        // Limited accent colors for important elements
        accent: {
          warm: 'hsl(25 70% 48%)', // Softer warm orange
          cool: 'hsl(200 60% 50%)', // Softer complementary blue
          success: 'hsl(142 50% 45%)', // Even softer green
        },
        // System colors (used sparingly)
        system: {
          blue: 'hsl(200 60% 50%)',
          green: 'hsl(142 50% 45%)',
          orange: 'hsl(25 70% 48%)',
          red: 'hsl(0 60% 50%)',
          yellow: 'hsl(45 70% 50%)',
        },
        destructive: {
          DEFAULT: 'hsl(0 60% 50%)', // Even softer red
          hover: 'hsl(0 60% 55%)',
          foreground: 'hsl(30 20% 98%)',
        },
        success: {
          DEFAULT: 'hsl(142 50% 45%)',
          hover: 'hsl(142 50% 50%)',
          foreground: 'hsl(30 20% 98%)',
        },
        warning: {
          DEFAULT: 'hsl(45 70% 50%)',
          hover: 'hsl(45 70% 55%)',
          foreground: 'hsl(30 10% 14%)',
        },
        ring: 'hsl(25 70% 48%)',
        card: {
          DEFAULT: 'hsl(30 8% 16%)',
          hover: 'hsl(30 8% 20%)',
          foreground: 'hsl(30 20% 94%)',
        },
      },
      fontFamily: {
        sans: [
          '-apple-system',
          'BlinkMacSystemFont',
          'SF Pro Display',
          'Inter',
          'Helvetica Neue',
          'system-ui',
          'sans-serif',
        ],
        mono: ['SF Mono', 'Monaco', 'Inconsolata', 'Fira Code', 'monospace'],
      },
      fontSize: {
        '2xs': '0.625rem', // 10px
        xs: '0.6875rem', // 11px
        sm: '0.75rem', // 12px
        base: '0.8125rem', // 13px
        lg: '0.875rem', // 14px
        xl: '1rem', // 16px
        '2xl': '1.125rem', // 18px
        '3xl': '1.375rem', // 22px
        '4xl': '1.75rem', // 28px
      },
      borderRadius: {
        none: '0',
        sm: '0.375rem', // 6px
        DEFAULT: '0.5rem', // 8px
        md: '0.625rem', // 10px
        lg: '0.75rem', // 12px
        xl: '1rem', // 16px
        '2xl': '1.25rem', // 20px
        '3xl': '1.5rem', // 24px
      },
      backdropBlur: {
        xs: '2px',
        sm: '4px',
        DEFAULT: '8px',
        md: '12px',
        lg: '16px',
        xl: '24px',
      },
      animation: {
        'fade-in': 'fadeIn 0.2s ease-in-out',
        'fade-out': 'fadeOut 0.2s ease-in-out',
        'slide-in': 'slideIn 0.3s ease-out',
        'slide-out': 'slideOut 0.3s ease-out',
        'scale-in': 'scaleIn 0.2s ease-out',
        'bounce-gentle': 'bounceGentle 0.6s ease-in-out',
        glow: 'glow 2s ease-in-out infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        fadeOut: {
          '0%': { opacity: '1' },
          '100%': { opacity: '0' },
        },
        slideIn: {
          '0%': { transform: 'translateY(10px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        slideOut: {
          '0%': { transform: 'translateY(0)', opacity: '1' },
          '100%': { transform: 'translateY(10px)', opacity: '0' },
        },
        scaleIn: {
          '0%': { transform: 'scale(0.95)', opacity: '0' },
          '100%': { transform: 'scale(1)', opacity: '1' },
        },
        bounceGentle: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-4px)' },
        },
        glow: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.8' },
        },
      },
      boxShadow: {
        glass: '0 8px 32px 0 rgba(0, 0, 0, 0.2)',
        card: '0 2px 8px rgba(0, 0, 0, 0.2)',
        'card-hover': '0 4px 16px rgba(0, 0, 0, 0.3)',
      },
    },
  },
  plugins: [require('@tailwindcss/typography'), require('tailwindcss-animate')],
};
