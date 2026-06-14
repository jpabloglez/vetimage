// Ambient declaration for the untyped legacy `cornerstone-core` package.
// The library ships no types; we use it loosely (pixelToCanvas, getEnabledElement,
// enable/disable, events). This silences TS7016 for both cornerstoneInit.ts and
// the FindingsOverlay without pulling in a heavyweight @types shim.
declare module 'cornerstone-core';
