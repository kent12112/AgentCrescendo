// Learn: Import compile-time types only; this import is erased from emitted JavaScript: import type { NextConfig } from "next";.
import type { NextConfig } from "next";

// Learn: Declare this block-scoped binding: const config: NextConfig = {. const prevents reassignment of the binding, not mutation of an object it references.
const config: NextConfig = {
  // Learn: Set this named object/configuration property: poweredByHeader: false,. The receiving API determines how the value is used.
  poweredByHeader: false,
// Learn: Close the surrounding object, function, call, or type expression; delimiters determine which construct ends here.
};

// Learn: Expose this value as the module default for the framework/importing module.
export default config;
