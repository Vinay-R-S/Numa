// Lightweight toast helper - wraps browser console + optional UI notification
// Replace with a proper toast library (e.g. sonner) if desired.
export const toast = {
  error: (msg: string) => console.error("[toast]", msg),
  success: (msg: string) => console.log("[toast]", msg),
}
