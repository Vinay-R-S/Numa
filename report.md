# GitHub OAuth 404 Error — Bug Report

**Project:** Numa  
**Date:** 2026-05-19  
**Affected Flow:** Settings → GitHub Connect (via Productivity page)  
**Error:** `Failed to load resource: the server responded with a status of 404 (Not Found)`

---

## Summary

The 404 error is **not** caused by a missing server route. The backend route `GET /api/github/connect` exists and is correctly registered. The errors are in the **client-side API calls** that happen around the connect flow, and in a **missing OAuth Redirect URI field** in the Settings form.

---

## Bug #1 — `connectGitHub()` reads wrong field from response ❌

**File:** `client/src/components/productivity/productivityApi.ts`, line 83  
**Severity:** CRITICAL — this is the direct cause of the 404

### What happens

When the user clicks **"Connect GitHub"** on the Productivity page:

1. The client calls `GET /api/github/connect`
2. The backend returns: `{ "authorization_url": "https://github.com/login/oauth/authorize?..." }`
3. The client reads `data.auth_url` — **a field that does not exist in the response**
4. `connectGitHub()` returns `undefined`
5. The browser redirects to `undefined`, which resolves to the current-page URL + `/undefined` → **404**

### Current broken code

```ts
// productivityApi.ts — line 77-84
export async function connectGitHub(): Promise<string> {
  const res = await fetch(`${API_BASE}/api/github/connect`, {
    headers: getAuthHeaders(),
  })
  if (!res.ok) throw new Error("Failed to get GitHub auth URL")
  const data = await res.json()
  return data.auth_url   // WRONG — backend sends "authorization_url", not "auth_url"
}
```

**Backend schema returns:** `authorization_url`  
**Client reads:** `auth_url` (undefined)

### Fix

```ts
return data.authorization_url   // matches the backend field name
```

---

## Bug #2 — `disconnectGitHub()` uses wrong HTTP method ❌

**File:** `client/src/components/productivity/productivityApi.ts`, line 96  
**Severity:** HIGH — causes a 405 Method Not Allowed error on disconnect

### What happens

The client sends `POST /api/github/disconnect`, but the backend registers this as `DELETE`:

```python
# server/src/github_agent/router.py — line 263
@router.delete("/disconnect", status_code=204)
```

### Current broken code

```ts
export async function disconnectGitHub(): Promise<void> {
  const res = await fetch(`${API_BASE}/api/github/disconnect`, {
    method: "POST",   // WRONG — backend uses DELETE
    headers: getAuthHeaders(),
  })
  if (!res.ok) throw new Error("Failed to disconnect GitHub")
}
```

### Fix

```ts
method: "DELETE",   // matches the backend route definition
```

---

## Bug #3 — Settings form doesn't expose `GITHUB_OAUTH_REDIRECT_URI` ⚠️

**File:** `client/src/app/(protected)/settings/page.tsx`, lines 773-780  
**Severity:** MEDIUM — users cannot update the redirect URI from the UI

### What happens

The GitHub section in the Integration Keys form only shows `Client ID` and `Client Secret`.
The `GITHUB_OAUTH_REDIRECT_URI` — which **must exactly match** what's registered in the GitHub OAuth App — cannot be changed from the UI. If this is wrong, GitHub rejects the callback and the user gets a redirect_uri_mismatch error.

### Current fields

```ts
{
  id: "github",
  label: "GitHub",
  fields: [
    { key: "github_client_id", label: "Client ID", isSecret: true },
    { key: "github_client_secret", label: "Client Secret", isSecret: true },
    // MISSING: github_oauth_redirect_uri
  ],
},
```

### Fix

Add the field to settings/page.tsx:
```ts
{ key: "github_oauth_redirect_uri", label: "OAuth Redirect URI", isSecret: false },
```

Add it to the backend allowed keys in `server/src/ai_settings/router.py`:
```python
_INTEGRATION_CHECK_KEYS = {
    ...
    "GITHUB_OAUTH_REDIRECT_URI": "github_oauth_redirect_uri",
}
_INTEGRATION_ALLOWED_KEYS = {
    ...
    "github_oauth_redirect_uri": "GITHUB_OAUTH_REDIRECT_URI",
}
```

---

## Current Configuration State

From `server/.env`:

| Variable | Value |
|---|---|
| `GITHUB_CLIENT_ID` | `Ov23liISCRrhNoTykAAZ` |
| `GITHUB_CLIENT_SECRET` | (set) |
| `GITHUB_OAUTH_REDIRECT_URI` | `http://localhost:8000/api/github/callback` |

The backend callback route is registered at `GET /api/github/callback`. This matches the `.env` value — so the server-side configuration is correct.

> **Action required on GitHub App settings:** Make sure `http://localhost:8000/api/github/callback`
> is added as an **Authorization callback URL** in your GitHub OAuth App at:
> https://github.com/settings/developers

---

## Full OAuth Flow (for reference)

```
User clicks "Connect GitHub"
       |
       v
Client: GET /api/github/connect  (productivityApi.ts)
       |
       v
Backend returns: { "authorization_url": "https://github.com/login/oauth/authorize?..." }
       |
       v  <-- Bug #1: client reads data.auth_url (undefined) instead of data.authorization_url
Browser redirects to GitHub OAuth consent page
       |
       v
GitHub redirects to: http://localhost:8000/api/github/callback?code=...&state=...
       |
       v
Backend exchanges code for access token, stores in DB
       |
       v
Backend redirects to: http://localhost:3000/settings?github=connected
```

---

## Files to Change

| File | Line | Change |
|---|---|---|
| `client/src/components/productivity/productivityApi.ts` | 83 | `data.auth_url` → `data.authorization_url` |
| `client/src/components/productivity/productivityApi.ts` | 96 | `method: "POST"` → `method: "DELETE"` |
| `client/src/app/(protected)/settings/page.tsx` | 780 | Add `github_oauth_redirect_uri` field |
| `server/src/ai_settings/router.py` | 168/181 | Add `GITHUB_OAUTH_REDIRECT_URI` to key maps |

---

## Corrected `productivityApi.ts` functions

```ts
export async function connectGitHub(): Promise<string> {
  const res = await fetch(`${API_BASE}/api/github/connect`, {
    headers: getAuthHeaders(),
  })
  if (!res.ok) throw new Error("Failed to get GitHub auth URL")
  const data = await res.json()
  return data.authorization_url   // FIXED
}

export async function disconnectGitHub(): Promise<void> {
  const res = await fetch(`${API_BASE}/api/github/disconnect`, {
    method: "DELETE",   // FIXED
    headers: getAuthHeaders(),
  })
  if (!res.ok) throw new Error("Failed to disconnect GitHub")
}
```
