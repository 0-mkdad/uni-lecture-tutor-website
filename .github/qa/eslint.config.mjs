export default [{
  files: ["**/*.js"],
  languageOptions: { ecmaVersion: "latest", sourceType: "script", globals: {
    document: "readonly", window: "readonly", navigator: "readonly",
    location: "readonly", matchMedia: "readonly", FormData: "readonly"
  }},
  rules: { "no-undef": "error", "no-unreachable": "error", "no-dupe-keys": "error", "no-unused-vars": "error" }
}];
