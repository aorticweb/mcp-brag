import * as React from 'react';
import { Slot } from '@radix-ui/react-slot';
import { cva, type VariantProps } from 'class-variance-authority';

import { cn } from '../../utils';

const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 whitespace-nowrap font-medium transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50 focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0 [&_svg]:flex-shrink-0 active:scale-[0.98] group relative overflow-hidden',
  {
    variants: {
      variant: {
        default: 'bg-primary text-primary-foreground hover:bg-primary-hover shadow-sm',
        destructive:
          'bg-destructive text-destructive-foreground hover:bg-destructive-hover shadow-sm',
        outline:
          'border border-border bg-transparent text-foreground hover:bg-white/5 hover:border-border-strong',
        secondary: 'bg-secondary text-secondary-foreground hover:bg-secondary-hover shadow-sm',
        ghost: 'hover:bg-white/5 text-foreground-secondary hover:text-foreground',
        link: 'text-primary underline-offset-4 hover:underline p-0 h-auto',
        glass: 'glass text-foreground hover:bg-white/10',
      },
      size: {
        default: 'h-8 px-3 text-sm rounded-lg',
        sm: 'h-6 px-2 text-xs rounded-md',
        lg: 'h-9 px-4 text-base rounded-lg',
        icon: 'h-8 w-8 rounded-lg',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, children, ...props }, ref) => {
    const Comp = asChild ? Slot : 'button';
    return (
      <Comp className={cn(buttonVariants({ variant, size, className }))} ref={ref} {...props}>
        {/* Shimmer effect for default variant */}
        {variant === 'default' && (
          <div className="absolute inset-0 -translate-x-full group-hover:translate-x-full transition-transform duration-700">
            <div className="h-full w-12 bg-gradient-to-r from-transparent via-white/20 to-transparent skew-x-12" />
          </div>
        )}
        {children}
      </Comp>
    );
  }
);
Button.displayName = 'Button';

export { Button, buttonVariants };
