const WebSocket = require('ws');

const ws = new WebSocket('wss://0yv5r2auh5.execute-api.us-west-2.amazonaws.com/prod');

ws.on('open', function open() {
  console.log('Connected to WebSocket');
  
  // Send a test message
  const testMessage = {
    action: 'makecall',
    prompt: 'Bitcoin will reach $100,000 by the end of 2025'
  };
  
  console.log('Sending message:', testMessage);
  ws.send(JSON.stringify(testMessage));
});

ws.on('message', function message(data) {
  console.log('Received:', JSON.parse(data.toString()));
});

ws.on('close', function close() {
  console.log('WebSocket connection closed');
});

ws.on('error', function error(err) {
  console.error('WebSocket error:', err);
});

// Close connection after 10 seconds
setTimeout(() => {
  ws.close();
}, 10000);