export function getInitials(nameOrEmail?: string | null): string {
  const value = (nameOrEmail || 'U').trim();
  if (!value) return 'U';

  const nameParts = value
    .replace(/@.*/, '')
    .split(/\s+/)
    .filter(Boolean);

  if (nameParts.length >= 2) {
    return `${nameParts[0][0]}${nameParts[nameParts.length - 1][0]}`.toUpperCase();
  }

  return value.slice(0, 2).toUpperCase();
}

export function getAvatarFallbackUrl(nameOrEmail?: string | null, size = 200): string {
  const initials = getInitials(nameOrEmail);
  return `https://ui-avatars.com/api/?name=${encodeURIComponent(initials)}&background=0f766e&color=fff&size=${size}&bold=true`;
}

export function normalizeStorageUrl(url?: string | null): string {
  if (!url) return '';

  const trimmedUrl = url.trim();
  if (!trimmedUrl) return '';

  if (trimmedUrl.startsWith('data:') || trimmedUrl.startsWith('blob:')) {
    return trimmedUrl;
  }

  const publicStorageOrigin = process.env.NEXT_PUBLIC_STORAGE_PUBLIC_URL;

  try {
    const parsed = new URL(trimmedUrl);

    if (publicStorageOrigin) {
      const publicOrigin = new URL(publicStorageOrigin);
      parsed.protocol = publicOrigin.protocol;
      parsed.hostname = publicOrigin.hostname;
      parsed.port = publicOrigin.port;
      return parsed.toString();
    }

    if (parsed.hostname === 'minio' && typeof window !== 'undefined') {
      parsed.hostname = window.location.hostname || 'localhost';
      parsed.port = parsed.port || '9000';
      return parsed.toString();
    }

    return parsed.toString();
  } catch {
    const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

    try {
      return new URL(trimmedUrl, apiBaseUrl).toString();
    } catch {
      return trimmedUrl;
    }
  }
}
