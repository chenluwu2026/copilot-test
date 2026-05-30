export function Card({
  title,
  children,
  className = "",
}: {
  title?: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={`rounded-lg border border-aims-border bg-aims-card p-4 ${className}`}>
      {title && <h2 className="mb-3 text-sm font-medium text-gray-400">{title}</h2>}
      {children}
    </div>
  );
}
