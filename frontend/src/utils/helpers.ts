// Utility helpers
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(amount);
}

export function formatNumber(num: number): string {
  return new Intl.NumberFormat('en-US').format(num);
}

export function formatDate(dateString: string): string {
  const date = new Date(dateString);
  return new Intl.DateTimeFormat('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date);
}

export function formatRelativeTime(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return formatDate(dateString);
}

export function getStatusColor(status: string): string {
  switch (status) {
    case 'completed':
      return 'text-green-600 bg-green-100';
    case 'running':
      return 'text-blue-600 bg-blue-100';
    case 'pending':
      return 'text-yellow-600 bg-yellow-100';
    case 'failed':
      return 'text-red-600 bg-red-100';
    default:
      return 'text-gray-600 bg-gray-100';
  }
}

export function getRecommendationTypeColor(type: string): string {
  switch (type) {
    case 'idle_instance':
      return 'text-orange-600 bg-orange-100';
    case 'unattached_volume':
      return 'text-purple-600 bg-purple-100';
    case 'orphaned_ip':
      return 'text-red-600 bg-red-100';
    case 'rightsize':
      return 'text-blue-600 bg-blue-100';
    case 'reserved_instance':
      return 'text-green-600 bg-green-100';
    case 'committed_use':
      return 'text-teal-600 bg-teal-100';
    default:
      return 'text-gray-600 bg-gray-100';
  }
}

export function getRecommendationTypeLabel(type: string): string {
  switch (type) {
    case 'idle_instance':
      return 'Idle Instance';
    case 'unattached_volume':
      return 'Unattached Volume';
    case 'orphaned_ip':
      return 'Orphaned IP';
    case 'rightsize':
      return 'Right-size';
    case 'reserved_instance':
      return 'Reserved Instance';
    case 'committed_use':
      return 'Committed Use';
    default:
      return type;
  }
}

export function getProviderLabel(provider: string): string {
  switch (provider) {
    case 'aws':
      return 'AWS';
    case 'gcp':
      return 'GCP';
    case 'azure':
      return 'Azure';
    default:
      return provider;
  }
}

export function getProviderColor(provider: string): string {
  switch (provider) {
    case 'aws':
      return 'text-orange-600 bg-orange-100';
    case 'gcp':
      return 'text-blue-600 bg-blue-100';
    case 'azure':
      return 'text-purple-600 bg-purple-100';
    default:
      return 'text-gray-600 bg-gray-100';
  }
}