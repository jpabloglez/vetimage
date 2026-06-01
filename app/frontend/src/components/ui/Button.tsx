import React from 'react';
import { LucideIcon } from 'lucide-react';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'medical' | 'danger' | 'ghost' | 'outline';
  size?: 'sm' | 'md' | 'lg' | 'xl';
  loading?: boolean;
  leftIcon?: LucideIcon;
  rightIcon?: LucideIcon;
  fullWidth?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      variant = 'primary',
      size = 'md',
      loading = false,
      leftIcon: LeftIcon,
      rightIcon: RightIcon,
      fullWidth = false,
      children,
      className = '',
      disabled,
      ...props
    },
    ref
  ) => {
    const baseClasses = [
      'inline-flex items-center justify-center font-medium transition-all duration-200',
      'focus:outline-none focus:ring-2 focus:ring-offset-2',
      'disabled:opacity-50 disabled:cursor-not-allowed',
      'rounded-medical',
    ];

    const variantClasses = {
      primary: [
        'bg-medical-500 hover:bg-medical-600 active:bg-medical-700',
        'text-white shadow-sm hover:shadow-md',
        'focus:ring-medical-500',
      ],
      secondary: [
        'bg-slate-100 hover:bg-slate-200 active:bg-slate-300',
        'dark:bg-slate-700 dark:hover:bg-slate-600 dark:active:bg-slate-500',
        'text-slate-900 dark:text-slate-100',
        'border border-slate-200 dark:border-slate-600',
        'focus:ring-slate-500',
      ],
      medical: [
        'bg-gradient-to-r from-medical-500 to-teal-500',
        'hover:from-medical-600 hover:to-teal-600',
        'active:from-medical-700 active:to-teal-700',
        'text-white shadow-medical hover:shadow-medical-lg',
        'focus:ring-medical-500',
      ],
      danger: [
        'bg-error-500 hover:bg-error-600 active:bg-error-700',
        'text-white shadow-sm hover:shadow-md',
        'focus:ring-error-500',
      ],
      ghost: [
        'bg-transparent hover:bg-slate-100 active:bg-slate-200',
        'dark:hover:bg-slate-800 dark:active:bg-slate-700',
        'text-slate-700 dark:text-slate-300',
        'focus:ring-slate-500',
      ],
      outline: [
        'bg-transparent border-2 border-medical-500',
        'hover:bg-medical-50 active:bg-medical-100',
        'dark:hover:bg-medical-900 dark:active:bg-medical-800',
        'text-medical-600 dark:text-medical-400',
        'focus:ring-medical-500',
      ],
    };

    const sizeClasses = {
      sm: ['px-3 py-1.5 text-sm'],
      md: ['px-4 py-2 text-base'],
      lg: ['px-6 py-3 text-lg'],
      xl: ['px-8 py-4 text-xl'],
    };

    const widthClasses = fullWidth ? ['w-full'] : [];

    const iconSizeClasses = {
      sm: 'w-4 h-4',
      md: 'w-5 h-5',
      lg: 'w-6 h-6',
      xl: 'w-7 h-7',
    };

    const iconSize = iconSizeClasses[size];

    const allClasses = [
      ...baseClasses,
      ...variantClasses[variant],
      ...sizeClasses[size],
      ...widthClasses,
      className,
    ].join(' ');

    return (
      <button
        ref={ref}
        className={allClasses}
        disabled={disabled || loading}
        {...props}
      >
        {loading && (
          <svg
            className={`${iconSize} mr-2 animate-spin`}
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="m4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
          </svg>
        )}
        {!loading && LeftIcon && <LeftIcon className={`${iconSize} mr-2`} />}
        {children}
        {!loading && RightIcon && <RightIcon className={`${iconSize} ml-2`} />}
      </button>
    );
  }
);

Button.displayName = 'Button';

export default Button;