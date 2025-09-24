import { test, expect } from '@playwright/test';

test.describe('API Integration Tests', () => {
  test('should return healthy status from health endpoint', async ({ request }) => {
    const response = await request.get('/api/health');
    expect(response.status()).toBe(200);

    const health = await response.json();
    expect(health.status).toBe('healthy');
    expect(health.timestamp).toBeDefined();
  });

  test('should require authentication for protected endpoints', async ({ request }) => {
    const response = await request.get('/api/chat/sessions');
    expect(response.status()).toBe(401);
  });

  test('should authenticate with demo credentials', async ({ request }) => {
    const response = await request.post('/api/auth/login', {
      data: {
        username: 'demo_admin',
        password: 'demo_password_123'
      }
    });

    expect(response.status()).toBe(200);
    const authData = await response.json();
    expect(authData.access_token).toBeDefined();
    expect(authData.user).toBeDefined();
  });

  test('should create chat session with authentication', async ({ request }) => {
    // First authenticate
    const authResponse = await request.post('/api/auth/login', {
      data: {
        username: 'demo_admin',
        password: 'demo_password_123'
      }
    });

    const authData = await authResponse.json();
    const token = authData.access_token;

    // Create chat session
    const sessionResponse = await request.post('/api/chat/sessions', {
      headers: {
        'Authorization': `Bearer ${token}`
      },
      data: {
        title: 'E2E Test Session'
      }
    });

    expect(sessionResponse.status()).toBe(201);
    const session = await sessionResponse.json();
    expect(session.id).toBeDefined();
    expect(session.title).toBe('E2E Test Session');
  });

  test('should send chat message and receive response', async ({ request }) => {
    // Authenticate first
    const authResponse = await request.post('/api/auth/login', {
      data: {
        username: 'demo_admin',
        password: 'demo_password_123'
      }
    });

    const authData = await authResponse.json();
    const token = authData.access_token;

    // Create session
    const sessionResponse = await request.post('/api/chat/sessions', {
      headers: {
        'Authorization': `Bearer ${token}`
      },
      data: {
        title: 'API Test Session'
      }
    });

    const session = await sessionResponse.json();

    // Send message
    const messageResponse = await request.post('/api/chat/message', {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      data: {
        session_id: session.id,
        message: 'Hello, this is a test message',
        model: 'default'
      }
    });

    expect(messageResponse.status()).toBe(200);
    const result = await messageResponse.json();
    expect(result.response).toBeDefined();
    expect(result.response.length).toBeGreaterThan(0);
  });

  test('should handle streaming chat response', async ({ request }) => {
    // Authenticate
    const authResponse = await request.post('/api/auth/login', {
      data: {
        username: 'demo_admin',
        password: 'demo_password_123'
      }
    });

    const authData = await authResponse.json();
    const token = authData.access_token;

    // Create session
    const sessionResponse = await request.post('/api/chat/sessions', {
      headers: {
        'Authorization': `Bearer ${token}`
      },
      data: {
        title: 'Streaming Test Session'
      }
    });

    const session = await sessionResponse.json();

    // Send streaming message
    const streamResponse = await request.post('/api/chat/stream', {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      data: {
        session_id: session.id,
        message: 'Tell me about AI in one paragraph',
        stream: true
      }
    });

    expect(streamResponse.status()).toBe(200);
    expect(streamResponse.headers()['content-type']).toContain('text/plain');
  });

  test('should validate request schemas', async ({ request }) => {
    // Authenticate
    const authResponse = await request.post('/api/auth/login', {
      data: {
        username: 'demo_admin',
        password: 'demo_password_123'
      }
    });

    const authData = await authResponse.json();
    const token = authData.access_token;

    // Send invalid message request
    const invalidResponse = await request.post('/api/chat/message', {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      data: {
        // Missing required fields
        message: ''
      }
    });

    expect(invalidResponse.status()).toBe(422); // Validation error
  });

  test('should handle rate limiting', async ({ request }) => {
    // Authenticate
    const authResponse = await request.post('/api/auth/login', {
      data: {
        username: 'demo_admin',
        password: 'demo_password_123'
      }
    });

    const authData = await authResponse.json();
    const token = authData.access_token;

    // Create session
    const sessionResponse = await request.post('/api/chat/sessions', {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });

    const session = await sessionResponse.json();

    // Send multiple rapid requests to test rate limiting
    const promises = Array.from({ length: 10 }, (_, i) =>
      request.post('/api/chat/message', {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        data: {
          session_id: session.id,
          message: `Rate limit test ${i}`,
          model: 'default'
        }
      })
    );

    const responses = await Promise.all(promises);
    const rateLimitedResponses = responses.filter(r => r.status() === 429);

    // Should have some rate limited responses
    expect(rateLimitedResponses.length).toBeGreaterThan(0);
  });
});