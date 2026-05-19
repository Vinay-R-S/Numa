// Lightweight toast helper - avoids console.error because Next dev treats it as an error overlay.
// Replace with a proper toast library (e.g. sonner) if desired.
export const toast = {
  error: (msg: string) => console.warn("[toast]", msg),
  success: (msg: string) => console.log("[toast]", msg),
}
