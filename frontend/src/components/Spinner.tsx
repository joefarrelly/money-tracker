export function Spinner({ className = "" }: { className?: string }) {
  return (
    <div className={`flex items-center justify-center py-16 ${className}`}>
      <div className="w-7 h-7 rounded-full border-2 border-slate-800 border-t-indigo-500 animate-spin" />
    </div>
  );
}
