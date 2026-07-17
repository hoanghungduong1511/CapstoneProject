/** @type {import('next').NextConfig} */
const nextConfig = {
  typescript: {
    ignoreBuildErrors: true,
  },
  images: {
    unoptimized: true,
  },
  experimental: {
    // Optimize large icon libraries - only import used icons
    optimizePackageImports: ['lucide-react', 'recharts'],
  },
}

export default nextConfig
