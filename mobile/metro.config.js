// mobile/metro.config.js
const { getDefaultConfig } = require('expo/metro-config');

const config = getDefaultConfig(__dirname);

// allow .cjs files (Firebase ships some CJS entrypoints)
config.resolver.sourceExts.push('cjs');

// disable the new package-exports check so Metro can resolve "firebase/auth"
config.resolver.unstable_enablePackageExports = false;

module.exports = config;