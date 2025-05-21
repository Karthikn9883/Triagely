import { Amplify } from "aws-amplify";
import Constants from "expo-constants";

const extra = Constants.expoConfig?.extra || {};
const config = {
  Auth: {
    region: extra.awsRegion,
    userPoolId: extra.cogUserPoolId,
    userPoolWebClientId: extra.cogAppClientId,
    authenticationFlowType: "USER_PASSWORD_AUTH",
  }
};
Amplify.configure(config);

export default config;
