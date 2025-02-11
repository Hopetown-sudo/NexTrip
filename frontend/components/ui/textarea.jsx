import * as React from "react";
import { cn } from "@/lib/utils";

const Textarea = React.forwardRef(({ className, value, ...props }, ref) => {
  return (
    <textarea
      className={cn(
        "flex min-h-[40px] w-full rounded-md border border-input bg-transparent px-3 py-1 text-base shadow-sm placeholder:text-muted-foreground focus:outline-none disabled:cursor-not-allowed disabled:opacity-50 md:text-sm resize-none",
        className
      )}
      ref={ref}
      value={value}
      readOnly
      {...props}
    />
  );
});

Textarea.displayName = "Textarea";

export { Textarea };


