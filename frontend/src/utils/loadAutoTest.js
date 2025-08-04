// Load auto-test script in development
if (import.meta.env.DEV) {
  import('./autoTest.js').then(() => {
    console.log('🧪 Auto-test script loaded in development mode');
    console.log('Run autoTest() in console to start automated testing');
  });
}