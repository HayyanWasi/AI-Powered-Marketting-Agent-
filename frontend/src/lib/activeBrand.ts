/** Navigation preference only. The backend validates ownership on every request. */
const key = (userId: string) => `active_company_profile_id:${userId}`;

export function getActiveBrandId(userId: string): string | null {
  return typeof window === "undefined" ? null : localStorage.getItem(key(userId));
}

export function setActiveBrandId(userId: string, profileId: string | null): void {
  if (profileId) localStorage.setItem(key(userId), profileId);
  else localStorage.removeItem(key(userId));
}
