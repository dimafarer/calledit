const WebSocket = require('ws');

const ws = new WebSocket('wss://0yv5r2auh5.execute-api.us-west-2.amazonaws.com/prod');

ws.on('open', function open() {
  console.log('Connected to WebSocket');
  
  // Send a test message with timezone
  const testMessage = {
    action: 'makecall',
    prompt: 'The S&P 500 will reach 6000 points by March 2025',
    timezone: 'America/New_York'
  };
  
  console.log('Sending message:', testMessage);
  ws.send(JSON.stringify(testMessage));
});

ws.on('message', function message(data) {
  const parsedData = JSON.parse(data.toString());
  console.log('Received:', parsedData);
  
  // If it's the complete response, pretty print the JSON
  if (parsedData.type === 'complete') {
    try {
      const completePrediction = JSON.parse(parsedData.content);
      console.log('\n=== FINAL PREDICTION ===');
      console.log(JSON.stringify(completePrediction, null, 2));
    } catch (e) {
      console.log('Could not parse complete response as JSON');
    }
  }
});

ws.on('close', function close() {
  console.log('WebSocket connection closed');
});

ws.on('error', function error(err) {
  console.error('WebSocket error:', err);
});

// Close connection after 30 seconds to allow for Strands processing
setTimeout(() => {
  ws.close();
}, 30000);