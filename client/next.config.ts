import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  devIndicators: false,
  // Allow access from any device on the local network during development
  // This enables testing on mobile devices connected to the same WiFi
  allowedDevOrigins: [
    "192.168.29.220",  // Current network IP
    "192.168.1.1",     // Common router gateway
    "localhost",
  ],
};

export default nextConfig;
