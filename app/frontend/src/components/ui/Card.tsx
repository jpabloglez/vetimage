import React from 'react';

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  variant?: 'default' | 'medical' | 'glass' | 'elevated';
  padding?: 'none' | 'sm' | 'md' | 'lg' | 'xl';
}

const Card = React.forwardRef<HTMLDivElement, CardProps>(
  (
    {
      children,
      variant = 'default',
      padding = 'md',
      className = '',
      ...props
    },
    ref
  ) => {
    const baseClasses = ['rounded-medical', 'transition-all duration-200'];

    const variantClasses = {
      default: [
        'bg-white dark:bg-slate-800',
        'border border-slate-200 dark:border-slate-700',
        'shadow-sm hover:shadow-md',
      ],
      medical: [
        'medical-card',
        'hover:shadow-medical-lg',
      ],
      glass: [
        'glass-morphism',
        'shadow-lg',
      ],
      elevated: [
        'bg-white dark:bg-slate-800',
        'shadow-lg hover:shadow-xl',
        'border border-slate-100 dark:border-slate-700',
      ],
    };

    const paddingClasses = {
      none: [],
      sm: ['p-3'],
      md: ['p-6'],
      lg: ['p-8'],
      xl: ['p-12'],
    };

    const allClasses = [
      ...baseClasses,
      ...variantClasses[variant],
      ...paddingClasses[padding],
      className,
    ].join(' ');

    return (
      <div ref={ref} className={allClasses} {...props}>
        {children}
      </div>
    );
  }
);

Card.displayName = 'Card';

// Card subcomponents
export interface CardHeaderProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
}

export const CardHeader = React.forwardRef<HTMLDivElement, CardHeaderProps>(
  ({ children, className = '', ...props }, ref) => {
    const classes = [
      'border-b border-slate-200 dark:border-slate-700',
      'pb-4 mb-6',
      className,
    ].join(' ');

    return (
      <div ref={ref} className={classes} {...props}>
        {children}
      </div>
    );
  }
);

CardHeader.displayName = 'CardHeader';

export interface CardTitleProps extends React.HTMLAttributes<HTMLHeadingElement> {
  children: React.ReactNode;
  as?: 'h1' | 'h2' | 'h3' | 'h4' | 'h5' | 'h6';
}

export const CardTitle = React.forwardRef<HTMLHeadingElement, CardTitleProps>(
  ({ children, as: Component = 'h3', className = '', ...props }, ref) => {
    const classes = [
      'text-xl font-semibold text-slate-900 dark:text-slate-100',
      'medical-gradient-text',
      className,
    ].join(' ');

    return (
      <Component ref={ref} className={classes} {...props}>
        {children}
      </Component>
    );
  }
);

CardTitle.displayName = 'CardTitle';

export interface CardContentProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
}

export const CardContent = React.forwardRef<HTMLDivElement, CardContentProps>(
  ({ children, className = '', ...props }, ref) => {
    const classes = [
      'text-slate-600 dark:text-slate-300',
      'leading-relaxed',
      className,
    ].join(' ');

    return (
      <div ref={ref} className={classes} {...props}>
        {children}
      </div>
    );
  }
);

CardContent.displayName = 'CardContent';

export interface CardFooterProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
}

export const CardFooter = React.forwardRef<HTMLDivElement, CardFooterProps>(
  ({ children, className = '', ...props }, ref) => {
    const classes = [
      'border-t border-slate-200 dark:border-slate-700',
      'pt-4 mt-6',
      'flex items-center justify-between',
      className,
    ].join(' ');

    return (
      <div ref={ref} className={classes} {...props}>
        {children}
      </div>
    );
  }
);

CardFooter.displayName = 'CardFooter';

export default Card;