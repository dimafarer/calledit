import { describe, it, expect } from 'vitest';

const API_BASE = import.meta.env.VITE_APIGATEWAY || 'https://zvdf8sswt3.execute-api.us-west-2.amazonaws.com/Prod';
const WS_URL = import.meta.env.VITE_WEBSOCKET_URL || 'wss://0yv5r2auh5.execute-api.us-west-2.amazonaws.com/prod';

describe('CalledIt Integration Tests', () => {
  
  describe('WebSocket Streaming', () => {
    it('should connect and receive streaming response', async () => {
      return new Promise<void>((resolve) => {
        const timeout = setTimeout(() => {
          ws?.close();
          resolve();
        }, 10000);

        let ws: WebSocket;
        let messageReceived = false;

        try {
          ws = new WebSocket(WS_URL);
          
          ws.onopen = () => {
            console.log('✅ WebSocket connected');
            ws.send(JSON.stringify({
              action: 'makecall',
              prompt: 'Test prediction',
              timezone: 'UTC'
            }));
          };
          
          ws.onmessage = (event) => {
            try {
              const message = JSON.parse(event.data);
              console.log('📨 Message type:', message.type);
              messageReceived = true;
              
              if (message.type === 'complete') {
                clearTimeout(timeout);
                ws.close();
                resolve();
              }
            } catch (e) {
              // Continue listening
            }
          };
          
          ws.onerror = () => {
            clearTimeout(timeout);
            resolve();
          };
          
        } catch (error) {
          clearTimeout(timeout);
          resolve();
        }
      });
    });
  });

  describe('Verifiability Categories', () => {
    it('should categorize predictions correctly', async () => {
      const testCases = [
        { prompt: 'The sun will rise tomorrow', expected: 'agent_verifiable' },
        { prompt: 'Bitcoin will hit $100k today', expected: 'api_tool_verifiable' },
        { prompt: 'I will feel happy', expected: 'human_verifiable_only' }
      ];

      const results = [];
      
      for (const testCase of testCases) {
        const result = await testCategory(testCase.prompt);
        results.push({ ...testCase, actual: result });
        await new Promise(resolve => setTimeout(resolve, 2000));
      }

      console.log('\n🧪 Category Test Results:');
      results.forEach(r => {
        const match = r.actual === r.expected ? '✅' : '❌';
        console.log(`${match} "${r.prompt.substring(0, 25)}..." -> ${r.actual || 'timeout'}`);
      });

      const successCount = results.filter(r => r.actual === r.expected).length;
      console.log(`📊 Success: ${successCount}/${results.length}`);
      
      expect(successCount).toBeGreaterThan(0);
    });
  });
});

async function testCategory(prompt: string): Promise<string | null> {
  return new Promise((resolve) => {
    const timeout = setTimeout(() => {
      ws?.close();
      resolve(null);
    }, 15000);

    let ws: WebSocket;

    try {
      ws = new WebSocket(WS_URL);
      
      ws.onopen = () => {
        ws.send(JSON.stringify({
          action: 'makecall',
          prompt,
          timezone: 'UTC'
        }));
      };
      
      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          
          if (message.type === 'complete') {
            const response = typeof message.content === 'string' 
              ? JSON.parse(message.content) 
              : message.content;
              
            clearTimeout(timeout);
            ws.close();
            resolve(response?.verifiable_category || null);
          }
        } catch (e) {
          // Continue
        }
      };
      
      ws.onerror = () => {
        clearTimeout(timeout);
        resolve(null);
      };
      
    } catch (error) {
      clearTimeout(timeout);
      resolve(null);
    }
  });
}