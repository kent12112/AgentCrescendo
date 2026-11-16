// Import types { NextConfig } from "next"; these are removed from emitted JavaScript.
import type { NextConfig } from "next";

// Define const config: NextConfig = {
const config: NextConfig = {
  // Set this named object/configuration property: poweredByHeader: false,. The receiving API
  // determines how the value is used.
  poweredByHeader: false,
};

// Expose this value as the module default for the framework/importing module.
export default config;
