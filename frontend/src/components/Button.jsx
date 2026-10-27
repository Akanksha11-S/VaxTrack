import { Link } from "react-router-dom";
import { Loader2 } from "lucide-react";

const VARIANTS = {
  primary: "bg-teal-600 text-white hover:bg-teal-700 disabled:bg-teal-600/50",
  secondary: "bg-white text-ink border border-line-strong hover:bg-paper disabled:text-ink-muted",
  ghost: "text-ink-soft hover:bg-teal-50 hover:text-ink",
  danger: "bg-rose-700 text-white hover:bg-rose-700/90 disabled:bg-rose-700/50",
  quiet: "text-teal-700 hover:underline px-0",
};
const SIZES = { sm: "h-8 px-3 text-sm", md: "h-10 px-4 text-sm", lg: "h-11 px-5 text-base" };

export default function Button({ variant = "primary", size = "md", to, href, loading = false, icon: Icon, children, className = "", ...rest }) {
  const cls = `inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-control font-medium transition-colors disabled:cursor-not-allowed ${VARIANTS[variant]} ${variant === "quiet" ? "" : SIZES[size]} ${className}`;
  const content = (
    <>
      {loading ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : Icon ? <Icon className="h-4 w-4" aria-hidden /> : null}
      {children}
    </>
  );
  if (to) return <Link to={to} className={cls} {...rest}>{content}</Link>;
  if (href) return <a href={href} className={cls} target="_blank" rel="noreferrer noopener" {...rest}>{content}</a>;
  return <button type="button" className={cls} disabled={loading || rest.disabled} {...rest}>{content}</button>;
}
