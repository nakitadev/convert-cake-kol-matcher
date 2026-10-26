import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* Dynamic proxying to FastAPI backend is handled at runtime by app/api/[[...path]]/route.ts */
};

export default nextConfig;
