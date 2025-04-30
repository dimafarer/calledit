// Comment out the Amplify import since it's causing issues
// import { Amplify } from "aws-amplify";

export const configureAmplify = () => {
  // Simplified Amplify configuration
  console.log('Amplify configuration initialized');
  // The actual configuration will be handled by the backend
  
  // Comment out the Amplify configuration code
  /*
  Amplify.configure({
    Auth: {
      // Get the Cognito configuration from environment variables
      region: import.meta.env.VITE_AWS_REGION || 'us-east-1',
      userPoolId: import.meta.env.VITE_COGNITO_USER_POOL_ID,
      userPoolWebClientId: import.meta.env.VITE_COGNITO_CLIENT_ID,
      oauth: {
        domain: import.meta.env.VITE_COGNITO_DOMAIN?.replace('https://', '') || '',
        scope: ['email', 'profile', 'openid'],
        redirectSignIn: window.location.origin,
        redirectSignOut: window.location.origin,
        responseType: 'code'
      }
    }
  });
  */
};


