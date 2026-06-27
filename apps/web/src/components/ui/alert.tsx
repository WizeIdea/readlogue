import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const alertVariants = cva("alert", {
  variants: {
    variant: {
      default: "alert-default",
      destructive: "alert-destructive",
    },
  },
  defaultVariants: {
    variant: "default",
  },
});

function Alert({
  className,
  variant,
  ...props
}: React.ComponentProps<"div"> & VariantProps<typeof alertVariants>) {
  return (
    <div
      role="alert"
      className={cn(alertVariants({ variant }), className)}
      {...props}
    />
  );
}

function AlertTitle({ className, ...props }: React.ComponentProps<"h3">) {
  return <h3 className={cn("alert-title", className)} {...props} />;
}

function AlertDescription({
  className,
  ...props
}: React.ComponentProps<"div">) {
  return <div className={cn("alert-description", className)} {...props} />;
}

export { Alert, AlertTitle, AlertDescription };
