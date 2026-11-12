import { forwardRef, type InputHTMLAttributes, type SelectHTMLAttributes, type TextareaHTMLAttributes } from "react";
import { cn } from "@/utils/cn";

const base = "w-full rounded-md border border-line bg-surface px-3 text-sm outline-none transition-colors focus:border-primary focus:ring-1 focus:ring-primary";

function Wrap({ label, error, id, children }: { label: string; error?: string; id: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <label htmlFor={id} className="text-sm font-medium text-ink">{label}</label>
      {children}
      {error && <p role="alert" className="text-xs text-danger">{error}</p>}
    </div>
  );
}

interface FieldProps extends InputHTMLAttributes<HTMLInputElement> { label: string; error?: string }
export const Field = forwardRef<HTMLInputElement, FieldProps>(({ label, error, id, className, ...props }, ref) => {
  const fid = id ?? props.name ?? label;
  return <Wrap label={label} error={error} id={fid}><input ref={ref} id={fid} aria-invalid={!!error} className={cn(base, "h-9", error && "border-danger", className)} {...props} /></Wrap>;
});
Field.displayName = "Field";

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> { label: string; error?: string }
export const SelectField = forwardRef<HTMLSelectElement, SelectProps>(({ label, error, id, className, children, ...props }, ref) => {
  const fid = id ?? props.name ?? label;
  return <Wrap label={label} error={error} id={fid}><select ref={ref} id={fid} className={cn(base, "h-9", className)} {...props}>{children}</select></Wrap>;
});
SelectField.displayName = "SelectField";

interface AreaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> { label: string; error?: string }
export const TextArea = forwardRef<HTMLTextAreaElement, AreaProps>(({ label, error, id, className, ...props }, ref) => {
  const fid = id ?? props.name ?? label;
  return <Wrap label={label} error={error} id={fid}><textarea ref={ref} id={fid} rows={3} className={cn(base, "py-2", className)} {...props} /></Wrap>;
});
TextArea.displayName = "TextArea";
