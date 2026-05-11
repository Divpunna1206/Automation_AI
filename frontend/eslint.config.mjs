import nextVitals from "eslint-config-next/core-web-vitals";
import nextTypeScript from "eslint-config-next/typescript";

const eslintConfig = [
  ...nextVitals,
  ...nextTypeScript,
  {
    rules: {
      "react-hooks/set-state-in-effect": "off"
    }
  },
  {
    ignores: [".next/**", "next-env.d.ts", "node_modules/**"]
  }
];

export default eslintConfig;
