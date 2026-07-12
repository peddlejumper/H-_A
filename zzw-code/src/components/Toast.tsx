import { useUIStore } from '@/stores/uiStore';
import { CheckCircle, AlertCircle, Info, AlertTriangle, X } from 'lucide-react';

const iconMap = {
  success: CheckCircle,
  error: AlertCircle,
  info: Info,
  warning: AlertTriangle,
};

const colorMap = {
  success: 'border-zzw-green text-zzw-green',
  error: 'border-zzw-red text-zzw-red',
  info: 'border-zzw-cyan text-zzw-cyan',
  warning: 'border-zzw-yellow text-zzw-yellow',
};

const bgMap = {
  success: 'bg-zzw-green/10',
  error: 'bg-zzw-red/10',
  info: 'bg-zzw-cyan/10',
  warning: 'bg-zzw-yellow/10',
};

export default function ToastContainer() {
  const { toasts, removeToast } = useUIStore();

  if (toasts.length === 0) return null;

  return (
    <div className="fixed bottom-16 right-4 z-40 flex flex-col gap-2 pointer-events-none">
      {toasts.map((toast) => {
        const Icon = iconMap[toast.type];
        return (
          <div
            key={toast.id}
            className={`pointer-events-auto flex items-center gap-2 px-3 py-2.5 rounded-lg border ${colorMap[toast.type]} ${bgMap[toast.type]} shadow-lg animate-slide-right max-w-sm`}
          >
            <Icon className="w-4 h-4 shrink-0" />
            <span className="text-xs text-zzw-text flex-1">{toast.message}</span>
            <button
              onClick={() => removeToast(toast.id)}
              className="w-4 h-4 rounded flex items-center justify-center text-zzw-text-dim hover:text-zzw-text transition-colors shrink-0"
            >
              <X className="w-3 h-3" />
            </button>
          </div>
        );
      })}
    </div>
  );
}