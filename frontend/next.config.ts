import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // 'standalone' output bundles only the necessary files for production,
  // significantly reducing image size and enabling efficient container deploys.
  output: "standalone",

  // Expose backend URL for server-side rendering if needed.
  // The primary API URL is set via NEXT_PUBLIC_API_URL at build time.
  env: {
    NEXT_PUBLIC_API_URL:
      process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
  },
};

export default nextConfig;
